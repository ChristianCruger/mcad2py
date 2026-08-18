"""``references/seed.mcdx`` -- Mathcad's random stream, reproduced exactly.

Prime's generator is the Microsoft C runtime ``rand()``; ``Seed(n)`` is
``srand(n)``; one ``runif`` draw takes two ``rand()`` calls packed into 30
bits; ``rnorm`` is Kinderman-Monahan ratio of uniforms with the exact
``sqrt(8/e)`` constant. All of that is pinned here against Mathcad's own cache,
so ``runif`` and ``rnorm`` are the two ``r*`` helpers that are byte-exact
rather than merely repeatable.

The sheet also carries three constructs this fixture is the first to reach: a
bare ``Seed(1)`` region (a call with no ``=``, which must not print), a bare
call as a non-final line of a program body (which must not become an implicit
return), and a whole-column write ``M^<i> :=`` inside a program.
"""

from __future__ import annotations

import numpy as np
import pytest

from conftest import cached_results, flat, reference, run_sheet

SHEET = reference("seed")


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(SHEET)


@pytest.fixture(scope="module")
def cache():
    return cached_results(SHEET)


def test_generated_source_shape(sheet):
    """The three constructs the sheet is the first fixture to exercise."""
    source, _ns, _echoed = sheet
    # A bare ``Seed(1)`` region runs but does not print.
    assert "\nSeed(1)\n" in source
    assert "print(Seed(1))" in source  # the ``Seed(1) =`` region still echoes
    # A bare call above the last line of a program body stays a statement.
    assert "        Seed(1)\n        nums = rnorm(p, mu, sigma)" in source
    # ``M^<i> := nums`` is a column write, not an illegal assignment target.
    assert "M = col_set(M, i, nums)" in source
    # ``range[n] := n`` must not shadow the builtin.
    assert "range_ = index_build(" in source


def test_runif_matches_mathcad(sheet, cache):
    """``Seed(1)`` then ``runif(20, 0, 1)`` -- exact, to the last bit."""
    _source, _ns, echoed = sheet
    assert flat(echoed[2]) == pytest.approx(cache["13"], abs=0.0)


def test_seed_returns_one(sheet, cache):
    """``Seed(n) =`` echoes 1, a status code -- not the seed."""
    _source, _ns, echoed = sheet
    assert cache["14"] == [1.0]
    assert flat(echoed[3]) == pytest.approx([1.0], abs=0.0)


def test_rnorm_matches_mathcad(sheet, cache):
    """One ``rnorm`` draw, then the uniforms that follow it in the stream.

    The four trailing uniforms are what identified the method: they are
    ``U[4..7]``, so one normal draw consumed exactly four uniforms -- one
    rejected ratio-of-uniforms pair, then an accepted one.
    """
    _source, _ns, echoed = sheet
    assert flat(echoed[4]) == pytest.approx(cache["15"], abs=0.0)
    assert flat(echoed[5]) == pytest.approx(cache["16"], abs=0.0)
    # The trailing four are the stream continuing, not a restart.
    assert flat(echoed[5]).tolist() == cache["13"][4:8]


def test_program_reseeds_each_pass(sheet, cache):
    """The whole point of the sheet: ``Seed`` inside a program repeats a set."""
    _source, ns, echoed = sheet
    columns = ns["Same"](1000, 0, 2)
    assert columns.shape == (1000, 3)
    mags = np.asarray(getattr(columns, "magnitude", columns), dtype=float)
    assert np.array_equal(mags[:, 0], mags[:, 1])
    assert np.array_equal(mags[:, 0], mags[:, 2])
    # And that repeated set is Mathcad's own.
    assert flat(echoed[0]) == pytest.approx(cache["8"], abs=0.0)


def test_histogram_of_the_repeated_set(sheet, cache):
    """``hist`` over the seeded sample, and its peak bin count."""
    _source, _ns, echoed = sheet
    assert flat(echoed[1]) == pytest.approx(cache["10"], abs=0.0)


# ---------------------------------------------------------------------------
# Arms the worksheet itself never reaches. It calls ``Seed`` on a bare integer,
# ``runif`` on 0..1, and writes a dimensionless column -- so a Pint argument, a
# non-unit interval and a dimensioned column write are all untested by the six
# checks above, and each goes through a different part of the seam.


def test_seed_accepts_a_pint_quantity():
    """A seed can arrive as a dimensionless Pint quantity, not a bare int."""
    from mcad2py.runtime import Seed, runif
    from mcad2py.units import ureg

    Seed(7)
    plain = runif(3, 0, 1)
    Seed(ureg.Quantity(7, "dimensionless"))
    assert np.array_equal(runif(3, 0, 1), plain)


def test_seed_reduces_an_unreduced_ratio():
    """``float()`` on a ``mm/m`` ratio would read 7000, not 7."""
    from mcad2py.runtime import Seed, runif
    from mcad2py.units import ureg

    Seed(7)
    plain = runif(3, 0, 1)
    Seed(ureg.Quantity(7000, "mm") / ureg.Quantity(1, "m"))
    assert np.array_equal(runif(3, 0, 1), plain)


def test_runif_scales_to_an_arbitrary_interval():
    """The sheet only ever draws on 0..1; the interval is applied here."""
    from mcad2py.runtime import Seed, runif

    Seed(1)
    unit_interval = runif(5, 0, 1)
    Seed(1)
    shifted = runif(5, -10, 30)
    assert shifted == pytest.approx(-10 + 40 * unit_interval)


def test_rnorm_shifts_and_scales_the_same_stream():
    """``mu``/``sigma`` are applied to one shared stream, not a separate one."""
    from mcad2py.runtime import Seed, rnorm

    Seed(3)
    standard = rnorm(6, 0, 1)
    Seed(3)
    scaled = rnorm(6, 5, 2)
    assert scaled == pytest.approx(5 + 2 * standard)


def test_col_set_keeps_units():
    """A dimensioned column write must not be flattened to magnitudes."""
    from mcad2py.runtime import col_set
    from mcad2py.units import ureg

    M = col_set(None, 0, ureg.Quantity(np.array([1.0, 2.0, 3.0]), "m"))
    M = col_set(M, 1, ureg.Quantity(np.array([4.0, 5.0, 6.0]), "m"))
    assert M.shape == (3, 2)
    assert np.array_equal(
        np.asarray(M.to("mm").magnitude, dtype=float),
        np.array([[1000.0, 4000.0], [2000.0, 5000.0], [3000.0, 6000.0]]),
    )


def test_col_set_grows_and_zero_fills():
    """Writing a short column, then a longer one, grows and zero-fills."""
    from mcad2py.runtime import col_set

    M = col_set(None, 0, np.array([1.0, 2.0]))
    M = col_set(M, 2, np.array([7.0, 8.0, 9.0]))
    assert np.asarray(M, dtype=float).tolist() == [
        [1.0, 0.0, 7.0],
        [2.0, 0.0, 8.0],
        [0.0, 0.0, 9.0],
    ]
