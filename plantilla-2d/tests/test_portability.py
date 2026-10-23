"""Static guards: the cross-platform rules stay true as the code grows (no Mac-only calls, explicit UTF-8...)."""

import ast
import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_FILES = sorted([*(ROOT / "reels").glob("*.py"), *(ROOT / ".claude").rglob("*.py")])
SKIP_OPEN_OWNERS = {"wave", "tarfile", "zipfile", "gzip", "bz2", "lzma", "Image"}


def _text_io_without_encoding(path: Path) -> list[int]:
    """Line numbers of text reads/writes/subprocess calls that rely on the OS default encoding."""
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        kws = {k.arg for k in node.keywords}
        if "encoding" in kws:
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text"):
            bad.append(node.lineno)
        elif isinstance(f, ast.Attribute) and f.attr == "open" and not (isinstance(f.value, ast.Name) and f.value.id in SKIP_OPEN_OWNERS):
            mode = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "r"
            if isinstance(mode, str) and "b" not in mode:
                bad.append(node.lineno)
        elif isinstance(f, ast.Name) and f.id == "open":
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
            if isinstance(mode, str) and "b" not in mode:
                bad.append(node.lineno)
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "subprocess":
            if any(k.arg in ("text", "universal_newlines") and getattr(k.value, "value", None) is True for k in node.keywords):
                bad.append(node.lineno)
    return bad


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_text_io_is_explicit_utf8(path):
    assert _text_io_without_encoding(path) == [], "add encoding=\"utf-8\" (Windows defaults to cp1252)"


def _code_lines(path: Path) -> list[tuple[int, str]]:
    return [(i, line) for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if not line.lstrip().startswith("#")]


@pytest.mark.parametrize("pattern,why", [
    (r"\[\s*[\"']npx[\"']", "npx is npx.cmd on Windows: use system.remotion_cmd()"),
    (r"[\"']/dev/null", "use system.DEVNULL (os.devnull)"),
    (r"\[\s*[\"']open[\"']\s*,", "use system.open_path() (open is Mac-only)"),
    (r"/Applications/", "Blender paths live in system.blender_candidates()"),
    (r"Library/Mobile Documents", "no iCloud-only features"),
    (r"launchctl|osascript", "no macOS-only automation"),
])
def test_no_platform_specific_calls_outside_system(pattern, why):
    hits = [f"{p.relative_to(ROOT)}:{i}" for p in PY_FILES if p.name != "system.py" for i, line in _code_lines(p)
            if re.search(pattern, line)]
    assert hits == [], why


def test_requires_python_312():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.12"' in text
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"



def test_no_personal_references_in_template():
    pattern = re.compile(r"tarritoai|tarrito\.ia|(?-i:/Users/)", re.I)
    # Names from the original project, stored as hashes so the guard does not spell them out.
    banned = {'1275302e01cef631', 'd37c5e7961d0ed50', '04334bf216661ddc'}

    def personal(line: str) -> bool:
        words = re.findall(r"\w+", line.lower())
        return bool(pattern.search(line)) or any(hashlib.sha256(w.encode()).hexdigest()[:16] in banned for w in words)

    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".md", ".json", ".toml"}
             and not {"node_modules", ".venv", "episodes", ".cache", "tests", "voz", "generado"} & set(p.relative_to(ROOT).parts)
             and p.name not in {"package-lock.json", "uv.lock"}]
    hits = [f"{p.relative_to(ROOT)}:{i}" for p in files for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if personal(line)]
    assert hits == []


def test_remotion_is_called_through_node_never_npx():
    text = (ROOT / "reels" / "render.py").read_text(encoding="utf-8")
    assert "system.remotion_cmd" in text and '"npx"' not in text


def test_remotion_versions_match_the_3d_factory():
    """Same Remotion as the 3D factory: npm reuses its download cache and both behave the same."""
    import json

    mine = json.loads((ROOT / "remotion" / "package.json").read_text(encoding="utf-8"))["dependencies"]
    other = ROOT.parent / "plantilla" / "remotion" / "package.json"
    if other.exists():  # inside the repo (in a student's folder the 3D template is not next to it)
        assert mine == json.loads(other.read_text(encoding="utf-8"))["dependencies"]
