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
from datetime import datetime
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


def latest_two_files(data_dir: str) -> List[str]:
    entries: List[Tuple[float, str]] = []
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        if is_candidate_file(name, path):
            entries.append((os.path.getmtime(path), path))
    entries.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in entries[:2]]


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

    body = render_meta(file1, file2, refresh) + render_warnings((file1, file2)) + render_table(file1, file2)
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
