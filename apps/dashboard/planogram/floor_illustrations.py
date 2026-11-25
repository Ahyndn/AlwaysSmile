"""Schematic architectural overlays for the illustrative floor plans.

All coordinates use the same units as the floor and room configurations.
This module does not represent verified construction or survey information.
"""

from typing import Any, Iterable


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_illustration(floor: Any, rooms: Iterable[Any]) -> dict[str, Any]:
    """Build an illustrative architectural overlay from configured room rectangles.

    Supports either dictionaries or objects for floors and rooms. Room geometry
    must use x, y, width, and height fields, in the same units as the floor.
    """
    floor_width = _number(
        floor.get("width") if isinstance(floor, dict) else getattr(floor, "width", 0)
    )
    floor_height = _number(
        floor.get("height") if isinstance(floor, dict) else getattr(floor, "height", 0)
    )

    if floor_width <= 0 or floor_height <= 0:
        return {"illustrative": True, "features": []}

    features: list[dict[str, Any]] = []

    def add(kind: str, x: float, y: float, width: float, height: float) -> None:
        if width <= 0 or height <= 0:
            return
        features.append({
            "kind": kind,
            "x": round(x, 3),
            "y": round(y, 3),
            "width": round(width, 3),
            "height": round(height, 3),
        })

    valid_rooms = []
    for room in rooms:
        get = room.get if isinstance(room, dict) else lambda key, default=None: getattr(room, key, default)
        x = _number(get("x"))
        y = _number(get("y"))
        width = _number(get("width"))
        height = _number(get("height"))
        if width <= 0 or height <= 0:
            continue
        valid_rooms.append((x, y, width, height))

        # Room outline and a schematic opening on its lower edge.
        add("wall", x, y, width, height)
        opening_width = min(width * 0.14, 1.2)
        if width > opening_width * 2:
            add("opening", x + width * 0.5 - opening_width * 0.5,
                y + height - 0.04, opening_width, 0.08)

    # A simple dashed circulation spine, placed clear of the outer edge.
    if valid_rooms:
        left = min(room[0] for room in valid_rooms)
        right = max(room[0] + room[2] for room in valid_rooms)
        top = min(room[1] for room in valid_rooms)
        bottom = max(room[1] + room[3] for room in valid_rooms)
        corridor_width = max(0.08, min(floor_width, floor_height) * 0.012)
        add("circulation", left, (top + bottom) / 2 - corridor_width / 2,
            right - left, corridor_width)

    # Repeated illustrative window marks along the exterior edges.
    window_size = max(0.12, min(floor_width, floor_height) * 0.025)
    for x, y, width, height in valid_rooms:
        if y <= 0.05:
            add("window", x + width * 0.35, 0, window_size, 0.06)
        if y + height >= floor_height - 0.05:
            add("window", x + width * 0.60, floor_height - 0.06, window_size, 0.06)
        if x <= 0.05:
            add("window", 0, y + height * 0.35, 0.06, window_size)
        if x + width >= floor_width - 0.05:
            add("window", floor_width - 0.06, y + height * 0.60, 0.06, window_size)

    return {"illustrative": True, "features": features}
