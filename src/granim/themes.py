"""Built-in themes; a custom theme overlays tokens on a base."""
from __future__ import annotations

_TOKENS = {
    "--bg", "--surface", "--node-fill", "--node-stroke", "--node-text", "--edge",
    "--edge-flip", "--state-active", "--state-visited", "--state-frontier",
    "--state-done", "--badge-bg", "--badge-text", "--pulse", "--font", "--unit",
    "--radius",
}

THEMES = {
    "dark": {
        "--bg": "#000000", "--surface": "#101014", "--node-fill": "#0c1418",
        "--node-stroke": "#58C4DD", "--node-text": "#ffffff", "--edge": "#b9b9b9",
        "--edge-flip": "#FFE45C", "--state-active": "#FFE45C",
        "--state-visited": "#58C4DD", "--state-frontier": "#83C167",
        "--state-done": "#9A72AC", "--badge-bg": "#FFE45C", "--badge-text": "#1a1404",
        "--pulse": "#FFE45C", "--font": "'Segoe UI', system-ui, sans-serif",
        "--unit": "56", "--radius": "8",
    },
    "light": {
        "--bg": "#fafbfd", "--surface": "#ffffff", "--node-fill": "#eef6f9",
        "--node-stroke": "#1d7d9c", "--node-text": "#10222b", "--edge": "#5b6470",
        "--edge-flip": "#c98a00", "--state-active": "#c98a00",
        "--state-visited": "#1d7d9c", "--state-frontier": "#3d8b4f",
        "--state-done": "#7c5e9e", "--badge-bg": "#c98a00", "--badge-text": "#ffffff",
        "--pulse": "#3d8b4f", "--font": "'Segoe UI', system-ui, sans-serif",
        "--unit": "56", "--radius": "8",
    },
    "contrast": {
        "--bg": "#000000", "--surface": "#101010", "--node-fill": "#101010",
        "--node-stroke": "#ffffff", "--node-text": "#ffffff", "--edge": "#dddddd",
        "--edge-flip": "#ffb000", "--state-active": "#ffb000",
        "--state-visited": "#40a0ff", "--state-frontier": "#00e070",
        "--state-done": "#d080ff", "--badge-bg": "#ffb000", "--badge-text": "#000000",
        "--pulse": "#00e070", "--font": "'Segoe UI', system-ui, sans-serif",
        "--unit": "56", "--radius": "8",
    },
}


def resolve_theme(theme) -> dict:
    from .core.recorder import GranimError

    if isinstance(theme, str):
        if theme not in THEMES:
            raise GranimError(f"unknown theme {theme!r}; one of {sorted(THEMES)}")
        return {"name": theme, "tokens": THEMES[theme]}
    if isinstance(theme, dict):
        base = theme.get("base", "dark")
        tokens = dict(THEMES[base])
        for k, v in theme.items():
            if k == "base":
                continue
            if k not in _TOKENS:
                raise GranimError(f"unknown theme token {k!r}")
            tokens[k] = v
        return {"name": "custom", "tokens": tokens}
    raise GranimError("theme must be a name or a token dict")
