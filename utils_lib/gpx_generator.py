"""Convert an Apple plist track dump to GPX - mirrors GPXGenerator.java.

The Java original used a very line-granular state machine: skip until
`<array>`, then for each record consume fixed line offsets to read altitude,
date, latitude, longitude. We reproduce that exact layout expectation rather
than parse the plist as XML, so behaviour matches the original input format.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List


def _strip_tag(line: str, start: int, end_offset: int) -> str:
    """Java did line.substring(6, len-7); we mirror those literal offsets."""
    return line[start: len(line) - end_offset]


def parse_plist_lines(lines: Iterable[str]) -> List[dict]:
    """Yield track points from the plist line stream.

    Expected per-record layout (after `<array>`):
        <dict>
            <key>altitude</key>
            <real>...</real>
            <key>date</key>
            <string>...</string>
            <key>latitude</key>
            <real>...</real>
            <key>longitude</key>
            <real>...</real>
        </dict>
    """
    lines = list(lines)
    i = 0
    while i < len(lines) and lines[i].strip() != "<array>":
        i += 1
    i += 1  # consume <array>
    points: List[dict] = []
    while i < len(lines) and lines[i] != "</array>":
        i += 1  # blank / <dict> line
        altitude_line = lines[i].strip() if i < len(lines) else ""
        i += 1  # skip key line
        i += 1  # skip <key>date</key>... actually layout: next is the value line?
        # The Java original read altitude as the line immediately after the first
        # skipped `nextLine()`. We replicate the exact consume pattern:
        #   nextLine(); // skip one
        #   altitude = nextLine().strip();
        #   nextLine();
        #   date = nextLine().strip();
        #   nextLine();
        #   lat = nextLine().strip();
        #   nextLine();
        #   lon = nextLine().strip();
        #   nextLine();
        # Rewind to follow that precisely:
        # Re-do from current i.
        # (We were inside the loop; the exact offsets are encoded below.)
        break

    # Re-implement the Java consume pattern directly on the index.
    i = 0
    while i < len(lines) and lines[i].strip() != "<array>":
        i += 1
    i += 1
    points = []
    while i < len(lines) and lines[i] != "</array>":
        i += 1  # skip one line
        altitude_string = lines[i].strip() if i < len(lines) else ""
        i += 1
        i += 1  # skip key/value separator
        date_string = lines[i].strip() if i < len(lines) else ""
        i += 1
        i += 1
        latitude_string = lines[i].strip() if i < len(lines) else ""
        i += 1
        i += 1
        longitude_string = lines[i].strip() if i < len(lines) else ""
        i += 1
        i += 1

        # Java substring offsets:
        #   altitude: substring(6, len-7)  -> strips <real>...</real>
        #   date:     substring(8, len-9)  -> strips <string>...</string>
        #   latitude/longitude: substring(6, len-7)
        altitude = float(altitude_string[6: len(altitude_string) - 7])
        date_str = date_string[8: len(date_string) - 9]
        latitude = float(latitude_string[6: len(latitude_string) - 7])
        longitude = float(longitude_string[6: len(longitude_string) - 7])

        # Parse "yyyy-MM-dd HH:mm:ss Z" and emit ISO-8601 UTC.
        dt = None
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            dt = None
        points.append({
            "lat": latitude,
            "lon": longitude,
            "ele": altitude,
            "time": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else "",
        })
    return points


def points_to_gpx(points: List[dict]) -> str:
    out: List[str] = ["<gpx>", "<trk>", "<trkseg>"]
    for p in points:
        out.append(f'<trkpt lat="{p["lat"]:.6f}" lon="{p["lon"]:.6f}">')
        out.append(f'<ele>{p["ele"]:.6f}</ele>')
        out.append(f'<time>{p["time"]}</time>')
        out.append("</trkpt>")
    out += ["</trkseg>", "</trk>", "</gpx>"]
    return "\n".join(out) + "\n"


def convert(input_path: str, output_path: str) -> int:
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    points = parse_plist_lines(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(points_to_gpx(points))
    return len(points)
