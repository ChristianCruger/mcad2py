"""Tests for the command-line entry point and the package's public surface.

The failure paths matter more than they look: pointing the converter at the
wrong file is the single most likely thing a new user does, and until these
were fixed a corrupt download (or a legacy ``.xmcd``, which is a different
format entirely) produced a raw ``zipfile.BadZipFile`` traceback rather than a
sentence explaining the problem.
"""

import zipfile
from pathlib import Path

import pytest

import mcad2py
from mcad2py.cli import main
from mcad2py.loader import load_mcdx

REFERENCE = Path(__file__).parent.parent / "references" / "plain_concrete_cohesion.mcdx"


# ---------------------------------------------------------------------------
# Failure paths: a message, an exit code, and no traceback
# ---------------------------------------------------------------------------


@pytest.fixture
def not_a_zip(tmp_path: Path) -> Path:
    """A file with a .mcdx name that isn't a zip archive at all."""
    path = tmp_path / "corrupt.mcdx"
    path.write_text("this is not a zip archive")
    return path


@pytest.fixture
def zip_without_worksheet(tmp_path: Path) -> Path:
    """A valid zip that isn't a Mathcad package."""
    path = tmp_path / "wrong.mcdx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("hello.txt", "hi")
    return path


def test_missing_file_reports_the_path(tmp_path, capsys):
    code = main(["convert", str(tmp_path / "nope.mcdx"), "-f", "py", "-o", "-"])
    err = capsys.readouterr().err
    assert code == 1
    assert "no such file" in err
    assert "nope.mcdx" in err
    assert "Traceback" not in err


def test_a_non_zip_is_a_clean_error_not_a_traceback(not_a_zip, capsys):
    """Regression: ``zipfile.BadZipFile`` used to escape the CLI uncaught."""
    code = main(["convert", str(not_a_zip), "-f", "py", "-o", "-"])
    err = capsys.readouterr().err
    assert code == 1
    assert "not a readable .mcdx file" in err
    assert "Traceback" not in err and "BadZipFile" not in err
    # The message names the likeliest cause rather than leaving the user guessing.
    assert ".xmcd" in err


def test_a_zip_without_a_worksheet_is_a_clean_error(zip_without_worksheet, capsys):
    code = main(["convert", str(zip_without_worksheet), "-f", "py", "-o", "-"])
    err = capsys.readouterr().err
    assert code == 1
    assert "is this a Mathcad Prime file?" in err
    assert "Traceback" not in err


def test_loader_raises_the_documented_exception_types(not_a_zip, tmp_path):
    """``ValueError`` for an unreadable package, ``FileNotFoundError`` for a
    missing path -- what the CLI (and any library caller) catches."""
    with pytest.raises(ValueError, match="not a readable"):
        load_mcdx(not_a_zip)
    with pytest.raises(FileNotFoundError, match="no such file"):
        load_mcdx(tmp_path / "nope.mcdx")


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_convert_to_stdout(capsys):
    code = main(["convert", str(REFERENCE), "-f", "py", "-o", "-"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith('"""Auto-generated from a Mathcad worksheet by mcad2py."""')
    assert "f_cd = 30 * ureg.MPa / 1.5" in out


def test_convert_writes_a_file_and_infers_the_format(tmp_path):
    out = tmp_path / "sheet.py"
    assert main(["convert", str(REFERENCE), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith('"""Auto-generated')

    notebook = tmp_path / "sheet.ipynb"
    assert main(["convert", str(REFERENCE), "-o", str(notebook)]) == 0
    assert '"cells"' in notebook.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_version_is_not_a_second_source_of_truth():
    """``__version__`` is read from the installed distribution's metadata, so it
    can't drift from pyproject.toml (which a release may stamp)."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        assert mcad2py.__version__ == version("mcad2py")
    except PackageNotFoundError:  # a bare source tree
        assert mcad2py.__version__ == "0.0.0.dev0"


def test_public_api():
    assert set(mcad2py.__all__) == {"convert_file", "convert_worksheet", "__version__"}
    assert callable(mcad2py.convert_file)
    assert callable(mcad2py.convert_worksheet)
