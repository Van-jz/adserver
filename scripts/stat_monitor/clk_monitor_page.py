#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Run commands from the repository root.
#
# Start:
#   python3 scripts/stat_monitor/clk_monitor_page.py --data-dir /data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat
#   Open http://<server-ip>:18080/
#
# Start in background:
#   nohup python3 scripts/stat_monitor/clk_monitor_page.py --data-dir /data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat > logs/clk_monitor_page.log 2>&1 &
#
# Stop:
#   If running in the foreground, press Ctrl+C.
#   If running in the background, find the process and kill it:
#     ps -ef | grep scripts/stat_monitor/clk_monitor_page.py
#     kill <pid>
"""Tiny web page for comparing the latest two clk_stat files."""

import argparse
import csv
import html
import os
import posixpath
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse


DEFAULT_DATA_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18080
DEFAULT_REFRESH = 1800
ALLOWED_SUFFIXES = (".csv", ".tsv", ".txt", ".log")
NO_CLICKS_MARKER = "No clicks in the current window."


@dataclass
class ClickCell:
    present: bool = False
    value: Optional[float] = None
    raw: str = ""

    @property
    def valid(self) -> bool:
        return self.present and self.value is not None


@dataclass
class ParsedStatFile:
    path: str
    name: str
    mtime: float
    rows: Dict[str, ClickCell] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TotalClickPoint:
    path: str
    name: str
    stat_time: datetime
    total: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a simple clk_stat diff monitor page.")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="directory containing clk_stat files")
    parser.add_argument("--host", default=DEFAULT_HOST, help="listen host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="listen port")
    parser.add_argument("--refresh", type=int, default=DEFAULT_REFRESH, help="page auto refresh seconds")
    return parser.parse_args()


def is_candidate_file(name: str, path: str) -> bool:
    if not os.path.isfile(path):
        return False
    lower_name = name.lower()
    return lower_name.endswith(ALLOWED_SUFFIXES) or lower_name.startswith("clk_stat.")


def stat_time_from_name(name: str) -> Optional[datetime]:
    if not name.startswith("clk_stat."):
        return None

    stamp = name[len("clk_stat.") :]
    digits = "".join(ch for ch in stamp if ch.isdigit())
    if len(digits) < 12:
        return None

    try:
        return datetime.strptime(digits[:12], "%Y%m%d%H%M")
    except ValueError:
        return None


def stat_time_for_path(path: str) -> datetime:
    return stat_time_from_name(os.path.basename(path)) or datetime.fromtimestamp(os.path.getmtime(path))


def candidate_files(data_dir: str) -> List[Tuple[datetime, float, str]]:
    entries: List[Tuple[datetime, float, str]] = []
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        if is_candidate_file(name, path):
            entries.append((stat_time_for_path(path), os.path.getmtime(path), path))
    return entries


def latest_two_files(data_dir: str) -> List[str]:
    entries = candidate_files(data_dir)
    entries.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [path for _, _, path in entries[:2]]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return f.read()


def parse_number(raw: str) -> Optional[float]:
    value = raw.strip()
    if not value:
        return None
    normalized = value.replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def add_click(rows: Dict[str, ClickCell], bundle: str, raw_clicks: str) -> Optional[str]:
    bundle = bundle.strip()
    if not bundle:
        return "empty bundle skipped"

    parsed = parse_number(raw_clicks)
    existing = rows.get(bundle)
    if parsed is None:
        rows[bundle] = ClickCell(present=True, value=None, raw=raw_clicks)
        return f"bundle {bundle} has non-numeric clicks: {raw_clicks!r}"

    if existing and existing.valid:
        rows[bundle] = ClickCell(present=True, value=existing.value + parsed, raw=str(existing.value + parsed))
    else:
        rows[bundle] = ClickCell(present=True, value=parsed, raw=raw_clicks)
    return None


def choose_delimiter(header_line: str, sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        counts = {delimiter: header_line.count(delimiter) for delimiter in (",", "\t", ";")}
        return max(counts, key=counts.get)


def parse_delimited_text(text: str, path: str) -> ParsedStatFile:
    lines = text.splitlines()
    first_nonempty = next((line for line in lines if line.strip()), "")
    if not first_nonempty:
        raise ValueError("file is empty")

    delimiter = choose_delimiter(first_nonempty, "\n".join(lines[:20]))
    reader = csv.DictReader(lines, delimiter=delimiter)
    fieldnames = reader.fieldnames or []
    normalized = {name.strip().lower(): name for name in fieldnames if name is not None}
    if "bundle" not in normalized or "clicks" not in normalized:
        raise ValueError("first row must contain columns: bundle, clicks")

    result = ParsedStatFile(path=path, name=os.path.basename(path), mtime=os.path.getmtime(path))
    bundle_column = normalized["bundle"]
    clicks_column = normalized["clicks"]
    for row_num, row in enumerate(reader, start=2):
        bundle = (row.get(bundle_column) or "").strip()
        clicks = (row.get(clicks_column) or "").strip()
        warning = add_click(result.rows, bundle, clicks)
        if warning:
            result.warnings.append(f"line {row_num}: {warning}")
    return result


def parse_plain_clk_stat_text(text: str, path: str) -> ParsedStatFile:
    lines = text.splitlines()
    result = ParsedStatFile(path=path, name=os.path.basename(path), mtime=os.path.getmtime(path))
    if any(NO_CLICKS_MARKER in line for line in lines):
        return result

    header_index = None
    for index, line in enumerate(lines):
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() == "bundle" and parts[-1].lower() == "clicks":
            header_index = index
            break
    if header_index is None:
        raise ValueError("cannot find table header with columns: bundle, clicks")

    for line_num, line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        stripped = line.strip()
        if not stripped:
            continue
        if set(stripped) <= {"-", " "}:
            continue
        if set(stripped) <= {"=", " "}:
            break

        parts = stripped.rsplit(None, 1)
        if len(parts) != 2:
            result.warnings.append(f"line {line_num}: invalid table row skipped")
            continue
        bundle, clicks = parts
        warning = add_click(result.rows, bundle, clicks)
        if warning:
            result.warnings.append(f"line {line_num}: {warning}")

    return result


def parse_stat_file(path: str) -> ParsedStatFile:
    text = read_text(path)
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    first_columns = [part.strip().lower() for part in first_line.replace(";", ",").replace("\t", ",").split(",")]
    if "bundle" in first_columns and "clicks" in first_columns:
        return parse_delimited_text(text, path)

    plain_error = None
    try:
        return parse_plain_clk_stat_text(text, path)
    except ValueError as exc:
        plain_error = exc

    try:
        return parse_delimited_text(text, path)
    except ValueError as exc:
        raise ValueError(f"{plain_error}; {exc}") from exc


def format_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def format_number(value: Optional[float]) -> str:
    if value is None:
        return ""
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def format_refresh(refresh: int) -> str:
    if refresh == 0:
        return "off"
    if refresh % 60 == 0:
        minutes = refresh // 60
        unit = "min" if minutes == 1 else "mins"
        return f"{minutes} {unit}"
    return f"{refresh}s"


def display_click(cell: ClickCell) -> str:
    if not cell.present:
        return "0"
    if cell.value is None:
        return "ERR"
    return format_number(cell.value)


def click_value_or_zero(cell: ClickCell) -> Optional[float]:
    if not cell.present:
        return 0.0
    return cell.value if cell.valid else None


def total_click_cell(rows: Dict[str, ClickCell]) -> ClickCell:
    total = sum(cell.value for cell in rows.values() if cell.valid)
    return ClickCell(present=True, value=total, raw=str(total))


def build_total_history(data_dir: str, hours: int = 24) -> Tuple[List[TotalClickPoint], List[str]]:
    entries = [entry for entry in candidate_files(data_dir) if os.path.basename(entry[2]).startswith("clk_stat.")]
    if not entries:
        return [], []

    entries.sort(key=lambda item: (item[0], item[1]))
    newest_time = entries[-1][0]
    cutoff_time = newest_time - timedelta(hours=hours)
    points: List[TotalClickPoint] = []
    errors: List[str] = []

    for stat_time, _, path in entries:
        if stat_time < cutoff_time or stat_time > newest_time:
            continue
        try:
            parsed = parse_stat_file(path)
        except Exception as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")
            continue

        total = total_click_cell(parsed.rows).value or 0.0
        points.append(
            TotalClickPoint(
                path=path,
                name=os.path.basename(path),
                stat_time=stat_time,
                total=total,
            )
        )

    return points, errors


def build_table_rows(file1: ParsedStatFile, file2: ParsedStatFile) -> List[Tuple[str, ClickCell, ClickCell, str]]:
    bundles = sorted(set(file1.rows) | set(file2.rows))
    rows: List[Tuple[str, ClickCell, ClickCell, str]] = []
    for bundle in bundles:
        cell1 = file1.rows.get(bundle, ClickCell())
        cell2 = file2.rows.get(bundle, ClickCell())
        diff = ""
        value1 = click_value_or_zero(cell1)
        value2 = click_value_or_zero(cell2)
        if value1 is not None and value2 is not None:
            diff = format_number(value2 - value1)
        rows.append((bundle, cell1, cell2, diff))
    rows.sort(key=lambda row: (row[3] == "", -(parse_number(row[3]) or 0), row[0]))
    total1 = total_click_cell(file1.rows)
    total2 = total_click_cell(file2.rows)
    rows.insert(0, ("total_click", total1, total2, format_number(total2.value - total1.value)))
    return rows


def html_page(title: str, body: str, refresh: int) -> bytes:
    refresh_tag = f'<meta http-equiv="refresh" content="{max(refresh, 1)}">' if refresh else ""
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {refresh_tag}
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f7f8fa;
      --fg: #1f2937;
      --muted: #667085;
      --line: #d0d5dd;
      --panel: #ffffff;
      --error: #b42318;
      --accent: #1769aa;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #111827;
        --fg: #f3f4f6;
        --muted: #9ca3af;
        --line: #374151;
        --panel: #1f2937;
        --error: #f97066;
        --accent: #7dd3fc;
      }}
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 24px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    .meta, .message, .error {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 16px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px 18px;
      align-items: end;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 2px;
    }}
    .value {{
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      overflow-wrap: anywhere;
    }}
    .refresh-button {{
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--fg);
      color: var(--panel);
      cursor: pointer;
      font: inherit;
      font-weight: 650;
      padding: 8px 12px;
    }}
    .refresh-button:hover {{
      opacity: 0.86;
    }}
    .error {{
      color: var(--error);
    }}
    .chart {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 16px;
      padding: 14px 16px 16px;
    }}
    .chart-head {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 16px;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 8px;
    }}
    .chart-title {{
      font-size: 16px;
      font-weight: 650;
    }}
    .chart svg {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .chart-grid {{
      stroke: var(--line);
      stroke-width: 1;
      opacity: 0.75;
    }}
    .chart-axis {{
      stroke: var(--line);
      stroke-width: 1;
    }}
    .chart-line {{
      fill: none;
      stroke: var(--accent);
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .chart-dot {{
      fill: var(--panel);
      stroke: var(--accent);
      stroke-width: 2;
    }}
    .chart-hover-area {{
      fill: transparent;
      pointer-events: all;
    }}
    .chart-hover-guide,
    .chart-tooltip {{
      opacity: 0;
      pointer-events: none;
      transition: opacity 120ms ease;
    }}
    .chart-hover-target:hover .chart-hover-guide,
    .chart-hover-target:hover .chart-tooltip {{
      opacity: 1;
    }}
    .chart-hover-guide {{
      stroke: var(--accent);
      stroke-width: 1.5;
      stroke-dasharray: 4 4;
    }}
    .chart-tooltip-box {{
      fill: var(--panel);
      stroke: var(--line);
      stroke-width: 1;
    }}
    .chart-tooltip-text {{
      fill: var(--fg);
      font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .chart-label {{
      fill: var(--muted);
      font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 9px 12px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      white-space: nowrap;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      background: rgba(127, 127, 127, 0.08);
    }}
    th:first-child, td:first-child {{
      text-align: left;
      white-space: normal;
      overflow-wrap: anywhere;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .total-row td {{
      font-weight: 700;
      background: rgba(127, 127, 127, 0.11);
    }}
    .diff-positive {{
      color: var(--accent);
      font-weight: 650;
    }}
    .muted {{
      color: var(--muted);
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {body}
  </main>
</body>
</html>
"""
    return page.encode("utf-8")


def render_meta(file1: ParsedStatFile, file2: ParsedStatFile, refresh: int) -> str:
    return f"""
<section class="meta">
  <div class="meta-grid">
    <div>
      <div class="label">clicks1_time</div>
      <div class="value">{html.escape(file1.name)}</div>
      <div class="muted">{html.escape(format_mtime(file1.mtime))} / {len(file1.rows)} rows</div>
    </div>
    <div>
      <div class="label">clicks2_time</div>
      <div class="value">{html.escape(file2.name)}</div>
      <div class="muted">{html.escape(format_mtime(file2.mtime))} / {len(file2.rows)} rows</div>
    </div>
    <div>
      <div class="label">refresh</div>
      <div class="value">{html.escape(format_refresh(refresh))}</div>
      <div class="muted">diff = clicks2 - clicks1</div>
    </div>
    <div>
      <button class="refresh-button" type="button" onclick="window.location.reload()">手动刷新</button>
    </div>
  </div>
</section>
"""


def render_warnings(files: Iterable[ParsedStatFile]) -> str:
    items = []
    for parsed in files:
        for warning in parsed.warnings[:20]:
            items.append(f"<li>{html.escape(parsed.name)}: {html.escape(warning)}</li>")
    if not items:
        return ""
    return f'<section class="error"><strong>数据警告</strong><ul>{"".join(items)}</ul></section>'


def render_total_history_chart(points: List[TotalClickPoint], errors: List[str]) -> str:
    error_items = "".join(f"<li>{html.escape(error)}</li>" for error in errors[:10])
    error_html = f'<div class="muted"><ul>{error_items}</ul></div>' if error_items else ""
    if not points:
        return f"""
<section class="chart">
  <div class="chart-head">
    <div class="chart-title">过去24小时点击总数</div>
    <div class="muted">暂无可展示数据</div>
  </div>
  {error_html}
</section>
"""

    width = 960
    height = 280
    left = 58
    right = 18
    top = 18
    bottom = 42
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_total = max(point.total for point in points)
    y_max = max(max_total, 1.0)

    def point_x(index: int) -> float:
        if len(points) == 1:
            return left + plot_width / 2
        return left + plot_width * index / (len(points) - 1)

    def point_y(total: float) -> float:
        return top + plot_height - (total / y_max * plot_height)

    chart_points = [(point_x(index), point_y(point.total), point) for index, point in enumerate(points)]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in chart_points)
    grid_values = [0.0, y_max / 2, y_max]
    grid_lines = []
    for value in grid_values:
        y = point_y(value)
        grid_lines.append(
            f'<line class="chart-grid" x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" />'
            f'<text class="chart-label" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{html.escape(format_number(value))}</text>'
        )

    dots = []
    for x, y, point in chart_points:
        label = f"{point.stat_time.strftime('%m-%d %H:%M')} / {format_number(point.total)}"
        dots.append(
            f'<circle class="chart-dot" cx="{x:.1f}" cy="{y:.1f}" r="3.5">'
            f"<title>{html.escape(label)}</title>"
            "</circle>"
        )

    hover_targets = []
    tooltip_height = 44
    for index, (x, y, point) in enumerate(chart_points):
        if len(chart_points) == 1:
            band_x = left
            band_width = plot_width
        else:
            prev_x = chart_points[index - 1][0] if index > 0 else left
            next_x = chart_points[index + 1][0] if index < len(chart_points) - 1 else width - right
            band_x = (prev_x + x) / 2 if index > 0 else left
            band_width = ((x + next_x) / 2 if index < len(chart_points) - 1 else width - right) - band_x

        time_text = point.stat_time.strftime("%m-%d %H:%M")
        total_text = f"total {format_number(point.total)}"
        tooltip_width = max(132, min(220, (max(len(time_text), len(total_text)) * 7) + 28))
        tooltip_x = x + 12
        if tooltip_x + tooltip_width > width - right:
            tooltip_x = x - tooltip_width - 12
        tooltip_x = max(left, tooltip_x)
        tooltip_y = y - tooltip_height - 12
        if tooltip_y < top:
            tooltip_y = y + 12
        if tooltip_y + tooltip_height > height - bottom:
            tooltip_y = height - bottom - tooltip_height

        hover_targets.append(
            '<g class="chart-hover-target">'
            f'<rect class="chart-hover-area" x="{band_x:.1f}" y="{top}" width="{band_width:.1f}" height="{plot_height}" />'
            f'<line class="chart-hover-guide" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - bottom}" />'
            '<g class="chart-tooltip">'
            f'<rect class="chart-tooltip-box" x="{tooltip_x:.1f}" y="{tooltip_y:.1f}" width="{tooltip_width:.1f}" height="{tooltip_height}" rx="6" />'
            f'<text class="chart-tooltip-text" x="{tooltip_x + 10:.1f}" y="{tooltip_y + 17:.1f}">{html.escape(time_text)}</text>'
            f'<text class="chart-tooltip-text" x="{tooltip_x + 10:.1f}" y="{tooltip_y + 34:.1f}">{html.escape(total_text)}</text>'
            "</g>"
            "</g>"
        )

    start_label = points[0].stat_time.strftime("%m-%d %H:%M")
    end_label = points[-1].stat_time.strftime("%m-%d %H:%M")
    latest_total = format_number(points[-1].total)
    range_label = f"{start_label} -> {end_label} / {len(points)} points / latest {latest_total}"

    return f"""
<section class="chart">
  <div class="chart-head">
    <div class="chart-title">过去24小时点击总数</div>
    <div class="muted">{html.escape(range_label)}</div>
  </div>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="过去24小时点击总数折线图">
    {''.join(grid_lines)}
    <line class="chart-axis" x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" />
    <polyline class="chart-line" points="{polyline}" />
    {''.join(dots)}
    {''.join(hover_targets)}
    <text class="chart-label" x="{left}" y="{height - 14}">{html.escape(start_label)}</text>
    <text class="chart-label" x="{width - right}" y="{height - 14}" text-anchor="end">{html.escape(end_label)}</text>
  </svg>
  {error_html}
</section>
"""


def render_table(file1: ParsedStatFile, file2: ParsedStatFile) -> str:
    body_rows = []
    for bundle, cell1, cell2, diff in build_table_rows(file1, file2):
        diff_class = "diff-positive" if diff and (parse_number(diff) or 0) > 0 else ""
        row_class = ' class="total-row"' if bundle == "total_click" else ""
        body_rows.append(
            f"<tr{row_class}>"
            f"<td>{html.escape(bundle)}</td>"
            f"<td>{html.escape(display_click(cell1))}</td>"
            f"<td>{html.escape(display_click(cell2))}</td>"
            f'<td class="{diff_class}">{html.escape(diff)}</td>'
            "</tr>"
        )
    if not body_rows:
        body_rows.append('<tr><td colspan="4" class="muted">没有可展示的 bundle 记录</td></tr>')

    return f"""
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>bundle</th>
        <th>clicks1</th>
        <th>clicks2</th>
        <th>diff</th>
      </tr>
    </thead>
    <tbody>
      {''.join(body_rows)}
    </tbody>
  </table>
</div>
"""


def render_monitor(data_dir: str, refresh: int) -> bytes:
    try:
        paths = latest_two_files(data_dir)
    except OSError as exc:
        body = f'<section class="error">无法读取数据目录：{html.escape(str(exc))}</section>'
        return html_page("clk monitor", body, refresh)

    if len(paths) < 2:
        body = (
            '<section class="message">'
            f'等待至少两个数据文件。当前目录：<span class="value">{html.escape(data_dir)}</span>'
            "</section>"
        )
        return html_page("clk monitor", body, refresh)

    older_path, newer_path = paths[1], paths[0]
    try:
        file1 = parse_stat_file(older_path)
    except Exception as exc:
        body = (
            '<section class="error">'
            "<strong>文件格式错误</strong><br>"
            f"{html.escape(os.path.basename(older_path))}: {html.escape(str(exc))}"
            "</section>"
        )
        return html_page("clk monitor", body, refresh)

    try:
        file2 = parse_stat_file(newer_path)
    except Exception as exc:
        body = (
            '<section class="error">'
            "<strong>文件格式错误</strong><br>"
            f"{html.escape(os.path.basename(newer_path))}: {html.escape(str(exc))}"
            "</section>"
        )
        return html_page("clk monitor", body, refresh)

    history_points, history_errors = build_total_history(data_dir)
    body = (
        render_meta(file1, file2, refresh)
        + render_warnings((file1, file2))
        + render_total_history_chart(history_points, history_errors)
        + render_table(file1, file2)
    )
    return html_page("clk monitor", body, refresh)


class MonitorHandler(BaseHTTPRequestHandler):
    data_dir = DEFAULT_DATA_DIR
    refresh = DEFAULT_REFRESH

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = posixpath.normpath(parsed.path)
        if path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return
        if path != "/":
            self.send_error(404, "not found")
            return

        page = render_monitor(self.data_dir, self.refresh)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def main() -> int:
    args = parse_args()
    if args.port <= 0 or args.port > 65535:
        print("error: --port must be between 1 and 65535", file=sys.stderr)
        return 2
    if args.refresh < 0:
        print("error: --refresh must be zero or positive", file=sys.stderr)
        return 2

    handler = type(
        "ConfiguredMonitorHandler",
        (MonitorHandler,),
        {"data_dir": os.path.abspath(args.data_dir), "refresh": args.refresh},
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"serving clk monitor on http://{args.host}:{args.port}/")
    print(f"data_dir: {os.path.abspath(args.data_dir)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
