#!/usr/bin/python3
# File: gen_worldmap.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Regenerates the world map used by the MiAZYearReport plugin.
#
# The report is a self-contained page: it cannot fetch anything at load time, so
# the map ships as a small SVG with one path per country, keyed by its ISO
# 3166-1 alpha-2 code (the same code MiAZ stores in the filename). This script
# builds that SVG from Natural Earth 1:110m country outlines (public domain) and
# writes it into the plugin's static directory.
#
# Run it only when the map has to be rebuilt:
#   python scripts/devel/gen_worldmap.py
#
# It needs network access; the generated file is committed, so a normal build
# never runs this.

import json
import os
import sys
import urllib.request

SOURCE = ('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/'
          'master/geojson/ne_110m_admin_0_countries.geojson')

TARGET = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'data', 'resources', 'plugins',
    'MiAZYearReport', 'static', 'worldmap.svg')

# Natural Earth leaves ISO_A2 as "-99" for a handful of entries. ISO_A2_EH
# covers most of them; the rest are patched by name.
BY_NAME = {
    'France': 'FR',
    'Norway': 'NO',
    'Kosovo': 'XK',
    'Northern Cyprus': 'CY',
    'Somaliland': 'SO',
}

# Antarctica is a wide white band that adds size and says nothing about who
# sends documents, and the far north is mostly empty ice.
SKIP = {'AQ'}
LAT_MIN, LAT_MAX = -60.0, 84.0

WIDTH = 1000.0
PRECISION = 1

# A country whose drawn box is smaller than this (in viewBox units) also gets a
# marker circle, so it stays findable when it is shaded.
PIN_BELOW = 9.0

# Robinson projection tables, one entry per 5 degrees of latitude.
PLEN = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427,
        0.9216, 0.8962, 0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732,
        0.6213, 0.5722, 0.5322]
PDFE = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340,
        0.4958, 0.5571, 0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936,
        0.9394, 0.9761, 1.0000]


def robinson(lon, lat):
    """Longitude and latitude in degrees to unprojected Robinson x, y."""
    sign = -1.0 if lat < 0 else 1.0
    lat = min(abs(lat), 90.0)
    index = lat / 5.0
    low = int(index)
    if low >= 18:
        low, ratio = 17, 1.0
    else:
        ratio = index - low
    x_scale = PLEN[low] + (PLEN[low + 1] - PLEN[low]) * ratio
    y_scale = PDFE[low] + (PDFE[low + 1] - PDFE[low]) * ratio
    return 0.8487 * x_scale * (lon * 3.141592653589793 / 180.0), 1.3523 * y_scale * sign


def rings(geometry):
    """Every outer and inner ring of a Polygon or MultiPolygon."""
    kind = geometry.get('type')
    if kind == 'Polygon':
        return list(geometry['coordinates'])
    if kind == 'MultiPolygon':
        return [ring for polygon in geometry['coordinates'] for ring in polygon]
    return []


def main():
    print(f"Downloading {SOURCE}")
    with urllib.request.urlopen(SOURCE, timeout=60) as response:
        data = json.load(response)

    # Project everything first so the drawing box comes from the real extent.
    projected = {}
    for feature in data['features']:
        props = feature['properties']
        code = props.get('ISO_A2_EH') or props.get('ISO_A2') or ''
        if code in ('', '-99'):
            code = BY_NAME.get(props.get('NAME', ''), '')
        if not code or code in SKIP:
            continue
        for ring in rings(feature['geometry']):
            points = [robinson(lon, max(min(lat, LAT_MAX), LAT_MIN)) for lon, lat in ring]
            projected.setdefault(code, []).append(points)

    xs = [x for parts in projected.values() for ring in parts for x, _y in ring]
    ys = [y for parts in projected.values() for ring in parts for _x, y in ring]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    scale = WIDTH / (max_x - min_x)
    height = (max_y - min_y) * scale

    def place(point):
        x, y = point
        # SVG y grows downwards, the projection grows northwards.
        return (round((x - min_x) * scale, PRECISION),
                round((max_y - y) * scale, PRECISION))

    paths = []
    pins = []
    for code in sorted(projected):
        parts = []
        box = []
        for ring in projected[code]:
            drawn = None
            chunk = []
            for point in ring:
                x, y = place(point)
                # Drop points that land on the previous one at this precision.
                if drawn == (x, y):
                    continue
                drawn = (x, y)
                box.append((x, y))
                chunk.append(f"{x},{y}" if chunk else f"M{x},{y}")
            if len(chunk) > 3:
                parts.append(chunk[0] + 'L' + 'L'.join(chunk[1:]) + 'Z')
        if not parts:
            continue
        paths.append(f'<path id="{code}" d="{"".join(parts)}"/>')

        # Countries too small to see at this scale (Luxembourg, Malta, the
        # island states) get a marker the report can switch on when they hold
        # documents, so a shaded country is never invisible.
        xs_c = [x for x, _y in box]
        ys_c = [y for _x, y in box]
        box_width = max(xs_c) - min(xs_c)
        box_height = max(ys_c) - min(ys_c)
        if max(box_width, box_height) < PIN_BELOW:
            pins.append(f'<circle id="pin-{code}" class="pin" '
                        f'cx="{round((max(xs_c) + min(xs_c)) / 2, PRECISION)}" '
                        f'cy="{round((max(ys_c) + min(ys_c)) / 2, PRECISION)}" r="4"/>')

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {round(WIDTH)} {round(height)}" '
        # The ranked country list beside the map carries the same values as
        # text, so the outlines add nothing for a screen reader.
        'aria-hidden="true" class="worldmap">\n'
        '<!-- Country outlines from Natural Earth 1:110m (public domain, '
        'naturalearthdata.com), projected with Robinson and generated by '
        'scripts/devel/gen_worldmap.py. Each path id is an ISO 3166-1 alpha-2 '
        'code. -->\n'
        + '\n'.join(paths) + '\n<g class="pins">' + ''.join(pins) + '</g>\n</svg>\n'
    )

    with open(TARGET, 'w', encoding='utf-8') as fh:
        fh.write(svg)
    print(f"{len(paths)} countries, {len(pins)} pins, {len(svg) / 1024:.0f} KB -> {TARGET}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
