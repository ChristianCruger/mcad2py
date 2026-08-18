"""A ``# TODO``/``# placeholder`` note must never break the generated module.

Such a note is a comment, so it swallows the rest of its line. That is harmless
when the note *is* the whole expression and fatal one level down, where the
closing parenthesis ends up inside the comment and nothing after it parses --
the one outcome the "unknown constructs stay visible, but the output still
loads" convention exists to prevent.

A wide interpolation worksheet hit this with a nested placeholder. There is no
fixture behind these tests because that sheet calls several functions it never
defines, so it cannot be executed or compared against ``result.xml``; the IR is
built by hand instead.
"""

from __future__ import annotations

import ast

from mcad2py import ir
from mcad2py.emit.codegen import expr_to_str

# ---------------------------------------------------------------------------
# A note nested in an expression must not close the line.


def test_a_nested_placeholder_still_parses():
    """``f(a, None  # placeholder)`` would put the ``)`` inside the comment.

    That is the one outcome the "unknown constructs stay visible but the output
    still loads" convention exists to prevent, and a trailing-note check only
    catches it when the note is the whole expression.
    """
    node = ir.Call(
        func="summation",
        args=[ir.Name(py="f", original="f"), ir.Placeholder(), ir.Placeholder()],
    )
    rendered = expr_to_str(node)
    ast.parse(rendered)  # the assertion: it is Python at all
    assert "placeholder" in rendered
    assert rendered.index("#") > rendered.index(")")


def test_a_nested_unsupported_note_survives_to_the_end_of_the_line():
    """The note is lifted, not dropped -- a silent ``None`` would be worse."""
    node = ir.Call(
        func="foo",
        args=[ir.Unsupported(note="apply/derivative"), ir.Number(value="2")],
    )
    rendered = expr_to_str(node)
    ast.parse(rendered)
    assert rendered == "foo(None, 2)  # TODO unsupported: apply/derivative"


def test_two_notes_in_one_expression_are_both_reported():
    node = ir.Call(func="foo", args=[ir.Placeholder(), ir.Unsupported(note="x")])
    rendered = expr_to_str(node)
    ast.parse(rendered)
    assert rendered == "foo(None, None)  # placeholder; TODO unsupported: x"


def test_a_top_level_note_is_unchanged():
    """The common case must render exactly as it did before the fix."""
    assert expr_to_str(ir.Unsupported(note="apply/derivative")) == (
        "None  # TODO unsupported: apply/derivative"
    )


def test_notes_do_not_leak_between_expressions():
    """The collector is per outermost call, not per module."""
    expr_to_str(ir.Unsupported(note="first"))
    assert expr_to_str(ir.Number(value="1")) == "1"
