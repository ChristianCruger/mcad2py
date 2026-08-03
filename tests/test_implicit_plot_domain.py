"""Plotting a function of an **undefined** variable.

Mathcad doesn't need a plotting variable defined: putting ``sin(x)`` on the y
axis against ``x`` on the x axis is enough, and it invents the interval
-10..10 for the free ``x``. The *axis* expression is then just a function of
it -- ``references/plotting-wo-var.mcdx``'s second trace puts ``x/2`` on the x
axis against ``cos(x)``, so that curve is drawn over -5..5 while its ``cos``
still sees the full -10..10.

Both traces are checked point-for-point against Mathcad's own cached sample
(``result.xml``'s ``<ml:Trace2dResult>``), which is what pins the interval,
the 499-point step and the "``x``, not the axis, is what spans -10..10"
reading. The rest of the file guards the inference itself: a plot over a
*defined* vector is untouched, and an ambiguous plot (two free names, or one
whose name is bound below by a solve block) doesn't get a domain invented.
"""

import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from mcad2py import ir
from mcad2py.convert import convert_file, convert_worksheet
from mcad2py.loader import load_mcdx
from mcad2py.parser.regions import parse_worksheet

REFERENCE = Path(__file__).parent.parent / "references" / "plotting-wo-var.mcdx"


def _src() -> str:
    return convert_file(REFERENCE, fmt="py")


def _cached_traces() -> list[tuple[list[float], list[float]]]:
    """Mathcad's cached ``<ml:Trace2dResult>`` data as (x, y) per trace.

    Each result holds two ``<ml:DataVectors>``: the range points (the x axis)
    then the values (the y axis).
    """
    result_xml = load_mcdx(REFERENCE).result_xml or ""
    vectors = [
        json.loads(m)
        for m in re.findall(
            r"<ml:DataVectors[^>]*>(\[.*?\])</ml:DataVectors>", result_xml, re.S
        )
    ]
    return list(zip(vectors[0::2], vectors[1::2]))


def _rendered_traces() -> dict[str, "tuple[np.ndarray, np.ndarray]"]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.close("all")
    namespace: dict = {}
    exec(compile(_src(), "<plotting-wo-var>", "exec"), namespace)  # noqa: S102
    lines = {
        line.get_label(): (line.get_xdata(), line.get_ydata())
        for fig in map(plt.figure, plt.get_fignums())
        for ax in fig.axes
        for line in ax.get_lines()
        if len(line.get_xdata()) > 2  # skip the axhline/axvline guides
    }
    plt.close("all")
    return lines


# ---------------------------------------------------------------------------
# The emitted code


def test_implicit_domain_is_built_not_read():
    """``x`` is never defined in the sheet, so the domain array is emitted."""
    src = _src()
    assert "_domain_x = plot_domain(-10.0, 10.0, 499)" in src
    assert "plot_domain" in src.split("from mcad2py.runtime import ")[1].splitlines()[0]
    # Both axes go through the invented array; nothing reads a bare ``x``.
    assert "plot_axis(_domain_x, None)" in src
    assert "sample(lambda x: sin(x), _domain_x)" in src
    assert "sample(lambda x: x / 2, _domain_x)" in src
    assert "sample(lambda x: cos(x), _domain_x)" in src


def test_invented_variable_does_not_leak_into_the_sheet():
    """Mathcad invents the variable for the plot alone -- it must not become a
    worksheet name the regions below could pick up."""
    namespace: dict = {}
    import matplotlib

    matplotlib.use("Agg")
    exec(compile(_src(), "<plotting-wo-var>", "exec"), namespace)  # noqa: S102
    assert "x" not in namespace
    assert "_domain_x" in namespace


def test_legend_names_the_function_not_the_axis_expression():
    """With an implicit domain the x axis is itself an expression (``x/2``), so
    the legend has to read off y -- the function actually being plotted."""
    assert set(_rendered_traces()) == {"sin(x)", "cos(x)"}


# ---------------------------------------------------------------------------
# Rendered curves vs Mathcad's cached sample


def test_traces_match_mathcads_cached_sample():
    rendered = _rendered_traces()
    cached = _cached_traces()
    assert len(cached) == 2

    for label, (cx, cy) in zip(("sin(x)", "cos(x)"), cached):
        x, y = rendered[label]
        assert len(x) == len(cx) == 499
        assert np.allclose(x, cx, rtol=0, atol=1e-12), label
        assert np.allclose(y, cy, rtol=0, atol=1e-12), label


def test_axis_expression_scales_the_domain_but_not_the_function():
    """``x/2`` vs ``cos(x)``: the curve is drawn over -5..5, yet ``cos`` still
    sees the free variable's full -10..10 (``cos(x)``, not ``cos(x/2)``)."""
    x, y = _rendered_traces()["cos(x)"]
    assert math.isclose(float(x.min()), -5.0, abs_tol=1e-12)
    assert math.isclose(float(x.max()), 5.0, abs_tol=1e-12)
    assert np.allclose(y, np.cos(np.asarray(x) * 2), rtol=0, atol=1e-12)
    # cos(x/2) over the same axis would be a different curve entirely.
    assert not np.allclose(y, np.cos(x), rtol=0, atol=1e-6)


def test_domain_interval_is_the_free_variables_not_the_axis():
    """The 499-point -10..10 belongs to ``x``; the first trace plots it bare."""
    x, _ = _rendered_traces()["sin(x)"]
    assert math.isclose(float(x.min()), -10.0, abs_tol=1e-12)
    assert math.isclose(float(x.max()), 10.0, abs_tol=1e-12)
    assert math.isclose(float(x[1] - x[0]), 20 / 498, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# When *not* to invent a domain


def _synthetic(body: str) -> ir.Worksheet:
    return parse_worksheet(
        '<worksheet xmlns="http://schemas.mathsoft.com/worksheet50" '
        'xmlns:ml="http://schemas.mathsoft.com/math50">'
        f"<regions>{body}</regions></worksheet>"
    )


def _plot(
    x_eqs: list[str], y_eqs: list[str], top: str = "100", x_domain: str = ""
) -> str:
    def equations(maths: list[str]) -> str:
        return "<plotEquations>" + "".join(
            f"<plotEquation><math>{m}</math>"
            "<math><ml:placeholder /></math></plotEquation>"
            for m in maths
        ) + "</plotEquations>"

    return (
        f'<region top="{top}" left="0"><plot><xyPlot><axes>'
        f"<xAxis>{equations(x_eqs)}{x_domain}</xAxis>"
        f"<yAxis>{equations(y_eqs)}</yAxis>"
        "</axes></xyPlot></plot></region>"
    )


def _xy_domain(start: str, end: str) -> str:
    """An ``<xyDomain>`` holding the two axis-limit ``<math>``s."""
    return (
        '<xyDomain scale-type="linear" auto-scale="true">'
        f"<startValue>{start}</startValue><endValue>{end}</endValue></xyDomain>"
    )


_AUTO = _xy_domain("<ml:placeholder />", "<ml:placeholder />")


_ID = '<ml:id xml:space="preserve">{}</ml:id>'
_SIN = (
    '<ml:apply><ml:id labels="FUNCTION" label-is-contextual="true" '
    'xml:space="preserve">sin</ml:id>' + _ID + "</ml:apply>"
)


def _vector(name: str, top: str) -> str:
    return (
        f'<region top="{top}" left="0"><math><ml:define>'
        f'<ml:id labels="VARIABLE">{name}</ml:id>'
        '<ml:matrix rows="2" cols="1"><ml:real>1</ml:real><ml:real>2</ml:real>'
        "</ml:matrix></ml:define></math></region>"
    )


def _only_plot(ws: ir.Worksheet) -> ir.Plot:
    plots = [r for r in ws.regions if isinstance(r, ir.Plot)]
    assert len(plots) == 1
    return plots[0]


def test_defined_vectors_keep_their_parametric_plot():
    """A parametric plot -- both axes real data vectors -- has no free name, so
    nothing is invented and it still plots the vectors directly."""
    ws = _synthetic(
        _vector("X", "10")
        + _vector("Y", "20")
        + _plot([_ID.format("X")], [_ID.format("Y")])
    )
    plot = _only_plot(ws)
    assert plot.domain is None
    assert plot.implicit_domain is None


def test_two_free_names_is_not_a_function_plot():
    ws = _synthetic(_plot([_ID.format("u")], [_SIN.format("v")]))
    plot = _only_plot(ws)
    assert plot.domain is None
    assert plot.implicit_domain is None


def test_a_name_defined_below_the_plot_is_not_in_scope():
    """Mathcad reads top-to-bottom, so a definition *under* the plot doesn't
    reach it -- the variable is free there and gets the default interval."""
    ws = _synthetic(
        _plot([_ID.format("x")], [_SIN.format("x")], top="10")
        + _vector("x", "900")
    )
    plot = _only_plot(ws)
    assert plot.domain == "x"
    assert plot.implicit_domain == (-10.0, 10.0, 499)


@pytest.mark.parametrize(
    "definition",
    [
        # A plain define above the plot.
        '<region top="10" left="0"><math><ml:define>'
        '<ml:id labels="VARIABLE">x</ml:id><ml:real>3</ml:real>'
        "</ml:define></math></region>",
        # A range define -- the ordinary explicit plotting variable.
        '<region top="10" left="0"><math><ml:define>'
        '<ml:id labels="VARIABLE">x</ml:id><ml:range><ml:real>0</ml:real>'
        "<ml:real>10</ml:real></ml:range></ml:define></math></region>",
    ],
    ids=["scalar", "range"],
)
def test_a_defined_name_is_never_given_an_invented_domain(definition):
    plot = _only_plot(_synthetic(definition + _plot([_ID.format("x")], [_SIN.format("x")])))
    assert plot.implicit_domain is None


def test_a_constant_in_the_expression_is_not_a_second_free_name():
    """``π``/``e`` are still bare identifiers in the IR (codegen is what turns
    them into ``math.pi``/``math.e``), so ``sin(π·x)`` must read as *one* free
    variable, not two."""
    times_pi = (
        "<ml:apply><ml:mult />" + _ID.format("π") + _ID.format("x") + "</ml:apply>"
    )
    plot = _only_plot(
        _synthetic(
            _plot(
                [_ID.format("x")],
                ['<ml:apply><ml:id labels="FUNCTION" label-is-contextual="true" '
                 f"xml:space=\"preserve\">sin</ml:id>{times_pi}</ml:apply>"],
            )
        )
    )
    assert plot.domain == "x"
    assert plot.implicit_domain == (-10.0, 10.0, 499)


# ---------------------------------------------------------------------------
# -10..10 is the *default*, not the rule: author-set x-axis limits replace it.


def test_author_set_axis_limits_become_the_domain():
    """Setting the x-axis limits re-samples the free variable over exactly
    those -- pinned by ``incomplete_ifs.mcdx``, whose -7..1 limits give a
    cached trace of 499 points from -7 to 1 (see test_incomplete_ifs.py)."""
    ws = _synthetic(
        _plot(
            [_ID.format("x")],
            [_SIN.format("x")],
            x_domain=_xy_domain("<ml:real>-7</ml:real>", "<ml:real>1</ml:real>"),
        )
    )
    plot = _only_plot(ws)
    assert plot.x_limits == (-7.0, 1.0)
    assert plot.implicit_domain == (-7.0, 1.0, 499)


def test_a_negated_limit_is_read():
    """A limit may reach the IR as ``<neg>`` over a literal rather than a
    signed literal, depending on how it was typed."""
    neg_two = "<ml:apply><ml:neg /><ml:real>2</ml:real></ml:apply>"
    plot = _only_plot(
        _synthetic(
            _plot(
                [_ID.format("x")],
                [_SIN.format("x")],
                x_domain=_xy_domain(neg_two, "<ml:real>4</ml:real>"),
            )
        )
    )
    assert plot.implicit_domain == (-2.0, 4.0, 499)


@pytest.mark.parametrize(
    "x_domain",
    [
        pytest.param("", id="no-xyDomain"),
        pytest.param(_AUTO, id="placeholder-limits"),
        # Not a plain number: no sample pins what Mathcad does, so default.
        pytest.param(
            _xy_domain(
                '<ml:id xml:space="preserve">a</ml:id>', "<ml:real>4</ml:real>"
            ),
            id="expression-limit",
        ),
    ],
)
def test_without_author_set_limits_the_default_interval_stands(x_domain):
    """An auto-scaling axis stores its *drawn* window in the ``start``/``end``
    attributes while the ``<xyDomain>`` values stay placeholders. That window
    is computed from the data, so it must not be read back as the domain --
    ``plotting-wo-var.mcdx``'s second trace draws -5..5 from a full -10..10."""
    plot = _only_plot(
        _synthetic(_plot([_ID.format("x")], [_SIN.format("x")], x_domain=x_domain))
    )
    assert plot.x_limits is None
    assert plot.implicit_domain == (-10.0, 10.0, 499)


def test_limits_do_not_touch_an_explicit_range_domain():
    """Axis limits only decide the interval Mathcad *invents*. A plot with a
    real plotting variable is sampled over that variable, whatever the axis
    window is set to."""
    range_def = (
        '<region top="10" left="0"><math><ml:define>'
        '<ml:id labels="VARIABLE">x</ml:id><ml:range><ml:real>0</ml:real>'
        "<ml:real>10</ml:real></ml:range></ml:define></math></region>"
    )
    plot = _only_plot(
        _synthetic(
            range_def
            + _plot(
                [_ID.format("x")],
                [_SIN.format("x")],
                x_domain=_xy_domain("<ml:real>2</ml:real>", "<ml:real>3</ml:real>"),
            )
        )
    )
    assert plot.domain == "x"
    assert plot.implicit_domain is None


def test_runtime_plot_domain_defaults_match_the_cache():
    from mcad2py.runtime import plot_domain

    values = plot_domain()
    cached_x = _cached_traces()[0][0]
    assert np.allclose(values, cached_x, rtol=0, atol=1e-12)
