import sys

import subprocess
from pathlib import Path

import yaml
from django.conf import settings

def build_renovation_config(floor):
    """
    Convert a Django Floor and its Rooms into a Renovation config.

    Room outlines are exported as walls. The interactive browser
    representation remains independent of this renderer.
    """

    walls = []

    width = float(floor.width)
    height = float(floor.height)

    # Outer building walls.
    walls.extend(
        [
            {
                "type": "wall",
                "pivot_point": [0, 0],
                "length": width,
                "thickness": 0.20,
            },
            {
                "type": "wall",
                "pivot_point": [0, 0],
                "length": height,
                "thickness": 0.20,
                "orientation_angle": 90,
            },
            {
                "type": "wall",
                "pivot_point": [width, 0],
                "length": height,
                "thickness": 0.20,
                "orientation_angle": 90,
            },
            {
                "type": "wall",
                "pivot_point": [0, height],
                "length": width,
                "thickness": 0.20,
            },
        ]
    )

    # Internal room boundaries.
    for room in floor.rooms.all():
        x = float(room.x)
        y = float(room.y)
        room_width = float(room.width)
        room_height = float(room.height)

        walls.extend(
            [
                {
                    "type": "wall",
                    "pivot_point": [x, y],
                    "length": room_width,
                    "thickness": 0.08,
                },
                {
                    "type": "wall",
                    "pivot_point": [x, y],
                    "length": room_height,
                    "thickness": 0.08,
                    "orientation_angle": 90,
                },
            ]
        )


    return {
        "project": {
            "dpi": 150,
            "pdf_file": None,
            "png_dir": str(
                Path(settings.MEDIA_ROOT) / "merchandise"
            ),
        },

        "default_layout": {
            "bottom_left_corner": [0, 0],
            "top_right_corner": [width, height],
            "scale_numerator": 1,
            "scale_denominator": 100,
            "grid_major_step": 1,
            "grid_minor_step": 0.1,
        },

        "reusable_elements": {
            "walls": walls,
        },

        "floor_plans": [
            {
                "title": {
                    "text": floor.name,
                    "font_size": 18,
                },

                "layout": {
                    "bottom_left_corner": [0, 0],
                    "top_right_corner": [width, height],
                },

                "inherited_elements": ["walls"],
            }
        ],
    }



def export_floor_plan(floor):
    """
    Write the generated YAML and invoke Renovation.

    Returns the generated configuration path and process result.
    """

    output_dir = Path(settings.MEDIA_ROOT) / "merchandise"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = build_renovation_config(floor)

    config_path = output_dir / f"floor_{floor.number}.yml"

    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "renovation",
            "-c",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr or "Renovation rendering failed.")

    return {
        "config": str(config_path),
        "stdout": result.stdout,
    }
