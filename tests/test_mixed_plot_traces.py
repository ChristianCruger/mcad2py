"""One plot carrying **both** a parametric and a function trace
(``references/mixed_plot_traces.mcdx``).

A trace is parametric when both axes are data vectors (a section outline, a
rebar scatter); it's a function trace when an axis is the plotting range and
the other is a function of it. Each kind worked alone -- a plot of only
parametric traces gets no domain at all, so nothing is sampled -- but *mixed*
on one plot they didn't: ``_detect_domain`` found ``t`` from the function trace
and applied it to the whole plot, so the parametric trace was emitted as
``sample(lambda t: v, t)``, evaluating a constant vector once per domain point.
That builds a nested object array and ``plot_axis`` raised ``ValueError:
setting an array element with a sequence``.

Mathcad states the distinction itself: the cached results are
``TraceType="Vector"`` (3 points) and ``TraceType="Range"`` (101), of different
lengths -- which is exactly what a single shared domain cannot express.

The sampling decision is therefore per axis expression, on whether it actually
references the domain variable. The one genuinely ambiguous case is settled at
runtime by ``static_axis``: a *scalar* that ignores the domain is a reference
line and does span it, where a vector keeps its own length.
"""

import re
import zipfile
from pathlib import Path

import numpy as np
import pytest

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.emit.codegen import plot_lines
from mcad2py.loader import load_mcdx
from mcad2py.parser.regions import parse_worksheet

REFERENCE = Path(__file__).parent.parent / "references" / "mixed_plot_traces.mcdx"


@pytest.fixture(scope="module")
def rendered() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.close("all")
    src = convert_file(REFERENCE, fmt="py").replace("plt.show()", "pass")
    exec(compile(src, "<generated>", "exec"), {})  # noqa: S102
    return {
        ln.get_label(): (np.asarray(ln.get_xdata()), np.asarray(ln.get_ydata()))
        for ln in plt.gcf().axes[0].lines
        if not ln.get_label().startswith("_")
    }


def _cached() -> dict[str, tuple[list[float], list[float]]]:
    """Mathcad's cached traces, keyed by ``TraceType`` (``Vector``/``Range``)."""
    result_xml = zipfile.ZipFile(REFERENCE).read("mathcad/result.xml").decode()
    out = {}
    for block in re.findall(r"<ml:Trace2dResult.*?</ml:Trace2dResult>", result_xml, re.S):
        kind = re.search(r'TraceType="([^"]*)"', block).group(1)
        vectors = [
            [float(v) for v in vec.split(",")]
            for vec in re.findall(
                r"<ml:DataVectors[^>]*>\[(.*?)\]</ml:DataVectors>", block, re.S
            )
        ]
        out[kind] = (vectors[0], vectors[1])
    return out


def test_parametric_trace_is_not_sampled_over_the_domain():
    """The regression, on the emitted source."""
    src = convert_file(REFERENCE, fmt="py")
    assert "static_axis(v, t)" in src
    assert "static_axis(2 * v, t)" in src
    # The function trace still is sampled, and the bare domain axis stays bare.
    assert "sample(lambda t: sin(t), t)" in src
    assert "sample(lambda t: v, t)" not in src


def test_each_trace_keeps_its_own_length(rendered):
    """The crux: 3 points and 101 on one plot. A single shared domain would
    force both to 101 -- which is what produced the nested array."""
    assert len(rendered["2 * v"][0]) == 3
    assert len(rendered["sin(t)"][0]) == 101


def test_traces_match_the_cached_results(rendered):
    cached = _cached()
    for label, kind in [("2 * v", "Vector"), ("sin(t)", "Range")]:
        x, y = rendered[label]
        cx, cy = cached[kind]
        assert len(x) == len(cx), kind
        assert np.allclose(x, cx, rtol=0, atol=1e-12), kind
        assert np.allclose(y, cy, rtol=0, atol=1e-12), kind


def test_parametric_trace_is_the_vector_pair(rendered):
    """``v`` against ``2·v`` -- not resampled, not reordered."""
    x, y = rendered["2 * v"]
    assert np.array_equal(y, [1.0, 2.0, 3.0])
    assert np.array_equal(x, [2.0, 4.0, 6.0])


# --- static_axis: the vector/scalar split -----------------------------------


def test_static_axis_passes_a_vector_through():
    import pint

    from mcad2py.runtime import col, static_axis

    ureg = pint.UnitRegistry()
    domain = np.linspace(0, 10, 101)

    plain = static_axis(col(1.0, 2.0, 3.0), domain)
    assert len(plain) == 3

    united = static_axis(col(1.0, 2.0, 3.0) * ureg.mm, domain)
    assert len(united) == 3
    assert united.check("[length]")


def test_static_axis_spans_the_domain_for_a_scalar():
    """A scalar that ignores the plotting variable is a *reference line*, so it
    has to be broadcast -- this is what ``sample`` used to do for every
    domain-independent expression, and the only part of that worth keeping."""
    import pint

    from mcad2py.runtime import static_axis

    ureg = pint.UnitRegistry()
    domain = np.linspace(0, 10, 101)

    line = static_axis(5.0, domain)
    assert len(line) == 101
    assert np.all(line == 5.0)

    united = static_axis(5.0 * ureg.MPa, domain)
    assert len(united) == 101
    assert np.all(united.to(ureg.MPa).magnitude == 5.0)


# --- the shapes that must keep working --------------------------------------

_WS = (
    '<worksheet xmlns="http://schemas.mathsoft.com/worksheet50" '
    'xmlns:ml="http://schemas.mathsoft.com/math50"><regions>{}</regions></worksheet>'
)
_ID = '<ml:id xml:space="preserve">{}</ml:id>'


def _define(name: str, value: str, top: str) -> str:
    return (
        f'<region top="{top}" left="0"><math><ml:define>'
        f'<ml:id labels="VARIABLE">{name}</ml:id>{value}'
        "</ml:define></math></region>"
    )


def _plot(pairs: list[tuple[str, str]]) -> str:
    def equations(maths: list[str]) -> str:
        return "<plotEquations>" + "".join(
            f"<plotEquation><math>{m}</math>"
            "<math><ml:placeholder /></math></plotEquation>"
            for m in maths
        ) + "</plotEquations>"

    return (
        '<region top="900" left="0"><plot><xyPlot><axes>'
        f"<xAxis>{equations([x for x, _ in pairs])}</xAxis>"
        f"<yAxis>{equations([y for _, y in pairs])}</yAxis>"
        "</axes></xyPlot></plot></region>"
    )


_VEC = '<ml:matrix rows="2" cols="1"><ml:real>1</ml:real><ml:real>2</ml:real></ml:matrix>'
_RANGE = "<ml:range><ml:real>0</ml:real><ml:real>10</ml:real></ml:range>"


def _plot_source(body: str) -> str:
    ws = parse_worksheet(_WS.format(body))
    plot = next(r for r in ws.regions if isinstance(r, ir.Plot))
    return "\n".join(plot_lines(plot))


def test_a_purely_parametric_plot_is_untouched():
    """Both axes data vectors, no plotting range anywhere: there is no domain,
    so nothing is sampled and nothing is wrapped (the RC_col outline case)."""
    src = _plot_source(
        _define("X", _VEC, "10")
        + _define("Y", _VEC, "20")
        + _plot([(_ID.format("X"), _ID.format("Y"))])
    )
    assert "sample(" not in src
    assert "static_axis(" not in src
    assert "plot_axis(X, None)" in src


def test_a_purely_function_plot_is_untouched():
    sin_t = (
        '<ml:apply><ml:id labels="FUNCTION" label-is-contextual="true" '
        'xml:space="preserve">sin</ml:id>' + _ID.format("t") + "</ml:apply>"
    )
    src = _plot_source(
        _define("t", _RANGE, "10") + _plot([(_ID.format("t"), sin_t)])
    )
    assert "sample(lambda t: sin(t), t)" in src
    assert "static_axis(" not in src


def test_a_constant_reference_line_still_spans_the_domain():
    """A scalar y against the plotting range: emitted through ``static_axis``,
    which broadcasts it. Emitting it *directly* would hand matplotlib a bare
    number against a 101-point x."""
    src = _plot_source(
        _define("t", _RANGE, "10")
        + _define("limit", "<ml:real>5</ml:real>", "20")
        + _plot([(_ID.format("t"), _ID.format("limit"))])
    )
    assert "static_axis(limit, t)" in src


def test_the_fixture_really_mixes_the_two_trace_kinds():
    """Guard the fixture: if a re-save ever dropped one of the traces, the
    tests above would still pass while testing nothing."""
    assert set(_cached()) == {"Vector", "Range"}
    plot = next(
        r for r in convert_worksheet(load_mcdx(REFERENCE)).regions
        if isinstance(r, ir.Plot)
    )
    assert plot.domain == "t"
    assert len(plot.traces) == 2
