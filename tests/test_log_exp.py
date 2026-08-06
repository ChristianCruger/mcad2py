"""Tests for logarithm/exponential coverage (``references/log-exp.mcdx``).

A catalogue sheet walking Mathcad's log/exp builtins, which surfaced several
gaps this file pins down:

* ``log`` takes an optional explicit base (``log(x, b)``), not just the
  1-arg base-10 default -- both now go through a runtime ``log`` helper
  (rather than ``math.log10``, which can't take a second argument).
* ``ln``/``log`` return a **complex** value for a negative real argument
  (``ln(-3) = ln(3) + iπ``), matching Mathcad, instead of raising like bare
  ``math.log``. Only ``ln(0)`` is a genuine Mathcad domain error (cached as
  an ``<engineError>``), which the runtime ``ln`` also raises on.
* ``ln0``, Mathcad's "safe" natural log that returns a large negative number
  (``-1e307``) at ``x = 0`` instead of erroring.
* the imaginary literal ``<ml:imag symbol="i">`` (unsupported before this),
  needed for ``e^(i·π) + 1`` (Euler's identity, ~0 up to float error).
* ``logspace(x1, x2, n)``: ``n`` points log-spaced between two *values*
  (unlike ``numpy.logspace``, whose bounds are exponents).
* redefining a builtin name (``exp(x) := x + 2``) and calling it afterwards
  must dispatch to the *user's* function, not the original builtin -- Mathcad
  marks such a call site ``labels="VARIABLE"`` (the same way it marks a call
  to an ordinary user-defined function), which the codegen now honours
  instead of unconditionally mapping the name through the builtin table.

``ln(0)`` genuinely raises, matching Mathcad's own ``domain_error``. Mathcad
caches that region as an ``<engineError>``, so the converter wraps it in a
``try``/``except`` (see ``ir.Region.cached_error``) and the sheet still runs as
a single ``exec()`` like every other reference -- the guarded region echoes the
caught exception in place of a value.
"""

import math
from pathlib import Path

import pytest

from mcad2py.convert import convert_file

REFERENCE = Path(__file__).parent.parent / "references" / "log-exp.mcdx"

# Mathcad's cached results (result.xml), in region/echo order. ``None`` marks
# the one region (``ln(0)``) Mathcad itself reports as a domain_error
# engineError, and which the generated code raises on too.
CACHED = [
    3.0,                                                   # log(1000)
    3.0000230549711473,                                    # ln(20.086)
    3.0,                                                   # log(1000, 10)
    8.0,                                                   # log(256, 2)
    20.085536923187664,                                    # e^3
    None,                                                  # ln(0): domain_error
    20.085536923187668,                                    # exp(3)
    -1e307,                                                # ln0(0)
    complex(1.0986122886681098, 3.1415926535897931),       # ln(-3)
    complex(0.0, 1.2246063538223773e-16),                  # e^(i*pi) + 1
    [1.0, 10.0, 100.0, 1000.0],                             # logspace(1, 1000, 4)
    4.0,                                                    # exp(2), redefined
    4.0,                                                    # log(2), redefined
]


@pytest.fixture(scope="module")
def sheet():
    """Convert and execute; the guarded ``ln(0)`` region echoes its exception."""
    src = convert_file(REFERENCE, fmt="py")
    echoed: list = []
    ns: dict = {"print": lambda *a: echoed.append(a[0] if len(a) == 1 else a)}
    exec(compile(src, "<generated>", "exec"), ns)  # noqa: S102
    return src, ns, echoed


def test_sheet_runs_end_to_end(sheet):
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == len(CACHED)


def test_ln_of_zero_raises_like_mathcads_domain_error(sheet):
    """The one cell Mathcad itself couldn't evaluate (cached ``engineError``,
    ``domain_error``) -- exactly the 6th echo (index 5). The converter guards it
    on the strength of that cached error, so it reports the exception instead of
    aborting the sheet, and the regions either side still evaluate."""
    src, _, echoed = sheet
    assert "# Mathcad reports an error here:" in src
    label, error = echoed[5]
    assert label == "error:" and isinstance(error, ValueError)
    assert echoed[4] is not None and echoed[6] is not None  # neighbors ran fine


def test_sheet_matches_cached_results(sheet):
    _, _, echoed = sheet
    for i, (got, want) in enumerate(zip(echoed, CACHED)):
        if want is None:
            assert got[0] == "error:", f"region {i}"  # the guarded domain error
        elif isinstance(want, complex):
            assert math.isclose(got.real, want.real, abs_tol=1e-9), f"region {i}"
            # The Euler's-identity residual (region 9) is float noise around a
            # true zero -- Mathcad's own quadrature differs from Python's at
            # the ~1e-5 relative level, so it's checked as "close to zero"
            # rather than pinned to Mathcad's specific residual.
            assert math.isclose(got.imag, want.imag, rel_tol=1e-3, abs_tol=1e-9), (
                f"region {i}: {got} != {want}"
            )
        elif isinstance(want, list):
            assert list(got) == pytest.approx(want), f"region {i}"
        else:
            assert math.isclose(got, want, rel_tol=1e-9), f"region {i}: {got} != {want}"


def test_log_takes_an_explicit_base(sheet):
    """``log(x, b)`` (2-arg): the explicit-base form, not just the 1-arg
    base-10 default -- both now share one runtime ``log`` helper."""
    src, _, _ = sheet
    assert "math.log10(" not in src  # the old (broken) 2-arg mapping
    from mcad2py.runtime import log as log_fn

    assert math.isclose(log_fn(1000, 10), 3.0)
    assert math.isclose(log_fn(256, 2), 8.0)
    assert math.isclose(log_fn(1000), 3.0)  # 1-arg still defaults to base 10


def test_ln_and_log_go_complex_for_a_negative_argument(sheet):
    """Mathcad returns a complex value for ``ln``/``log`` of a negative real,
    unlike bare ``math.log`` which raises."""
    from mcad2py.runtime import ln, log

    z = ln(-3)
    assert isinstance(z, complex)
    assert math.isclose(z.real, math.log(3))
    assert math.isclose(z.imag, math.pi)
    with pytest.raises(ValueError):
        ln(0)  # the one genuine domain error, matching Mathcad


def test_ln0_avoids_the_domain_error_at_zero(sheet):
    from mcad2py.runtime import ln0

    assert ln0(0) == -1e307
    assert math.isclose(ln0(20.086), math.log(20.086))


def test_logspace_is_value_spaced_not_exponent_spaced(sheet):
    """Unlike ``numpy.logspace``, ``logspace(x1, x2, n)``'s bounds are the
    actual endpoint *values*."""
    from mcad2py.runtime import logspace

    got = list(logspace(1, 1000, 4))
    assert got == pytest.approx([1, 10, 100, 1000])


def test_euler_identity_uses_the_parsed_imaginary_literal(sheet):
    src, _, echoed = sheet
    assert "1j" in src  # the parsed <ml:imag> literal
    z = echoed[9]
    assert isinstance(z, complex)
    assert z.real == 0.0
    assert math.isclose(z.imag, 0.0, abs_tol=1e-14)


def test_redefined_builtin_shadows_the_original(sheet):
    """``exp(x) := x + 2`` and ``log(x) := x**2`` are defined *after* the
    builtin calls above -- later calls must dispatch to the user's function,
    not ``math.exp``/the runtime ``log``. Mathcad marks these call sites
    ``labels="VARIABLE"``, same as an ordinary user-defined function."""
    src, ns, echoed = sheet
    assert ns["exp"](2) == 4  # 2 + 2, the user's definition
    assert ns["log"](2) == 4  # 2**2, the user's definition
    assert echoed[-2] == 4
    assert echoed[-1] == 4
    assert "math.exp(2)" not in src
