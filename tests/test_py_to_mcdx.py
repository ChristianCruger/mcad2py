"""The reverse converter (tools/py_to_mcdx.py) on small hand-written inputs.

The fixtures' round trip covers what codegen writes; these pin the shapes a
review found it read wrongly or let through when it should refuse.
"""
import sys
from pathlib import Path

import pytest

from mcad2py import ir
from mcad2py.emit.codegen import expr_to_str

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import py_to_mcdx as p  # noqa: E402


def worksheet(text: str) -> str:
    return p.build(p.read_python(text))["mathcad/worksheet.xml"]


def test_early_return_inside_a_block_keeps_its_return():
    xml = worksheet(
        "def f(n):\n"
        "    for i in arange(0, n, 1):\n"
        "        if i == 3:\n"
        "            return i\n"
        "    return -1\n")
    # The return inside the if leaves the program; the last line is implicit.
    assert xml.count("<ml:return>") == 1
    assert "<ml:then><ml:program><ml:return>" in xml


def test_negative_base_of_a_power_keeps_its_group():
    xml = worksheet("x = (-2)**2\n")
    assert "<ml:pow /><ml:parens><ml:real>-2</ml:real></ml:parens>" in xml
    # ...and the forward printer brackets it again: -2**2 is -(2**2).
    node = ir.BinOp(op="pow", left=ir.Number("-2"), right=ir.Number("2"))
    assert expr_to_str(node) == "(-2)**2"


def test_only_codegens_scale_is_a_display_scale():
    assert "<ml:unitOverride><ml:placeholder />" in worksheet("y = 10\nprint(y / (2 + 3))\n")
    assert "<ml:unitOverride><ml:apply><ml:pow />" in worksheet(
        "y = 10\nprint(y / (10**-6))\n")


def test_an_echo_is_not_merged_across_a_comment():
    regions = p.read_python("z = 1\n# Note\nprint(z)\n")
    assert [type(r).__name__ for r in regions] == ["Define", "TextRegion", "Evaluate"]


@pytest.mark.parametrize("text", [
    "print(x, end='')\n",
    "@dec\ndef f(a):\n    return a\n",
    "def f(a, b=2):\n    return a\n",
    "def f(a, /, b):\n    return a\n",
    "f = lambda *a: a\n",
    "x = range_sum(j, lambda i: i**2)\n",
    "x = NamedTuple(1)\n",
])
def test_refused(text):
    with pytest.raises((p.Refused, p.mb.Unsupported)):
        worksheet(text)


def test_malformed_input_is_an_error_not_a_traceback(tmp_path, capsys):
    src = tmp_path / "bad.py"
    src.write_text("print(disp())\n", encoding="utf-8")
    assert p.main([str(src), "-o", str(tmp_path / "bad.mcdx")]) == 1
    assert "unsupported input shape" in capsys.readouterr().err
    assert not (tmp_path / "bad.mcdx").exists()


def test_jscript_strings_are_escaped():
    assert p._js_string('3/4" bolt\\x\nnext') == '"3/4\\" bolt\\\\x\\nnext"'


def test_status_note_needs_a_number():
    assert p._STATUS_NOTE.match("Mathcad status control: the message is for the value 1.")
    assert p._STATUS_NOTE.match("Mathcad status control: the message is for the value -2.5e3.")
    assert not p._STATUS_NOTE.match(
        "Mathcad status control: the message is for the value 1+2.")
