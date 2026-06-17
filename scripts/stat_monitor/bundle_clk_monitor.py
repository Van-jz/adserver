#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitor previous half-hour click counts by bundle from kwaiadsinfo postshow logs."""

import argparse
import json
import os
import re
import socket
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


BLOCKED_DOMAINS = ("ad.ap4r.com", "s16.kwai.net", "adx.opera.com", "liftoff-creatives.io")
REQUEST_MARKER = "收到 kwaiadsinfo postshow 请求数据: "
UNKNOWN_BUNDLE = "(unknown)"
DEFAULT_OUTPUT_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat"
DEFAULT_MERGE_OUTPUT_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat_merge"
DEFAULT_LOG_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold"
DEFAULT_INCREASE_DIR_NAME = "increase_info_log"
DEFAULT_LOG_PREFIX = "info.prod0320"
DEFAULT_BUNDLE_MAP_FILE = "click_id_bundle_map.json"
DEFAULT_CURSOR_FILE_NAME = ".bundle_clk_monitor.cursor.json"
DEFAULT_MERGE_CURSOR_FILE_NAME = ".bundle_clk_monitor_merge.cursor.json"
DEFAULT_OUTPUT_FILE_PREFIX = "clk_stat"
MERGE_OUTPUT_FILE_PREFIX = "clk_stat_merge"
LOG_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:[.,](\d{1,6}))?")
CLICK_ID_RE = re.compile(r"(?:[?&])click_id=([^&#\s]+)")
PIXEL_ID_RE = re.compile(r"(?:[?&])pixel_id=(\d+)")
MAIL_ALERT_MINUTES = 30
MAIL_ALERT_TO = "hanjing915@qq.com"
TG_CHAT_IDS = "8691808668,-5361073302"
CLICK_DROP_ALERT_THRESHOLD = 0.10
MERGE_ALERT_TARGET_NAME = "线上总计"
MERGE_LOG_FILE_RE = re.compile(
    rf"^{re.escape(DEFAULT_LOG_PREFIX)}(?:\.[^_]+)?_(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.part_(?P<part>\d+)\.log$"
)
INCREASE_LOG_RE = re.compile(r"^increase_info_log\..*\.(?P<stamp>\d{8}\.\d{4})(?:\.\d+)?$")


def script_dir() -> str:
    """返回当前脚本所在目录，用来定位相邻的 send_mail 模块。"""
    return os.path.dirname(os.path.abspath(__file__))


def load_json_file(path: str, default: Any) -> Any:
    """读取 JSON 文件；文件不存在或格式错误时返回 default。"""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def find_log_files(log_dir: str, log_prefix: str) -> List[str]:
    """在日志目录中找到匹配前缀且以 .log 结尾的文件，按修改时间从新到旧排序。"""
    try:
        files = os.listdir(log_dir)
    except OSError as exc:
        raise RuntimeError(f"cannot list log dir {log_dir}: {exc}") from exc

    log_files = [
        os.path.join(log_dir, name)
        for name in files
        if name.startswith(log_prefix) and name.endswith(".log")
    ]
    if not log_files:
        raise RuntimeError(f"no log files found in {log_dir} with prefix {log_prefix}")
    return sorted(log_files, key=os.path.getmtime, reverse=True)


def find_latest_log_file(log_dir: str, log_prefix: str) -> str:
    """在日志目录中找到最新修改的、匹配前缀且以 .log 结尾的文件。"""
    return find_log_files(log_dir, log_prefix)[0]


def extract_request_body(log_line: str) -> Optional[str]:
    """从 postshow 日志行中截取请求体；非目标日志行返回 None。"""
    pos = log_line.find(REQUEST_MARKER)
    if pos < 0:
        return None
    return log_line[pos + len(REQUEST_MARKER):].strip()


def parse_log_time_parts(log_line: str) -> Optional[Tuple[str, Optional[str], str]]:
    """快速解析行首固定格式时间，返回 (秒级字符串, 微秒字符串, 展示字符串)。"""
    if len(log_line) < 19:
        return None

    base = log_line[:19]
    if (
        base[4] != "-"
        or base[7] != "-"
        or base[10] != " "
        or base[13] != ":"
        or base[16] != ":"
        or not (
            base[:4].isdigit()
            and base[5:7].isdigit()
            and base[8:10].isdigit()
            and base[11:13].isdigit()
            and base[14:16].isdigit()
            and base[17:19].isdigit()
        )
    ):
        return None

    fraction = None
    display = base
    if len(log_line) > 20 and log_line[19] in (".", ",") and log_line[20].isdigit():
        end = 20
        while end < len(log_line) and end < 26 and log_line[end].isdigit():
            end += 1
        fraction = log_line[20:end]
        display = f"{base}.{fraction}"

    return base, fraction, display


def log_time_parts_to_timestamp(base: str, fraction: Optional[str]) -> Optional[float]:
    """把 parse_log_time_parts 的结果转换为时间戳。"""
    try:
        dt = datetime(
            int(base[:4]),
            int(base[5:7]),
            int(base[8:10]),
            int(base[11:13]),
            int(base[14:16]),
            int(base[17:19]),
        )
    except ValueError:
        return None

    if fraction:
        dt = dt.replace(microsecond=int(fraction[:6].ljust(6, "0")))
    return dt.timestamp()


def parse_log_time(log_line: str) -> Optional[Tuple[float, str]]:
    """解析日志行首时间，返回时间戳和原始展示字符串。"""
    parsed = parse_log_time_parts(log_line)
    if not parsed:
        return None

    base, fraction, display = parsed
    ts = log_time_parts_to_timestamp(base, fraction)
    if ts is None:
        return None
    return ts, display


def format_log_time(ts: float) -> str:
    """把秒级时间戳格式化成日志时间字符串。"""
    dt = datetime.fromtimestamp(ts)
    if dt.microsecond:
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_replay_time(value: str) -> datetime:
    """解析历史回放时间参数。"""
    for fmt in ("%Y%m%d %H%M", "%Y%m%d%H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"invalid time '{value}', expected format like '20260615 1500'"
    )


def previous_half_hour_window(run_dt: datetime) -> Tuple[datetime, datetime, datetime]:
    """Return (anchor, window_start, window_end) for the previous half-hour slot."""
    # 先把运行时间归到当前半小时段的起点，再向前取完整 30 分钟窗口。
    anchor_minute = 30 if run_dt.minute >= 30 else 0
    anchor = run_dt.replace(minute=anchor_minute, second=0, microsecond=0)
    window_start = anchor - timedelta(minutes=30)
    window_end = anchor - timedelta(microseconds=1)
    return anchor, window_start, window_end


def is_half_hour_boundary(value: datetime) -> bool:
    """判断时间是否落在整点或半点。"""
    return value.minute in (0, 30) and value.second == 0 and value.microsecond == 0


def display_window_end(anchor: datetime) -> datetime:
    """把窗口结束锚点转换成展示和扫描使用的最后一刻。"""
    return anchor - timedelta(microseconds=1)


def parse_merge_log_file_name(name: str) -> Optional[Tuple[str, int]]:
    """解析 merge 模式主日志文件名，返回 (date, part)。"""
    match = MERGE_LOG_FILE_RE.match(name)
    if not match:
        return None
    return match.group("date"), int(match.group("part"))


def find_merge_main_log_files(
    log_dir: str,
    target_date: str,
    window_start: datetime,
    window_end: datetime,
) -> List[str]:
    """查找 merge 模式下可能覆盖统计窗口的主机分片日志。"""
    try:
        names = os.listdir(log_dir)
    except OSError as exc:
        raise RuntimeError(f"cannot list log dir {log_dir}: {exc}") from exc

    candidates = []
    day_start_ts = datetime.strptime(target_date, "%Y-%m-%d").timestamp()
    window_start_ts = window_start.timestamp()
    window_end_ts = window_end.timestamp()
    for name in names:
        parsed = parse_merge_log_file_name(name)
        if not parsed:
            continue
        file_date, part = parsed
        if file_date != target_date:
            continue
        path = os.path.join(log_dir, name)
        if os.path.isfile(path):
            candidates.append((part, name, path, os.path.getmtime(path)))

    candidates.sort()
    selected_indexes = set()
    for index, (_, _, _, file_end_ts) in enumerate(candidates):
        # 日志按 part 递增；当前分片大致覆盖“上一分片结束 -> 当前分片结束”。
        file_start_ts = candidates[index - 1][3] if index > 0 else day_start_ts
        if file_end_ts < window_start_ts or file_start_ts > window_end_ts:
            continue
        selected_indexes.add(index)
        if index > 0:
            selected_indexes.add(index - 1)

    return [candidates[index][2] for index in sorted(selected_indexes)]


def parse_increase_log_time(name: str) -> Optional[datetime]:
    """从 increase_info_log 文件名中解析分片时间。"""
    match = INCREASE_LOG_RE.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group("stamp"), "%Y%m%d.%H%M")
    except ValueError:
        return None


def find_increase_log_files(increase_dir: str, window_start: datetime, anchor: datetime) -> List[str]:
    """查找分片结束时间落在统计窗口内的 increase_info_log 文件。"""
    try:
        names = os.listdir(increase_dir)
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise RuntimeError(f"cannot list increase log dir {increase_dir}: {exc}") from exc

    selected = []
    for name in names:
        # 增量日志按 5 分钟分片结束时间命名；例如 1600 覆盖 15:55-15:59。
        log_time = parse_increase_log_time(name)
        if log_time is None or log_time <= window_start or log_time > anchor:
            continue
        path = os.path.join(increase_dir, name)
        if os.path.isfile(path):
            selected.append((log_time, name, path))
    return [path for _, _, path in sorted(selected)]


def parse_json_data(request_body_str: str) -> Optional[Dict[str, Any]]:
    """解析 postshow 请求体，兼容直接 JSON 和 data=URL编码JSON 两种格式。"""
    try:
        if request_body_str.startswith("data="):
            return json.loads(urllib.parse.unquote(request_body_str[5:]))
        return json.loads(request_body_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        if request_body_str.startswith("data="):
            return None
        try:
            return json.loads(urllib.parse.unquote(request_body_str))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None


def extract_referrer_package(json_data: Dict[str, Any]) -> Optional[str]:
    """从请求数据中提取 referrer_package，作为本批 URL 的 bundle。"""
    data = json_data.get("data")
    if isinstance(data, dict):
        value = data.get("referrer_package")
        return value if isinstance(value, str) and value else None
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(parsed, dict):
            value = parsed.get("referrer_package")
            return value if isinstance(value, str) and value else None
    return None


def extract_urls_from_data(json_data: Dict[str, Any]) -> List[str]:
    """从请求数据中提取 URL 列表，兼容 data 为 dict 或字符串的格式。"""
    data = json_data.get("data")
    if isinstance(data, dict):
        urls = data.get("urls", [])
        return [u for u in urls if isinstance(u, str)] if isinstance(urls, list) else []
    if isinstance(data, str):
        return re.findall(r"https?://[^\s]+", data)
    return []


def parse_url_pixel_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """从点击 URL 中提取 pixel_id 和 click_id；解析失败返回 (None, None)。"""
    try:
        pixel_match = PIXEL_ID_RE.search(url)
        click_match = CLICK_ID_RE.search(url)

        pixel_id = pixel_match.group(1) if pixel_match else None
        click_id = click_match.group(1) if click_match else None
        if click_id and ("%" in click_id or "+" in click_id):
            click_id = urllib.parse.unquote_plus(click_id)

        return pixel_id, click_id
    except Exception:
        return None, None


def load_bundle_map(bundle_map_file: Optional[str]) -> Dict[str, str]:
    """读取 click_id 到 bundle 的兜底映射文件；兼容值为字符串或对象的新旧格式。"""
    if not bundle_map_file:
        return {}
    data = load_json_file(bundle_map_file, {})
    if not isinstance(data, dict):
        return {}

    bundle_map = {}
    for click_id, value in data.items():
        if not isinstance(click_id, str) or not click_id:
            continue

        bundle = None
        if isinstance(value, str):
            bundle = value
        elif isinstance(value, dict):
            bundle = value.get("bundle")

        if isinstance(bundle, str) and bundle:
            bundle_map[click_id] = bundle

    return bundle_map


def find_last_log_time(log_file: str) -> Optional[Tuple[float, str]]:
    """扫描日志文件，找到最后一条可解析的行首时间。"""
    latest_log_time = None
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_log_time(line)
            if parsed:
                latest_log_time = parsed
    return latest_log_time


def find_latest_parsed_log_time(log_files: List[str]) -> Optional[Tuple[str, float, str]]:
    """按文件修改时间从新到旧查找最近一条可解析日志时间。"""
    for log_file in log_files:
        latest_log_time = find_last_log_time(log_file)
        if latest_log_time:
            return log_file, latest_log_time[0], latest_log_time[1]
    return None


def find_window_log_files(log_files: List[str], window_start_time: float, latest_log_file: str) -> List[str]:
    """选择可能覆盖统计窗口的日志文件，并按修改时间从旧到新排序。"""
    selected = [
        log_file
        for log_file in log_files
        if log_file == latest_log_file or os.path.getmtime(log_file) >= window_start_time
    ]
    return sorted(selected, key=os.path.getmtime)


def get_cursor_file_path(
    output_dir: str,
    cursor_file: Optional[str],
    default_file_name: str = DEFAULT_CURSOR_FILE_NAME,
) -> str:
    """返回自动模式用来续读主机日志的游标文件路径。"""
    if cursor_file:
        return os.path.abspath(cursor_file)
    return os.path.join(os.path.abspath(output_dir), default_file_name)


def load_scan_cursor(cursor_file: str, log_files: List[str], window_start_time: float) -> Dict[str, int]:
    """读取上次主机日志扫描位置；不安全或不适用时返回空游标。"""
    try:
        with open(cursor_file, "r", encoding="utf-8") as f:
            cursor = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: cannot read clk monitor cursor {cursor_file}: {exc}", file=sys.stderr)
        return {}

    if not isinstance(cursor, dict):
        return {}

    log_file = cursor.get("log_file")
    position = cursor.get("position")
    cursor_time = cursor.get("log_time")
    if not isinstance(log_file, str) or not isinstance(position, int) or position <= 0:
        return {}
    if log_file not in log_files:
        return {}
    if isinstance(cursor_time, (int, float)) and cursor_time > window_start_time:
        return {}

    try:
        if os.path.getsize(log_file) < position:
            return {}
    except OSError as exc:
        print(f"warning: cannot stat clk monitor cursor log {log_file}: {exc}", file=sys.stderr)
        return {}

    return {log_file: position}


def save_scan_cursor(cursor_file: str, cursor: Dict[str, Any]) -> None:
    """保存下次自动模式扫描可续读的位置。"""
    try:
        cursor_dir = os.path.dirname(cursor_file)
        if cursor_dir:
            os.makedirs(cursor_dir, exist_ok=True)
        with open(cursor_file, "w", encoding="utf-8") as f:
            json.dump(cursor, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
    except OSError as exc:
        print(f"warning: cannot write clk monitor cursor {cursor_file}: {exc}", file=sys.stderr)


def clear_scan_cursor(cursor_file: str) -> None:
    """当跟踪的日志已经读到 EOF 时清除自动模式游标。"""
    try:
        os.remove(cursor_file)
    except FileNotFoundError:
        return
    except OSError as exc:
        print(f"warning: cannot remove clk monitor cursor {cursor_file}: {exc}", file=sys.stderr)


def update_scan_cursor(
    cursor_file: str,
    log_files: List[str],
    file_positions: Dict[str, Dict[str, Any]],
) -> None:
    """只保留最新一个还没读到 EOF 的日志文件位置。"""
    for log_file in reversed(log_files):
        file_state = file_positions.get(log_file)
        if not file_state:
            continue
        if file_state.get("reached_eof"):
            continue

        cursor = {
            "log_file": log_file,
            "position": int(file_state.get("end_position", 0)),
            "log_time": file_state.get("next_log_time"),
            "log_time_display": file_state.get("next_log_time_display"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if cursor["position"] > 0:
            save_scan_cursor(cursor_file, cursor)
            return

    clear_scan_cursor(cursor_file)


def split_formatted_log_time(value: str) -> Tuple[str, Optional[str]]:
    """Split a formatted log timestamp into second and fractional parts."""
    if "." not in value:
        return value, None
    base, fraction = value.split(".", 1)
    return base, fraction


def compare_log_time_parts(
    base: str,
    fraction: Optional[str],
    target_base: str,
    target_fraction: Optional[str],
) -> int:
    """Compare parsed log time parts against a formatted target timestamp."""
    if base < target_base:
        return -1
    if base > target_base:
        return 1

    left_fraction = (fraction or "").ljust(6, "0")
    right_fraction = (target_fraction or "").ljust(6, "0")
    if left_fraction < right_fraction:
        return -1
    if left_fraction > right_fraction:
        return 1
    return 0


def scan_window_clicks(
    log_files: List[str],
    window_start_time: float,
    window_end_time: float,
    bundle_map: Dict[str, str],
    start_positions: Optional[Dict[str, int]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """统计指定日志时间窗口内的有效点击事件，并按 click_id 去重。

    bundle 归因优先级：click_id_bundle_map -> referrer_package -> (unknown)。
    """
    events: List[Dict[str, Any]] = []
    seen_click_ids = set()
    window_start_display = format_log_time(window_start_time)
    window_end_display = format_log_time(window_end_time)
    window_start_base, window_start_fraction = split_formatted_log_time(window_start_display)
    window_end_base, window_end_fraction = split_formatted_log_time(window_end_display)
    stats = {
        "scanned_lines": 0,
        "scanned_log_time_start": window_start_display,
        "scanned_log_time_end": window_end_display,
        "actual_scanned_log_time_start": None,
        "actual_scanned_log_time_end": None,
        "postshow_lines": 0,
        "candidate_urls": 0,
        "duplicate_click_ids": 0,
        "blocked_urls": 0,
        "valid_clicks": 0,
        "file_positions": {},
    }
    earliest_log_time = None
    latest_log_time = None
    start_positions = start_positions or {}

    last_referrer_package = None
    lines_since_referrer = 0

    for log_file in log_files:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            start_position = start_positions.get(log_file, 0)
            if start_position > 0:
                f.seek(start_position)

            reached_eof = True
            end_position = f.tell()
            latest_file_log_time = None
            next_file_log_time = None
            while True:
                line_start_position = f.tell()
                line = f.readline()
                if not line:
                    end_position = f.tell()
                    break

                parsed_log_time = parse_log_time_parts(line)
                if not parsed_log_time:
                    continue

                log_time_base, log_time_fraction, log_time_display = parsed_log_time
                if compare_log_time_parts(
                    log_time_base,
                    log_time_fraction,
                    window_end_base,
                    window_end_fraction,
                ) > 0:
                    reached_eof = False
                    end_position = line_start_position
                    log_time = log_time_parts_to_timestamp(log_time_base, log_time_fraction)
                    if log_time is not None:
                        next_file_log_time = (log_time, log_time_display)
                    break

                # 窗口前的 postshow 也要解析，用来延续 referrer_package 上下文；
                # 只有窗口内的 URL 才会进入最终统计。
                in_window = compare_log_time_parts(
                    log_time_base,
                    log_time_fraction,
                    window_start_base,
                    window_start_fraction,
                ) >= 0
                log_time = None
                if in_window:
                    log_time = log_time_parts_to_timestamp(log_time_base, log_time_fraction)
                    if log_time is None:
                        continue
                    latest_file_log_time = (log_time, log_time_display)
                    stats["scanned_lines"] += 1
                    if earliest_log_time is None or log_time < earliest_log_time[0]:
                        earliest_log_time = (log_time, log_time_display)
                    if latest_log_time is None or log_time > latest_log_time[0]:
                        latest_log_time = (log_time, log_time_display)

                request_body = extract_request_body(line)
                if request_body is None:
                    continue

                stats["postshow_lines"] += 1
                json_data = parse_json_data(request_body)
                if json_data is None:
                    continue

                referrer_package = extract_referrer_package(json_data)
                if referrer_package:
                    last_referrer_package = referrer_package
                    lines_since_referrer = 0
                else:
                    lines_since_referrer += 1
                    if last_referrer_package and lines_since_referrer <= 10:
                        referrer_package = last_referrer_package

                if not in_window:
                    continue

                for raw_url in extract_urls_from_data(json_data):
                    url = raw_url.strip().rstrip('"')
                    if "click_id" not in url or "pixel_id" not in url:
                        continue
                    if any(domain in url for domain in BLOCKED_DOMAINS):
                        stats["blocked_urls"] += 1
                        continue

                    stats["candidate_urls"] += 1
                    _, click_id = parse_url_pixel_id(url)
                    if not click_id:
                        continue
                    # 同一次扫描内，同一个 click_id 只计一次，保持与 orchestrator 的去重口径一致。
                    if click_id in seen_click_ids:
                        stats["duplicate_click_ids"] += 1
                        continue

                    seen_click_ids.add(click_id)
                    bundle = bundle_map.get(click_id) or referrer_package or UNKNOWN_BUNDLE
                    events.append(
                        {
                            "log_time": log_time,
                            "log_time_display": log_time_display,
                            "bundle": bundle,
                            "click_id": click_id,
                        }
                    )
                    stats["valid_clicks"] += 1

            stats["file_positions"][log_file] = {
                "start_position": start_position,
                "end_position": end_position,
                "reached_eof": reached_eof,
                "last_log_time": latest_file_log_time[0] if latest_file_log_time else None,
                "last_log_time_display": latest_file_log_time[1] if latest_file_log_time else None,
                "next_log_time": next_file_log_time[0] if next_file_log_time else None,
                "next_log_time_display": next_file_log_time[1] if next_file_log_time else None,
            }

    if earliest_log_time:
        stats["actual_scanned_log_time_start"] = earliest_log_time[1]
    if latest_log_time:
        stats["actual_scanned_log_time_end"] = latest_log_time[1]

    return events, stats


def build_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把点击事件聚合成按 bundle 展示的表格行。"""
    bundle_clicks = Counter(event.get("bundle", UNKNOWN_BUNDLE) for event in events)

    rows = []
    for bundle in sorted(bundle_clicks.keys()):
        rows.append(
            {
                "bundle": bundle,
                "clicks": bundle_clicks[bundle],
            }
        )
    rows.sort(key=lambda row: (-row["clicks"], row["bundle"]))
    return rows


def render_table(rows: List[Dict[str, Any]], top: Optional[int], show_all: bool) -> str:
    """把聚合行渲染为终端可读的等宽表格。"""
    if not rows:
        return "No clicks in the current window."

    visible_rows = rows if show_all or top is None else rows[:top]
    headers = ["bundle", "clicks"]
    widths = {
        header: max(len(header), *(len(str(row[header])) for row in visible_rows))
        for header in headers
    }

    lines = []
    lines.append("  ".join(header.ljust(widths[header]) for header in headers))
    lines.append("  ".join("-" * widths[header] for header in headers))
    for row in visible_rows:
        lines.append(
            "  ".join(
                [
                    str(row["bundle"]).ljust(widths["bundle"]),
                    str(row["clicks"]).rjust(widths["clicks"]),
                ]
            )
        )

    hidden = len(rows) - len(visible_rows)
    if hidden > 0:
        lines.append(f"... {hidden} more bundle(s); use --all to show all")
    return "\n".join(lines)


def build_output_text(
    latest_log_file: str,
    minutes: int,
    scanned_range: str,
    total_clicks: int,
    table_text: str,
) -> str:
    """组装本次运行的完整输出文本，供终端打印和文件落盘共用。"""
    return "\n".join(
        [
            f"log_file: {latest_log_file}",
            f"min: {minutes}",
            f"scanned_log_time_range: {scanned_range}",
            f"total_clicks: {total_clicks}",
            table_text,
        ]
    )


def write_output_file(
    output_dir: str,
    output_text: str,
    run_dt: datetime,
    output_prefix: str = DEFAULT_OUTPUT_FILE_PREFIX,
) -> str:
    """将本次统计结果写入 {output_prefix}.YYYYMMDD-hhmm 文件，并返回文件路径。"""
    os.makedirs(output_dir, exist_ok=True)
    output_file = get_output_file_path(output_dir, run_dt, output_prefix)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)
        f.write("\n")
    return output_file


def get_output_file_path(
    output_dir: str,
    run_dt: datetime,
    output_prefix: str = DEFAULT_OUTPUT_FILE_PREFIX,
) -> str:
    """按运行时间拼出对应的统计文件路径。"""
    return os.path.join(output_dir, f"{output_prefix}.{run_dt.strftime('%Y%m%d-%H%M')}")


def get_clk_stat_file_path(output_dir: str, run_dt: datetime) -> str:
    """按运行时间拼出对应的 clk_stat 文件路径。"""
    return get_output_file_path(output_dir, run_dt, DEFAULT_OUTPUT_FILE_PREFIX)


def read_total_clicks_from_output(path: str, output_prefix: str = DEFAULT_OUTPUT_FILE_PREFIX) -> Optional[int]:
    """读取统计文件里的 total_clicks；兼容历史追加文件，取最后一次结果。"""
    totals = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re.match(r"^\s*total_clicks:\s*(\d+)\s*$", line)
                if match:
                    totals.append(int(match.group(1)))
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"warning: cannot read yesterday {output_prefix} {path}: {exc}", file=sys.stderr)
        return None

    if not totals:
        print(f"warning: cannot find total_clicks in yesterday {output_prefix}: {path}", file=sys.stderr)
        return None
    return totals[-1]


def read_total_clicks_from_clk_stat(path: str) -> Optional[int]:
    """读取 clk_stat 文件里的 total_clicks；兼容历史追加文件，取最后一次结果。"""
    return read_total_clicks_from_output(path, DEFAULT_OUTPUT_FILE_PREFIX)


def get_machine_ip() -> str:
    """获取报警邮件里展示的机器 IP，可用 CLK_MONITOR_MACHINE_IP 覆盖。"""
    env_ip = os.environ.get("CLK_MONITOR_MACHINE_IP")
    if env_ip:
        return env_ip

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        sock.close()

    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "unknown"


def maybe_send_zero_clicks_alert(
    minutes: int,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[str]:
    """满足 30 分钟以上且零点击时，通过 send_mail.py 发送报警邮件。"""
    if minutes < MAIL_ALERT_MINUTES or total_clicks != 0:
        return None

    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)

    try:
        from send_mail import send_mail
    except Exception as exc:
        print(f"warning: cannot import send_mail.py: {exc}", file=sys.stderr)
        return "failed"

    machine_ip = get_machine_ip()
    subject = f"[clk_monitor] {machine_ip} {minutes} minutes zero clicks alert"
    content = "\n".join(
        [
            f"！机器{machine_ip}已经{minutes}分钟没有点击了！",
            f"机器IP machine_ip: {machine_ip}",
            f"统计时间窗 minutes: {minutes}",
            f"总点击 total_clicks: {total_clicks}",
            f"日志文件 log_file: {latest_log_file}",
            f"扫描时间窗 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
        ]
    )
    result = send_mail(subject, content, MAIL_ALERT_TO)
    if result != "sent":
        print(f"warning: zero clicks alert mail result: {result}", file=sys.stderr)
    return result


def maybe_send_click_drop_alert(
    output_dir: str,
    run_dt: datetime,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[str]:
    """对比昨天同时间总点击，下降超过阈值时发送报警邮件。"""
    yesterday_dt = run_dt - timedelta(days=1)
    yesterday_file = get_clk_stat_file_path(output_dir, yesterday_dt)
    yesterday_total_clicks = read_total_clicks_from_clk_stat(yesterday_file)
    if yesterday_total_clicks is None:
        print(f"info: no yesterday clk_stat data for same time: {yesterday_file}; skip click drop alert")
        return None
    if yesterday_total_clicks <= 0:
        print(
            f"info: yesterday total_clicks is {yesterday_total_clicks} for {yesterday_file}; skip click drop alert"
        )
        return None

    drop_ratio = (yesterday_total_clicks - total_clicks) / yesterday_total_clicks
    if drop_ratio <= CLICK_DROP_ALERT_THRESHOLD:
        return None

    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)

    try:
        from send_mail import send_mail
    except Exception as exc:
        print(f"warning: cannot import send_mail.py: {exc}", file=sys.stderr)
        return "failed"

    machine_ip = get_machine_ip()
    drop_percent = drop_ratio * 100
    subject = f"[clk_monitor] {machine_ip} clicks dropped {drop_percent:.1f}% alert"
    content = "\n".join(
        [
            f"！机器{machine_ip}当轮点击较昨天同时间下降超过{CLICK_DROP_ALERT_THRESHOLD:.0%}！",
            f"机器IP machine_ip: {machine_ip}",
            f"当前时间 current_time: {run_dt.strftime('%Y-%m-%d %H:%M')}",
            f"昨日同期 yesterday_same_time: {yesterday_dt.strftime('%Y-%m-%d %H:%M')}",
            f"本轮总点击 current_total_clicks: {total_clicks}",
            f"昨日同期总点击 yesterday_total_clicks: {yesterday_total_clicks}",
            f"下跌比例 drop_percent: {drop_percent:.2f}%",
            f"扫描时间段 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
            f"昨日文件 yesterday_output_file: {yesterday_file}",
        ]
    )
    result = send_mail(subject, content, MAIL_ALERT_TO)
    if result != "sent":
        print(f"warning: click drop alert mail result: {result}", file=sys.stderr)
    return result


def ensure_send_mail_module_path() -> None:
    """把相邻 send_mail 目录加入 sys.path，供报警模块导入。"""
    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)


def send_alert_mail(subject: str, content: str, warning_name: str) -> str:
    """发送报警邮件，失败时只记录 warning，不中断监控。"""
    ensure_send_mail_module_path()
    try:
        from send_mail import send_mail
    except Exception as exc:
        print(f"warning: cannot import send_mail.py: {exc}", file=sys.stderr)
        return "failed"

    result = send_mail(subject, content, MAIL_ALERT_TO)
    if result != "sent":
        print(f"warning: {warning_name} mail result: {result}", file=sys.stderr)
    return result


def get_tg_chat_ids() -> List[str]:
    """从脚本常量中读取 Telegram chat ids。"""
    if isinstance(TG_CHAT_IDS, str):
        return [chat_id.strip() for chat_id in TG_CHAT_IDS.split(",") if chat_id.strip()]
    return [str(chat_id).strip() for chat_id in TG_CHAT_IDS if str(chat_id).strip()]


def send_alert_tg(content: str, warning_name: str) -> str:
    """用和邮件相同的正文发送 Telegram 报警。"""
    ensure_send_mail_module_path()
    try:
        from send_tg import send_telegram
    except Exception as exc:
        print(f"warning: cannot import send_tg.py: {exc}", file=sys.stderr)
        return "failed"

    chat_ids = get_tg_chat_ids()
    if not chat_ids:
        print("warning: telegram alert chat id is missing", file=sys.stderr)
        return "failed"

    results = [send_telegram(chat_id, content) for chat_id in chat_ids]
    result = "sent" if all(item == "sent" for item in results) else "failed"
    if result != "sent":
        print(f"warning: {warning_name} tg result: {','.join(results)}", file=sys.stderr)
    return result


def send_alert_notifications(subject: str, content: str, warning_name: str) -> Dict[str, str]:
    """通过邮件和 Telegram 发送同一份报警内容。"""
    return {
        "mail": send_alert_mail(subject, content, warning_name),
        "tg": send_alert_tg(content, warning_name),
    }


def maybe_send_merge_zero_clicks_alert(
    minutes: int,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[Dict[str, str]]:
    """merge 模式零点击时发送邮件和 Telegram 报警。"""
    if minutes < MAIL_ALERT_MINUTES or total_clicks != 0:
        return None

    subject = f"[clk_monitor] {MERGE_ALERT_TARGET_NAME} {minutes} minutes zero clicks alert"
    content = "\n".join(
        [
            f"！{MERGE_ALERT_TARGET_NAME}已经{minutes}分钟没有点击了！",
            f"线上总计: {MERGE_ALERT_TARGET_NAME}",
            f"统计时间窗 minutes: {minutes}",
            f"总点击 total_clicks: {total_clicks}",
            f"扫描时间窗 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
        ]
    )
    return send_alert_notifications(subject, content, "zero clicks alert")


def maybe_send_merge_click_drop_alert(
    output_dir: str,
    run_dt: datetime,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[Dict[str, str]]:
    """merge 模式对比昨天同时间总点击，下降超过阈值时发送报警。"""
    yesterday_dt = run_dt - timedelta(days=1)
    yesterday_file = get_output_file_path(output_dir, yesterday_dt, MERGE_OUTPUT_FILE_PREFIX)
    yesterday_total_clicks = read_total_clicks_from_output(yesterday_file, MERGE_OUTPUT_FILE_PREFIX)
    if yesterday_total_clicks is None:
        print(
            f"info: no yesterday {MERGE_OUTPUT_FILE_PREFIX} data for same time: {yesterday_file}; "
            "skip click drop alert"
        )
        return None
    if yesterday_total_clicks <= 0:
        print(
            f"info: yesterday total_clicks is {yesterday_total_clicks} for {yesterday_file}; skip click drop alert"
        )
        return None

    drop_ratio = (yesterday_total_clicks - total_clicks) / yesterday_total_clicks
    if drop_ratio <= CLICK_DROP_ALERT_THRESHOLD:
        return None

    drop_percent = drop_ratio * 100
    subject = f"[clk_monitor] {MERGE_ALERT_TARGET_NAME} clicks dropped {drop_percent:.1f}% alert"
    content = "\n".join(
        [
            f"！{MERGE_ALERT_TARGET_NAME}当轮点击较昨天同时间下降超过{CLICK_DROP_ALERT_THRESHOLD:.0%}！",
            f"线上总计: {MERGE_ALERT_TARGET_NAME}",
            f"当前时间 current_time: {run_dt.strftime('%Y-%m-%d %H:%M')}",
            f"昨日同期 yesterday_same_time: {yesterday_dt.strftime('%Y-%m-%d %H:%M')}",
            f"本轮总点击 current_total_clicks: {total_clicks}",
            f"昨日同期总点击 yesterday_total_clicks: {yesterday_total_clicks}",
            f"下跌比例 drop_percent: {drop_percent:.2f}%",
            f"扫描时间段 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
            f"昨日文件 yesterday_output_file: {yesterday_file}",
        ]
    )
    return send_alert_notifications(subject, content, "click drop alert")


def cleanup_old_outputs(
    output_dir: str,
    retention_days: int,
    now_dt: datetime,
    output_prefix: str = DEFAULT_OUTPUT_FILE_PREFIX,
) -> int:
    """清理 output_dir 中超过保留天数的统计产物，返回删除数量。"""
    cutoff_ts = (now_dt - timedelta(days=retention_days)).timestamp()
    deleted = 0
    try:
        names = os.listdir(output_dir)
    except OSError as exc:
        print(f"warning: cannot list output dir for cleanup: {output_dir}: {exc}", file=sys.stderr)
        return deleted

    for name in names:
        if not name.startswith(f"{output_prefix}."):
            continue
        path = os.path.join(output_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            if os.path.getmtime(path) >= cutoff_ts:
                continue
            os.remove(path)
            deleted += 1
        except OSError as exc:
            print(f"warning: cannot remove old {output_prefix} output {path}: {exc}", file=sys.stderr)
    return deleted


def cleanup_old_clk_stat_outputs(output_dir: str, retention_days: int, now_dt: datetime) -> int:
    """清理 output_dir 中超过保留天数的 clk_stat.* 产物，返回删除数量。"""
    return cleanup_old_outputs(output_dir, retention_days, now_dt, DEFAULT_OUTPUT_FILE_PREFIX)


def build_scanned_range(stats: Dict[str, Any]) -> str:
    """从扫描统计中生成展示用时间范围。"""
    if stats.get("scanned_log_time_start") and stats.get("scanned_log_time_end"):
        return f"{stats['scanned_log_time_start']} -> {stats['scanned_log_time_end']}"
    return "N/A"


def run_window(
    args: argparse.Namespace,
    log_files: List[str],
    bundle_map: Dict[str, str],
    window_start_time: float,
    window_end_time: float,
    output_dt: datetime,
    send_alerts: bool,
    use_cursor: bool = False,
) -> int:
    """扫描一个时间窗口，输出统计结果并按需发送报警。"""
    window_log_files = find_window_log_files(log_files, window_start_time, log_files[0])
    latest_log_file = window_log_files[-1] if window_log_files else log_files[0]
    cursor_file = get_cursor_file_path(args.output_dir, args.cursor_file)
    start_positions = load_scan_cursor(cursor_file, window_log_files, window_start_time) if use_cursor else {}

    window_events, stats = scan_window_clicks(
        window_log_files,
        window_start_time,
        window_end_time,
        bundle_map,
        start_positions=start_positions,
    )
    if use_cursor:
        update_scan_cursor(cursor_file, window_log_files, stats.get("file_positions", {}))
    rows = build_rows(window_events)
    scanned_range = (
        f"{datetime.fromtimestamp(window_start_time).strftime('%Y-%m-%d %H:%M:%S')} -> "
        f"{datetime.fromtimestamp(window_end_time).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    output_text = build_output_text(
        latest_log_file,
        int(round((window_end_time - window_start_time) / 60)),
        scanned_range,
        len(window_events),
        render_table(rows, args.top, args.all),
    )
    print(output_text)
    output_file = write_output_file(args.output_dir, output_text, output_dt)
    print(f"output_file: {output_file}")

    if send_alerts:
        drop_alert_result = maybe_send_click_drop_alert(
            args.output_dir,
            output_dt,
            len(window_events),
            latest_log_file,
            scanned_range,
            output_file,
        )
        if drop_alert_result:
            print(f"click_drop_alert_mail: {drop_alert_result}")
        alert_result = maybe_send_zero_clicks_alert(
            int(round((window_end_time - window_start_time) / 60)),
            len(window_events),
            latest_log_file,
            scanned_range,
            output_file,
        )
        if alert_result:
            print(f"alert_mail: {alert_result}")

    return 0


def join_log_file_names(paths: List[str]) -> str:
    """格式化本次选中的输入文件，保持输出字段名仍为 log_file。"""
    if not paths:
        return "N/A"
    return ", ".join(paths)


def run_merge_window(
    args: argparse.Namespace,
    log_dir: str,
    increase_dir: str,
    bundle_map: Dict[str, str],
    window_start: datetime,
    anchor: datetime,
    send_alerts: bool,
    use_cursor: bool = False,
) -> int:
    """merge 模式：扫描主机分片日志和增量日志，输出统计结果并按需报警。"""
    window_end = display_window_end(anchor)
    main_log_files = find_merge_main_log_files(
        log_dir,
        window_start.strftime("%Y-%m-%d"),
        window_start,
        window_end,
    )
    # 跨零点窗口要额外带上结束日期的主日志，避免 23:30-23:59 这类窗口附近漏文件。
    if window_end.strftime("%Y-%m-%d") != window_start.strftime("%Y-%m-%d"):
        main_log_files.extend(
            find_merge_main_log_files(
                log_dir,
                window_end.strftime("%Y-%m-%d"),
                window_start,
                window_end,
            )
        )
    increase_log_files = find_increase_log_files(increase_dir, window_start, anchor)
    selected_log_files = main_log_files + increase_log_files
    selected_log_file_text = join_log_file_names(selected_log_files)
    scanned_range = f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> {window_end.strftime('%Y-%m-%d %H:%M:%S')}"
    cursor_file = get_cursor_file_path(args.output_dir, args.cursor_file, DEFAULT_MERGE_CURSOR_FILE_NAME)
    start_positions = load_scan_cursor(cursor_file, main_log_files, window_start.timestamp()) if use_cursor else {}

    if selected_log_files:
        # 统计规则完全复用普通模式：解析 postshow、过滤域名、click_id 去重并归因 bundle。
        window_events, stats = scan_window_clicks(
            selected_log_files,
            window_start.timestamp(),
            window_end.timestamp(),
            bundle_map,
            start_positions=start_positions,
        )
        if use_cursor:
            update_scan_cursor(cursor_file, main_log_files, stats.get("file_positions", {}))
        rows = build_rows(window_events)
    else:
        window_events = []
        rows = []
        if use_cursor:
            clear_scan_cursor(cursor_file)

    output_text = build_output_text(
        selected_log_file_text,
        30,
        scanned_range,
        len(window_events),
        render_table(rows, args.top, args.all),
    )
    print(output_text)
    # 输出文件按半小时锚点命名，避免 crontab 在 04/34 分运行时生成 1504/1534 这类文件。
    output_file = write_output_file(args.output_dir, output_text, anchor, MERGE_OUTPUT_FILE_PREFIX)
    print(f"output_file: {output_file}")

    if not send_alerts:
        return 0

    drop_alert_result = maybe_send_merge_click_drop_alert(
        args.output_dir,
        anchor,
        len(window_events),
        selected_log_file_text,
        scanned_range,
        output_file,
    )
    if drop_alert_result:
        print(f"click_drop_alert_mail: {drop_alert_result.get('mail')}")
        print(f"click_drop_alert_tg: {drop_alert_result.get('tg')}")
    alert_result = maybe_send_merge_zero_clicks_alert(
        30,
        len(window_events),
        selected_log_file_text,
        scanned_range,
        output_file,
    )
    if alert_result:
        print(f"alert_mail: {alert_result.get('mail')}")
        print(f"alert_tg: {alert_result.get('tg')}")
    return 0


def parse_args() -> argparse.Namespace:
    """定义并解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Monitor previous half-hour click counts by bundle.",
        allow_abbrev=False,
    )
    parser.add_argument("--merge", action="store_true", help="merge main host logs with increase_info_log files")
    parser.add_argument("--time", dest="replay_time", type=parse_replay_time, help="replay anchor time, e.g. '20260615 1600' scans the previous 30 minutes")
    parser.add_argument("--top", type=int, default=20, help="number of bundles to display")
    parser.add_argument("--all", action="store_true", help="show all bundles")
    parser.add_argument("--no-alert", action="store_true", help="do not send alert mail")
    parser.add_argument("--log-dir", default=None, help="directory containing log files")
    parser.add_argument(
        "--increase-dir",
        default=None,
        help="directory containing increase_info_log files; default is log-dir/increase_info_log",
    )
    parser.add_argument("--output-dir", default=None, help="directory to write clk_stat or clk_stat_merge outputs")
    parser.add_argument("--retention-days", type=int, default=3, help="days to keep output files")
    parser.add_argument("--cursor-file", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--run-at", type=parse_replay_time, default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    """脚本入口：确定窗口、扫描日志并输出统计表。"""
    args = parse_args()
    run_dt = args.run_at or datetime.now()
    if args.output_dir is None:
        args.output_dir = DEFAULT_MERGE_OUTPUT_DIR if args.merge else DEFAULT_OUTPUT_DIR
    if args.top is not None and args.top <= 0:
        print("error: --top must be positive", file=sys.stderr)
        return 2
    if args.retention_days <= 0:
        print("error: --retention-days must be positive", file=sys.stderr)
        return 2
    if args.replay_time and not is_half_hour_boundary(args.replay_time):
        print("error: --time must be on a 00 or 30 minute boundary", file=sys.stderr)
        return 2

    # merge模式：扫描主机分片日志和增量日志，输出统计结果并按需报警。
    if args.merge:
        log_dir = os.path.abspath(args.log_dir or os.getcwd())
        increase_dir = os.path.abspath(args.increase_dir or os.path.join(log_dir, DEFAULT_INCREASE_DIR_NAME))
        bundle_map = load_bundle_map(os.path.join(log_dir, DEFAULT_BUNDLE_MAP_FILE))

        if args.replay_time:
            anchor = args.replay_time
            window_start = anchor - timedelta(minutes=30)
            print(
                "replay_window: "
                f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> "
                f"{display_window_end(anchor).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return run_merge_window(
                args,
                log_dir,
                increase_dir,
                bundle_map,
                window_start,
                anchor,
                send_alerts=False,
            )

        anchor, window_start, _ = previous_half_hour_window(run_dt)
        result = run_merge_window(
            args,
            log_dir,
            increase_dir,
            bundle_map,
            window_start,
            anchor,
            send_alerts=not args.no_alert,
            use_cursor=args.run_at is None,
        )
        deleted = cleanup_old_outputs(args.output_dir, args.retention_days, run_dt, MERGE_OUTPUT_FILE_PREFIX)
        print(f"cleanup_deleted: {deleted}")
        return result

    # 单机模式：只扫描主机分片日志info log，输出统计结果并按需报警。
    log_dir = os.path.abspath(args.log_dir) if args.log_dir else DEFAULT_LOG_DIR
    log_prefix = DEFAULT_LOG_PREFIX
    bundle_map_file = os.path.join(log_dir, DEFAULT_BUNDLE_MAP_FILE) if args.log_dir else DEFAULT_BUNDLE_MAP_FILE
    log_files = find_log_files(log_dir, log_prefix)
    send_alerts = not args.no_alert

    bundle_map = load_bundle_map(bundle_map_file)
    if args.replay_time:
        anchor = args.replay_time
        window_start = anchor - timedelta(minutes=30)
        window_end = display_window_end(anchor)
        print(
            "replay_window: "
            f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> "
            f"{window_end.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        run_window(
            args,
            log_files,
            bundle_map,
            window_start.timestamp(),
            window_end.timestamp(),
            anchor,
            send_alerts=False,
        )
        return 0

    anchor, window_start, window_end = previous_half_hour_window(run_dt)
    run_window(
        args,
        log_files,
        bundle_map,
        window_start.timestamp(),
        window_end.timestamp(),
        anchor,
        send_alerts=send_alerts,
        use_cursor=args.run_at is None,
    )
    deleted = cleanup_old_clk_stat_outputs(args.output_dir, args.retention_days, run_dt)
    print(f"cleanup_deleted: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
