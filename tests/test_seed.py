"""``references/seed.mcdx`` -- Mathcad's random stream, reproduced exactly.

Prime's generator is the Microsoft C runtime ``rand()``; ``Seed(n)`` is
``srand(n)`` and returns the *previous* state; one ``runif`` draw takes two
``rand()`` calls packed into 30 bits; ``rnorm`` is Kinderman-Monahan ratio of
uniforms with the exact ``sqrt(8/e)`` constant. On top of those the sheet
fingerprints the whole ``r*`` family: each block is ``Seed(1)``, one draw, then
``runif(4, 0, 1)``, and where those four uniforms sit in the stream counts what
the draw consumed. Every block below is checked to the last bit.

The sheet also carries three constructs this fixture is the first to reach: a
bare ``Seed(1)`` region (a call with no ``=``, which must not print), a bare
call as a non-final line of a program body (which must not become an implicit
return), and a whole-column write ``M^<i> :=`` inside a program.
"""

from __future__ import annotations

import numpy as np
import pytest

from conftest import cached_results, flat, reference, result_refs, run_sheet
from mcad2py import ir  # noqa: F401 -- parse_worksheet returns these
from mcad2py.emit.codegen import expr_to_str
from mcad2py.emit.py_backend import _render_region
from mcad2py.loader import load_mcdx
from mcad2py.parser.regions import parse_worksheet

SHEET = reference("seed")


@pytest.fixture(scope="module")
def sheet():
    return run_sheet(SHEET)


@pytest.fixture(scope="module")
def cache():
    return cached_results(SHEET)


@pytest.fixture(scope="module")
def blocks(sheet, cache):
    """``region-id`` -> ``(source text, echoed value, cached value)``.

    The sheet is a long catalogue of near-identical three-region blocks, and it
    keeps growing, so indexing echoes by position would break on every edit.
    Pairing them by ``region-id`` instead means a new block simply joins the
    table. Alignment comes from the backend itself: a region echoes once per
    ``print(`` in the lines it renders.
    """
    _source, _ns, echoed = sheet
    refs = result_refs(SHEET)
    ws = parse_worksheet(load_mcdx(SHEET).worksheet_xml)
    out, at = {}, 0
    for region in ws.regions:
        lines = _render_region(region)
        prints = sum(line.lstrip().startswith("print(") for line in lines)
        rid = getattr(getattr(region, "source", None), "region_id", None)
        if prints == 1 and rid is not None:
            value = getattr(region, "value", None)
            out[rid] = (
                expr_to_str(value) if value is not None else "",
                echoed[at],
                cache.get(refs.get(rid, "")),
            )
        at += prints
    assert at == len(echoed), (at, len(echoed))
    return out


def exact(blocks, region_id, expected_text=None):
    """Assert one region's echo equals Mathcad's cached value, bit for bit."""
    text, got, want = blocks[region_id]
    if expected_text is not None:
        assert text == expected_text
    assert want is not None, f"region {region_id} has no cached result"
    assert flat(got).tolist() == want


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


def test_seed_returns_the_previous_state(blocks):
    """``Seed(n) =`` echoes the generator's previous 32-bit state.

    Six consecutive ``Seed`` regions make this unambiguous: after a ``Seed(1)``
    the next ``Seed(1)`` echoes 1, and after a ``Seed(2)`` the next echoes 2, so
    the number is the state left behind rather than a status code or the new
    seed. The first of them echoes the end state of the run above it.
    """
    for region_id in (19, 20, 21, 22, 23, 25):
        exact(blocks, region_id)


def test_rnorm_matches_mathcad(blocks):
    """One ``rnorm`` draw, then the uniforms that follow it in the stream.

    The four trailing uniforms are what identified the method: they are
    ``U[4..7]``, so one normal draw consumed exactly four uniforms -- one
    rejected ratio-of-uniforms pair, then an accepted one.
    """
    exact(blocks, 16, "rnorm(1, 0, 1)")
    exact(blocks, 17, "runif(4, 0, 1)")


@pytest.mark.parametrize(
    "draw, trailing, call",
    [
        (26, 27, "rF(1, 1, 1)"),
        (29, 30, "rgeom(1, 0.5)"),
        (32, 33, "rgamma(1, 0.5)"),
        (35, 36, "rhypergeom(1, 0, 1, 1)"),
        (38, 39, "rbeta(1, 1, 1)"),
        (41, 42, "rcauchy(1, 0, 1)"),
        (44, 45, "rbinom(1, 1, 0.5)"),
        (47, 48, "rexp(1, 0.5)"),
        (50, 51, "rchisq(1, 0.5)"),
        (53, 54, "rlogis(1, 0, 1)"),
        (56, 57, "rnbinom(1, 1, 0.5)"),
        (59, 60, "rpois(1, 1)"),
        (65, 66, "rweibull(1, 1)"),
    ],
)
def test_distribution_draw_and_its_stream_position(blocks, draw, trailing, call):
    """Each ``r*`` block: the value, and where the stream resumes after it.

    The trailing ``runif(4, 0, 1)`` is the stricter half. A helper can return
    the right number from the wrong uniforms, but then the four that follow
    land at the wrong offset and every later draw on the sheet is wrong -- so
    this pins the consumption, not just the value.
    """
    exact(blocks, draw, call)
    exact(blocks, trailing, "runif(4, 0, 1)")


@pytest.mark.xfail(reason="rt draws a seventh uniform whose role is unresolved", strict=True)
def test_rt_matches_mathcad(blocks):
    """``rt`` is the one member of the family still on NumPy.

    Its cached value is exactly ``z1 / z2`` -- two normals, six uniforms -- but
    the block consumed **seven**. The extra uniform is drawn after the value is
    formed, and one cached ``rt`` cannot tell whether it flips the sign or is
    discarded, so guessing would silently negate half of all draws.
    """
    exact(blocks, 62, "rt(1, 1)")
    exact(blocks, 63, "runif(4, 0, 1)")


def test_first_runif_block_diverges_by_mathcad_recalculation_order(blocks):
    """A documented divergence, and the one place the sheet is not exact.

    Region 13 is a bare ``Seed(1)``; region 14 draws ``runif(20, 0, 1)`` right
    below it. Mathcad's cache for region 14 does **not** start at state 1: it
    starts 5556 ``rand()`` calls in, which is exactly one ``Seed(1)`` plus
    ``rnorm(1000)`` -- one pass of the ``Same`` program above it. So Prime ran
    the bare ``Seed`` region *before* the program rather than in reading order.
    Generated code runs in reading order, so it starts at state 1 instead.

    The divergence is confined to these two regions: region 15 reseeds, and
    every block after it is exact.
    """
    _text, got, want = blocks[14]
    assert flat(got).tolist() != want
    from mcad2py.runtime import Seed, rnorm, runif

    Seed(1)
    rnorm(1000, 0, 2)
    assert runif(20, 0, 1).tolist() == want


def test_program_reseeds_each_pass(sheet, blocks):
    """The whole point of the sheet: ``Seed`` inside a program repeats a set."""
    _source, ns, _echoed = sheet
    columns = ns["Same"](1000, 0, 2)
    assert columns.shape == (1000, 3)
    mags = np.asarray(getattr(columns, "magnitude", columns), dtype=float)
    assert np.array_equal(mags[:, 0], mags[:, 1])
    assert np.array_equal(mags[:, 0], mags[:, 2])
    # And that repeated set is Mathcad's own.
    exact(blocks, 9)


def test_histogram_of_the_repeated_set(blocks):
    """``hist`` over the seeded sample, and its peak bin count."""
    exact(blocks, 11)


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


# ---------------------------------------------------------------------------
# The ``r*`` family, at arms the worksheet never reaches. Every block on the
# sheet draws **one** value at **one** parameter set, so the array call, a
# dimensioned parameter, and every shape ``_gamma`` splits other than the one
# each block happened to use are all untested by the checks above.


def _stream_positions(call, *args):
    """``(value, uniforms consumed)`` for one helper call from ``Seed(1)``."""
    from mcad2py.runtime import Seed, runif

    Seed(1)
    reference_stream = runif(24, 0, 1).tolist()
    Seed(1)
    value = call(*args)
    tail = runif(1, 0, 1)[0]
    return value, reference_stream.index(tail)


def test_draw_count_is_honoured_and_the_stream_is_shared():
    """``m`` draws come off one stream, not ``m`` restarts of it."""
    from mcad2py.runtime import Seed, rexp

    Seed(5)
    many = rexp(4, 1)
    Seed(5)
    one_at_a_time = [rexp(1, 1)[0] for _ in range(4)]
    assert many.tolist() == one_at_a_time
    assert len(set(many.tolist())) == 4


def test_parameters_may_arrive_as_pint_quantities():
    """A rate or shape can reach a helper as a dimensionless quantity."""
    from mcad2py.runtime import Seed, rexp
    from mcad2py.units import ureg

    Seed(9)
    plain = rexp(3, 2.0)
    Seed(9)
    quantity = rexp(3, ureg.Quantity(2.0, "dimensionless"))
    assert quantity.tolist() == plain.tolist()


def test_an_unreduced_ratio_parameter_is_reduced_first():
    """``float()`` on a ``mm/m`` ratio would read 2000, not 2."""
    from mcad2py.runtime import Seed, rexp
    from mcad2py.units import ureg

    Seed(9)
    plain = rexp(3, 2.0)
    Seed(9)
    ratio = rexp(3, ureg.Quantity(2000, "mm") / ureg.Quantity(1, "m"))
    assert ratio.tolist() == plain.tolist()


def test_rexp_and_rweibull_share_one_inverse_cdf():
    """Both are ``-ln(u)`` reshaped, so both take exactly one uniform."""
    from mcad2py.runtime import Seed, rexp, rweibull

    Seed(4)
    e = rexp(6, 0.25)
    Seed(4)
    w = rweibull(6, 1.0)
    assert e.tolist() == pytest.approx((w * 4.0).tolist())


def test_a_whole_gamma_shape_is_a_sum_of_exponentials():
    """``_gamma(3)`` is three ``rexp(1)`` draws off the same stream.

    The sheet only ever reaches shape 1, 1/2 and 1/4, one piece at a time, so
    the decomposition itself is pinned here rather than by a cached number.
    """
    from mcad2py.runtime import Seed, rexp, rgamma

    Seed(11)
    combined = rgamma(1, 3)[0]
    Seed(11)
    parts = rexp(3, 1)
    assert combined == pytest.approx(float(np.sum(parts)), rel=0, abs=1e-15)


def test_a_half_gamma_shape_is_a_squared_normal():
    """``_gamma(1/2)`` is ``z**2 / 2``, which makes ``chisq(1)`` exactly ``z**2``."""
    from mcad2py.runtime import Seed, rchisq, rgamma, rnorm

    Seed(12)
    g = rgamma(1, 0.5)[0]
    Seed(12)
    c = rchisq(1, 1)[0]
    Seed(12)
    z = rnorm(1, 0, 1)[0]
    assert g == z * z / 2.0
    assert c == z * z


def test_a_mixed_gamma_shape_uses_both_pieces():
    """Shape 2.5 is two exponentials plus a squared normal, in that order."""
    from mcad2py.runtime import Seed, rexp, rgamma, rnorm

    Seed(13)
    mixed = rgamma(1, 2.5)[0]
    Seed(13)
    whole = float(np.sum(rexp(2, 1)))
    half = rnorm(1, 0, 1)[0] ** 2 / 2.0
    assert mixed == pytest.approx(whole + half, rel=0, abs=1e-15)


def test_rbinom_takes_one_uniform_whatever_n_is():
    """Inverse CDF, not ``n`` Bernoulli trials -- the sheet only reaches n=1."""
    from mcad2py.runtime import rbinom

    value, consumed = _stream_positions(rbinom, 1, 20, 0.3)
    assert consumed == 1
    assert 0 <= value[0] <= 20


def test_rbinom_covers_the_whole_support():
    """The walk must reach ``n`` at the top of the range and 0 at the bottom."""
    from mcad2py.runtime import Seed, rbinom

    Seed(2)
    draws = rbinom(400, 4, 0.5)
    assert set(draws.tolist()) == {0.0, 1.0, 2.0, 3.0, 4.0}
    assert float(np.mean(draws)) == pytest.approx(2.0, abs=0.2)


def test_rnbinom_and_rpois_return_whole_numbers():
    """Both are counts; a float array of integral values is what Mathcad shows."""
    from mcad2py.runtime import Seed, rnbinom, rpois

    Seed(6)
    counts = np.concatenate([rpois(50, 3.0), rnbinom(50, 2, 0.4)])
    assert np.array_equal(counts, np.floor(counts))
    assert counts.min() >= 0


def test_rbeta_stays_inside_the_unit_interval():
    """Two gamma draws over their sum, for shapes the sheet never uses."""
    from mcad2py.runtime import Seed, rbeta

    Seed(8)
    draws = rbeta(200, 2.0, 0.5)
    assert draws.min() > 0.0 and draws.max() < 1.0
    assert float(np.mean(draws)) == pytest.approx(2.0 / 2.5, abs=0.1)


def test_rlnorm_is_the_exponential_of_rnorm():
    """No cached ``rlnorm`` block exists, so this pins it against ``rnorm``."""
    from mcad2py.runtime import Seed, rlnorm, rnorm

    Seed(14)
    log_normal = rlnorm(5, 1.0, 0.5)
    Seed(14)
    normal = rnorm(5, 1.0, 0.5)
    assert log_normal.tolist() == np.exp(normal).tolist()


def test_rcauchy_and_rlogis_are_centred_and_scaled():
    """The sheet only calls both at loc=0, s=1."""
    from mcad2py.runtime import Seed, rcauchy, rlogis

    Seed(15)
    base = rcauchy(5, 0, 1)
    Seed(15)
    moved = rcauchy(5, 3, 2)
    assert moved.tolist() == pytest.approx((3 + 2 * base).tolist())

    Seed(16)
    base = rlogis(5, 0, 1)
    Seed(16)
    moved = rlogis(5, 3, 2)
    assert moved.tolist() == pytest.approx((3 + 2 * base).tolist())
