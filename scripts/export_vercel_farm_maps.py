"""Export render-ready farm map JSON files for the Vercel app.

The Streamlit app keeps the raw polygon files and applies map helpers at render
time.  This script materializes those helper results so the Vercel app can
render maps without repeating the geometry/styling calculations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_template import (
    MAP_SMALL_MAP_ZOOM,
    MAP_STROKE_HOVER_WIDTH,
    MAP_STROKE_PINNED_WIDTH,
    MAP_STROKE_REFERENCE_WIDTH,
    MAP_STROKE_SMALL_MAP_MULTIPLIER,
    MAP_STROKE_WIDTH,
)


DEFAULT_OUTPUT_DIR = Path(r"D:\Vercel_app\src\data\farm-maps")
DEFAULT_FILL = "#3f4652"
MAP_BACKGROUND = "#1a1a2e"
MAP_STROKE = "rgba(255,255,255,0.5)"
MAP_SELECTED_STROKE = "#ffffff"

FARM_MAPS = [
    {
        "farm_id": "126",
        "farm_name": "Farm 126",
        "source": "farm_126_polygons.json",
        "default_width": 2382,
        "default_height": 1684,
        "map_zoom": 1.0,
    },
    {
        "farm_id": "157",
        "farm_name": "Farm 157",
        "source": "farm_157_polygons.json",
        "default_width": 4000,
        "default_height": 2250,
        "map_zoom": None,
    },
    {
        "farm_id": "195",
        "farm_name": "Farm 195",
        "source": "farm_195_polygons.json",
        "default_width": 1683,
        "default_height": 1190,
        "map_zoom": None,
    },
]


def point_in_polygon(px: float, py: float, pts: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def geometric_centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    if len(pts) < 3:
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for i, (x0, y0) in enumerate(pts):
        x1, y1 = pts[(i + 1) % len(pts)]
        cross = x0 * y1 - x1 * y0
        signed_area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    signed_area *= 0.5
    if abs(signed_area) < 1e-10:
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    return cx / (6 * signed_area), cy / (6 * signed_area)


def pole_of_inaccessibility(pts: list[tuple[float, float]]) -> tuple[float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    best = (sum(xs) / len(xs), sum(ys) / len(ys))
    best_dist = 0.0
    steps = 12

    for xi in range(steps + 1):
        for yi in range(steps + 1):
            px = min_x + (max_x - min_x) * xi / steps
            py = min_y + (max_y - min_y) * yi / steps
            if not point_in_polygon(px, py, pts):
                continue

            min_edge_dist = float("inf")
            for i, (x1, y1) in enumerate(pts):
                x2, y2 = pts[(i + 1) % len(pts)]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0:
                    dist = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
                else:
                    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
                    dist = ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5
                min_edge_dist = min(min_edge_dist, dist)

            if min_edge_dist > best_dist:
                best_dist = min_edge_dist
                best = (px, py)

    return best


def best_label_pos(pts: list[tuple[float, float]]) -> tuple[float, float]:
    cx, cy = geometric_centroid(pts)
    if point_in_polygon(cx, cy, pts):
        return cx, cy
    return pole_of_inaccessibility(pts)


def style_for_image_width(img_w: int, map_zoom: float | None) -> dict:
    label_font_size = max(10, int(img_w * 47 / MAP_STROKE_REFERENCE_WIDTH))
    stroke_scale = (img_w / MAP_STROKE_REFERENCE_WIDTH) if img_w else 1
    if img_w and img_w < MAP_STROKE_REFERENCE_WIDTH:
        stroke_scale *= MAP_STROKE_SMALL_MAP_MULTIPLIER

    resolved_zoom = map_zoom or (MAP_SMALL_MAP_ZOOM if img_w and img_w < MAP_STROKE_REFERENCE_WIDTH else 1)

    return {
        "background": MAP_BACKGROUND,
        "defaultFill": DEFAULT_FILL,
        "fillOpacity": 0.45,
        "selectedFillOpacity": 0.85,
        "stroke": MAP_STROKE,
        "selectedStroke": MAP_SELECTED_STROKE,
        "strokeWidth": round(MAP_STROKE_WIDTH * stroke_scale, 2),
        "hoverStrokeWidth": round(MAP_STROKE_HOVER_WIDTH * stroke_scale, 2),
        "selectedStrokeWidth": round(MAP_STROKE_PINNED_WIDTH * stroke_scale, 2),
        "labelFontSize": label_font_size,
        "labelFontWeight": 700,
        "labelStroke": "#111827",
        "labelStrokeWidth": max(4, round(label_font_size * 0.15, 2)),
        "mapZoom": resolved_zoom,
    }


def build_render_ready_map(config: dict) -> dict:
    with (ROOT / config["source"]).open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    img_w = int(raw.get("image_width") or config["default_width"])
    img_h = int(raw.get("image_height") or config["default_height"])
    style = style_for_image_width(img_w, config.get("map_zoom"))
    viewbox_w = img_w / style["mapZoom"]
    viewbox_h = img_h / style["mapZoom"]
    viewbox_x = (img_w - viewbox_w) / 2
    viewbox_y = (img_h - viewbox_h) / 2

    lots = []
    for lot in raw.get("lots", []):
        points = [{"x": float(p["x"]), "y": float(p["y"])} for p in lot.get("points", [])]
        tuple_points = [(p["x"], p["y"]) for p in points]
        label_x, label_y = best_label_pos(tuple_points)
        lots.append(
            {
                "name": str(lot["name"]),
                "points": points,
                "pointsString": " ".join(f'{p["x"]:g},{p["y"]:g}' for p in points),
                "label": {"x": round(label_x), "y": round(label_y)},
                "fill": DEFAULT_FILL,
            }
        )

    return {
        "schemaVersion": 1,
        "generator": "scripts/export_vercel_farm_maps.py",
        "source": config["source"],
        "farmId": config["farm_id"],
        "farmName": config["farm_name"],
        "image": {"width": img_w, "height": img_h},
        "viewport": {
            "x": round(viewbox_x, 2),
            "y": round(viewbox_y, 2),
            "width": round(viewbox_w, 2),
            "height": round(viewbox_h, 2),
            "aspectRatio": round(viewbox_w / viewbox_h, 6) if viewbox_h else 1,
        },
        "style": style,
        "lots": lots,
    }


def export_maps(output_dir: Path, farms: Iterable[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for config in farms:
        data = build_render_ready_map(config)
        output_path = output_dir / f"farm_{config['farm_id']}_map.json"
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {output_path} ({len(data['lots'])} lots)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where render-ready map JSON files will be written.",
    )
    args = parser.parse_args()
    export_maps(args.output_dir, FARM_MAPS)


if __name__ == "__main__":
    main()
