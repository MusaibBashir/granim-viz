"""Renders a timeline into a single self-contained HTML file."""
from __future__ import annotations

import json
from pathlib import Path

_ASSETS = Path(__file__).parent / "player"


def render_html(timeline: dict) -> str:
    data = json.dumps(timeline, separators=(",", ":"), sort_keys=True)
    data = data.replace("</", "<\\/")  # protect the embedding <script> tag
    html = (_ASSETS / "template.html").read_text(encoding="utf-8")
    return (html
            .replace("{{TITLE}}", _esc(timeline["meta"]["title"]))
            .replace("{{CSS}}", (_ASSETS / "player.css").read_text(encoding="utf-8"))
            .replace("{{DATA}}", data)
            .replace("{{JS}}", (_ASSETS / "player.js").read_text(encoding="utf-8")))


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def display_inline(html: str) -> None:
    """Jupyter inline via iframe; plain print fallback elsewhere."""
    try:
        from IPython.display import HTML, display
    except ImportError:
        raise RuntimeError("rec.show() needs IPython; use rec.save(path) instead") from None
    srcdoc = html.replace("&", "&amp;").replace('"', "&quot;")
    display(HTML(f'<iframe srcdoc="{srcdoc}" style="width:100%;height:620px;'
                 f'border:none;border-radius:12px"></iframe>'))
