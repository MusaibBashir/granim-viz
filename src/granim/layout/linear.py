"""Grid and chain layouts."""
from __future__ import annotations

CELL_DX = 1.15
LIST_DX = 1.6
ROW_DY = 2.2
WRAP = 10


def array_layout(members: list[str]) -> dict[str, tuple[float, float]]:
    return {m: (i * CELL_DX, 0.0) for i, m in enumerate(members)}


def matrix_layout(members: list[str], cols: int) -> dict[str, tuple[float, float]]:
    return {m: ((i % cols) * CELL_DX, (i // cols) * CELL_DX)
            for i, m in enumerate(members)}


def list_layout(members: list[str]) -> dict[str, tuple[float, float]]:
    """Creation-order chain; positions are stable during pointer surgery."""
    pos = {}
    for i, m in enumerate(members):
        row, col = divmod(i, WRAP)
        if row % 2:
            col = WRAP - 1 - col  # snake: odd rows run right-to-left
        pos[m] = (col * LIST_DX, row * ROW_DY)
    return pos
