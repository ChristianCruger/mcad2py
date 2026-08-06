"""Tests for Mathcad difference equations (``references/difference_eq.mcdx``).

A *seeded iteration* is how Mathcad writes a recurrence: a seed pins one
element, a range variable drives the steps, and the equation assigns into an
element **slot** whose index is offset from that variable::

    guess[0]   := 30
    i          := 0 .. N
    guess[i+1] := (guess[i] + X/guess[i])/2      # Newton's square root of X

Before this, the parser only understood ``X[i] :=`` with a *bare* range variable
as the index (:class:`ir.IndexAssign`, one parallel ``index_build`` pass). The
offset index makes each step depend on the last, so the whole family routes to
:class:`ir.Recurrence` and emits a sequential loop instead. The sheet exercises
all three shapes it comes in:

* a **scalar** recurrence -- ``guess`` above, converging on ``sqrt(700)``;
* a **system** solved simultaneously -- an SIR epidemic model whose four
  vectors (``inf``/``sus``/``dec``/``rec``) each read the *previous* step, so
  the step's values must be staged before any of them is written back;
* a **matrix** recurrence -- ``V^<k> := A·V^<k-1>``, a Markov chain, which
  writes two-subscript slots ``V[i, k]`` and so builds a matrix column by
  column.

Two supporting behaviours fall out of the same sheet and are pinned here too:
the loop variable must stay **function-local** (the sheet keeps using ``i`` as a
range below the recurrence), and a plot whose two axes end up different lengths
(``guess`` has one more element than the index range it is plotted against) is
NaN-padded the way Mathcad's own cached trace is.
"""

import math
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from conftest import flat, reference, run_sheet
from mcad2py import ir
from mcad2py.convert import convert_worksheet
from mcad2py.loader import load_mcdx

REFERENCE = reference("difference_eq")

# Mathcad's cached results (result.xml), in echo order.
SQRT_700 = 26.457513110645905
CACHED = [
    # guess = -- ten elements: the seed plus one per step of i := 0..8.
    ("guess", [30, 26.666666666666664, 26.458333333333336, 26.457513123359583]
     + [SQRT_700] * 6),
    # (guess[i])^2 - X = -- the residual over the *range*, so nine elements.
    ("residual", [200, 11.111111111110972, 0.043402777777941992,
                  6.7274459070176817e-07, 0, 0, 0, 0, 0]),
    # V^<8> = -- the Markov chain's final state.
    ("V_final", [6.0167627, 29.124149800000009, 14.859087500000001]),
    # V^T = -- the whole history, nine columns of three (listed column-major).
    ("V_history", [
        10, 8, 7.1, 6.65, 6.3980000000000006, 6.2423, 6.13907, 6.067556, 6.0167627,
        25, 26.5, 27.400000000000002, 27.985000000000003, 28.385500000000004,
        28.668100000000003, 28.870825000000004, 29.017520500000007,
        29.124149800000009,
        15, 15.5, 15.5, 15.365, 15.2165, 15.089599999999999, 14.990105,
        14.9149235, 14.859087500000001,
    ]),
]


def _cached_traces() -> dict[str, list[float]]:
    """The SIR system's four cached plot traces, keyed by the vector they show.

    The system is only ever *plotted*, never echoed, so its cached values live
    in the plot's ``<ml:Trace2dResult>`` rather than in a ``<ml:result>``.
    """
    root = ET.fromstring(
        zipfile.ZipFile(REFERENCE).read("mathcad/result.xml").decode("utf-8")
    )
    order = ["inf", "sus", "dec", "rec"]  # the plot's trace order
    traces: dict[str, list[float]] = {}
    for data in root:
        points = data.find(".//{*}ResultPoints/{*}DataVectors")
        if points is None or data.get("result-id") not in ("13", "14", "15", "16"):
            continue
        traces[order[len(traces)]] = [
            float(v) for v in points.text.strip("[]").split(",")
        ]
    return traces


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(REFERENCE)


def test_sheet_runs_end_to_end(sheet):
    src, _, echoed = sheet
    assert "TODO unsupported" not in src
    assert len(echoed) == len(CACHED)


def test_sheet_matches_cached_results(sheet):
    """Every echo reproduces Mathcad's cached value."""
    _, _, echoed = sheet
    for index, (label, expected) in enumerate(CACHED):
        got = flat(echoed[index])
        want = np.asarray(expected, dtype=float)
        assert got.shape == want.shape, f"{label}: shape {got.shape} vs {want.shape}"
        assert np.allclose(got, want, rtol=1e-12, atol=1e-9), f"{label}: {got} != {want}"


def test_seeded_iteration_converges_to_the_square_root(sheet):
    """``guess[i+1] := (guess[i] + X/guess[i])/2`` is Newton's method for
    ``sqrt(700)``: it must be *sequential*, since every step reads the element
    the step before wrote. Ten elements for nine steps -- the seed plus one per
    value of ``i := 0..8``, which is why ``guess`` outruns its index range."""
    _, ns, _ = sheet
    guess = flat(ns["guess"])
    assert len(guess) == 10
    assert math.isclose(guess[0], 30)  # the seed, untouched
    assert math.isclose(guess[-1], math.sqrt(700), rel_tol=1e-15)


def test_the_loop_variable_does_not_leak_out_of_the_recurrence(sheet):
    """The recurrence goes inside a ``def`` precisely so its ``for i in …``
    stays local: the sheet uses ``i`` as a *range* again just below (``i_range[i]
    := i``), which a bare loop would have left bound to the last scalar index."""
    src, ns, _ = sheet
    assert "def _recur_guess(_idx, guess):" in src
    assert list(flat(ns["i"])) == list(range(9))  # still the whole range
    assert list(flat(ns["i_range"])) == list(range(9))


def test_system_of_difference_equations_updates_simultaneously(sheet):
    """The SIR model's four vectors are one Mathcad equation with a matrix on
    each side. Every right-hand side reads time ``τ``, so the step is staged in
    a tuple before anything is written back -- computing them one at a time
    would feed ``sus[τ+1]`` the ``inf[τ+1]`` this same step just produced."""
    src, ns, _ = sheet
    assert "def _recur_inf_sus_dec_rec(_idx, inf, sus, dec, rec):" in src
    assert "_step = (" in src
    traces = _cached_traces()
    for name, want in traces.items():
        got = flat(ns[name])
        assert got.shape == (len(want),), f"{name}: {got.shape} vs {len(want)}"
        assert np.allclose(got, want, rtol=1e-12, atol=1e-9), name
    # The population is conserved: everyone is susceptible, infected, deceased
    # or recovered at every step.
    total = sum(flat(ns[n]) for n in ("inf", "sus", "dec", "rec"))
    assert np.allclose(total, 22050.0, rtol=1e-12)


def test_matrix_recurrence_writes_two_subscript_slots(sheet):
    """``V^<k> := A·V^<k-1>`` names three ``V[i, k]`` slots, so the recurrence
    grows a *matrix* one column per step -- and the ``·`` has to have been
    resolved to a matrix product by the shape pass, not a scalar multiply."""
    src, ns, _ = sheet
    assert "matmul(A, matcol(V, k - 1))" in src
    assert "V = vec_set(V, (0, k), _step[0])" in src
    v = np.asarray(getattr(ns["V"], "magnitude", ns["V"]), dtype=float)
    assert v.shape == (3, 9)  # the seed column plus one per k := 1..8
    # A is a stochastic matrix, so each column keeps the initial total of 50.
    assert np.allclose(v.sum(axis=0), 50.0, rtol=1e-12)


def test_recurrence_targets_are_parsed_as_element_slots():
    """The IR distinguishes a difference equation from the parallel
    ``X[i] := …`` build: an offset or constant index yields a
    :class:`ir.Recurrence`, and only a bare range variable an
    :class:`ir.IndexAssign`."""
    ws = convert_worksheet(load_mcdx(REFERENCE))
    recurrences = [r for r in ws.regions if isinstance(r, ir.Recurrence)]
    assert len(recurrences) == 6  # one seed and one step per example

    seeds = [r for r in recurrences if r.index is None]
    steps = [r for r in recurrences if r.index is not None]
    assert len(seeds) == 3 and len(steps) == 3
    assert [s.index.py for s in steps] == ["i", "tau", "k"]
    # Each seed is the first write to its vectors, so it creates them.
    assert [s.create for s in seeds] == [
        ["guess"], ["inf", "sus", "dec", "rec"], ["V"]
    ]
    # ``V``'s seed names the same base three times; only the first creates it.
    assert [(t.base.py, t.col is not None) for t in seeds[2].targets] == [
        ("V", True)
    ] * 3
    # ``i_range[i] := i`` alongside them stays the parallel form.
    assert any(isinstance(r, ir.IndexAssign) for r in ws.regions)


def test_plot_pads_a_trace_whose_axes_are_different_lengths(sheet):
    """``guess`` (10 values) is plotted against ``i_range`` (9). Mathcad extends
    the short axis with a blank -- its cached trace is literally
    ``[0,1,…,8,NaN]`` -- where matplotlib would reject the mismatch."""
    from mcad2py.runtime import plot_trace

    src, _, _ = sheet
    assert "_ax.plot(*plot_trace(" in src
    x, y = plot_trace(np.arange(9.0), np.arange(10.0))
    assert x.shape == y.shape == (10,)
    assert math.isnan(x[-1]) and y[-1] == 9.0
