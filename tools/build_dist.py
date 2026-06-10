"""Zero-dependency sdist + wheel builder (PEP 427 / PEP 625).

`python -m build` produces equivalent output; this is the offline path.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "granim-viz"  # import name stays "granim"
NORM = DIST_NAME.replace("-", "_")
SUMMARY = ("Write the algorithm, get the animation. Instrumented data structures"
            " that compile your real Python code into interactive HTML visualizations."
            "Built for educational purposes")


def version() -> str:
    m = re.search(r'__version__ = "([^"]+)"',
                  (ROOT / "src/granim/__init__.py").read_text(encoding="utf-8"))
    assert m, "no __version__ in granim/__init__.py"
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{m.group(1)}"' in py, "pyproject version out of sync"
    assert f'name = "{DIST_NAME}"' in py, "pyproject name out of sync"
    return m.group(1)


def metadata(ver: str) -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    fields = [
        ("Metadata-Version", "2.1"),
        ("Name", DIST_NAME),
        ("Version", ver),
        ("Summary", SUMMARY),
        ("Author-email", "Musaib Bashir <musaibbashir.24@kgpian.iitkgp.ac.in>"),
        ("License", "MIT"),
        ("Project-URL", "Homepage, https://github.com/musaibbashir/granim-viz"),
        ("Project-URL", "Repository, https://github.com/musaibbashir/granim-viz"),
        ("Project-URL", "Issues, https://github.com/musaibbashir/granim-viz/issues"),
        ("Keywords", "visualization,animation,algorithms,data-structures,"
                     "education,linked-list,graph,tree,manim,teaching"),
        ("Classifier", "Development Status :: 4 - Beta"),
        ("Classifier", "Intended Audience :: Developers"),
        ("Classifier", "Intended Audience :: Education"),
        ("Classifier", "License :: OSI Approved :: MIT License"),
        ("Classifier", "Operating System :: OS Independent"),
        ("Classifier", "Programming Language :: Python :: 3"),
        ("Classifier", "Programming Language :: Python :: 3.10"),
        ("Classifier", "Programming Language :: Python :: 3.11"),
        ("Classifier", "Programming Language :: Python :: 3.12"),
        ("Classifier", "Programming Language :: Python :: 3.13"),
        ("Classifier", "Topic :: Education"),
        ("Classifier", "Topic :: Scientific/Engineering :: Visualization"),
        ("Classifier", "Topic :: Software Development :: Debuggers"),
        ("Requires-Python", ">=3.10"),
        ("Provides-Extra", "dev"),
        ("Requires-Dist", 'pytest; extra == "dev"'),
        ("Requires-Dist", 'ruff; extra == "dev"'),
        ("Description-Content-Type", "text/markdown"),
        ("License-File", "LICENSE"),
    ]
    head = "\n".join(f"{k}: {v}" for k, v in fields)
    return f"{head}\n\n{readme}"


def pkg_files() -> list[Path]:
    out = []
    for p in sorted((ROOT / "src/granim").rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            out.append(p)
    return out


def build_wheel(ver: str, dist: Path) -> Path:
    tag = "py3-none-any"
    info = f"{NORM}-{ver}.dist-info"
    whl = dist / f"{NORM}-{ver}-{tag}.whl"
    record_rows = []

    def add(zf, arcname: str, data: bytes):
        zi = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))  # reproducible
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, data)
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(data).digest()).rstrip(b"=").decode()
        record_rows.append((arcname, f"sha256={digest}", str(len(data))))

    with zipfile.ZipFile(whl, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pkg_files():
            add(zf, f"granim/{f.relative_to(ROOT / 'src/granim').as_posix()}",
                f.read_bytes())
        add(zf, f"{info}/METADATA", metadata(ver).encode())
        add(zf, f"{info}/WHEEL",
            f"Wheel-Version: 1.0\nGenerator: granim-build (0.1)\n"
            f"Root-Is-Purelib: true\nTag: {tag}\n".encode())
        add(zf, f"{info}/licenses/LICENSE", (ROOT / "LICENSE").read_bytes())
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for row in record_rows:
            w.writerow(row)
        w.writerow((f"{info}/RECORD", "", ""))
        zi = zipfile.ZipInfo(f"{info}/RECORD", date_time=(2026, 1, 1, 0, 0, 0))
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, buf.getvalue())
    return whl


def build_sdist(ver: str, dist: Path) -> Path:
    base = f"{NORM}-{ver}"
    sdist = dist / f"{base}.tar.gz"
    include = [ROOT / "pyproject.toml", ROOT / "LICENSE", ROOT / "README.md",
               ROOT / "CHANGELOG.md",
               *sorted(p for p in (ROOT / "docs").glob("*.md")
                       if p.name != "INTERVIEW_PREP.md"),  # personal, not shipped
               *pkg_files(),
               *sorted((ROOT / "tests").glob("*.py")),
               *sorted((ROOT / "examples").glob("*.py"))]
    with tarfile.open(sdist, "w:gz") as tf:
        def add_bytes(arcname: str, data: bytes):
            ti = tarfile.TarInfo(f"{base}/{arcname}")
            ti.size = len(data)
            ti.mtime = 1767225600  # 2026-01-01, reproducible
            ti.mode = 0o644
            tf.addfile(ti, io.BytesIO(data))

        add_bytes("PKG-INFO", metadata(ver).encode())
        for f in include:
            add_bytes(f.relative_to(ROOT).as_posix(), f.read_bytes())
    return sdist


def main():
    ver = version()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    whl = build_wheel(ver, dist)
    sd = build_sdist(ver, dist)
    print(f"built {whl.name} ({whl.stat().st_size:,} bytes)")
    print(f"built {sd.name} ({sd.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
