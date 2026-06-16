#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并主机与增量 postshow 日志，按 bundle 统计前一个半小时窗口的点击量。

脚本功能：
1. 根据脚本运行时间确定上一个半小时统计窗口，例如 13:10 统计 12:30-12:59。
2. 扫描当前目录中的 info.prod0320.*.part_*.log，以及 increase_info_log 目录中分片结束时间落在统计窗口后的增量日志。
3. 复用 bundle_clk_monitor.py 的点击解析、click_id 去重、bundle 聚合和输出格式。
4. 将结果写入 clk_stat_merge/clk_stat_merge.YYYYMMDD-HHMM。
5. 参照 bundle_clk_monitor.py 发送零点击和点击下降报警，报警中的机器标识固定为“线上总计”。
6. 支持通过 --time 重跑指定时间前 30 分钟的数据，重跑时不发送报警。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bundle_clk_monitor import (
    DEFAULT_BUNDLE_MAP_FILE,
    DEFAULT_LOG_PREFIX,
    build_output_text,
    build_rows,
    load_bundle_map,
    render_table,
    scan_window_clicks,
)


DEFAULT_LOG_DIR = os.getcwd()
DEFAULT_INCREASE_DIR_NAME = "increase_info_log"
DEFAULT_OUTPUT_DIR = "/data/disk0/home/luoxun/logs/springboot-scaffold/clk_stat_merge"
OUTPUT_FILE_PREFIX = "clk_stat_merge"
DEFAULT_CURSOR_FILE_NAME = ".bundle_clk_monitor_merge.cursor.json"
MAIL_ALERT_MINUTES = 30
MAIL_ALERT_TO = "hanjing915@qq.com"
TG_CHAT_IDS = "8691808668,-5361073302"
CLICK_DROP_ALERT_THRESHOLD = 0.10
ALERT_TARGET_NAME = "线上总计"
LOG_FILE_RE = re.compile(
    rf"^{re.escape(DEFAULT_LOG_PREFIX)}(?:\.[^_]+)?_(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.part_(?P<part>\d+)\.log$"
)
INCREASE_LOG_RE = re.compile(r"^increase_info_log\..*\.(?P<stamp>\d{8}\.\d{4})(?:\.\d+)?$")


def script_dir() -> str:
    """返回当前脚本所在目录，用来定位相邻的 send_mail 模块。"""
    return os.path.dirname(os.path.abspath(__file__))


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


def parse_log_file_name(name: str) -> Optional[Tuple[str, int]]:
    """Parse info log name and return (date, part)."""
    match = LOG_FILE_RE.match(name)
    if not match:
        return None
    return match.group("date"), int(match.group("part"))


def find_main_log_files(
    log_dir: str,
    target_date: str,
    window_start: datetime,
    window_end: datetime,
) -> List[str]:
    """Find current-directory info logs for the target date and likely window."""
    try:
        names = os.listdir(log_dir)
    except OSError as exc:
        raise RuntimeError(f"cannot list log dir {log_dir}: {exc}") from exc

    candidates = []
    day_start_ts = datetime.strptime(target_date, "%Y-%m-%d").timestamp()
    window_start_ts = window_start.timestamp()
    window_end_ts = window_end.timestamp()
    for name in names:
        parsed = parse_log_file_name(name)
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
    """Find increase_info_log files whose filename timestamp is a slice end in this window."""
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


def get_cursor_file_path(output_dir: str, cursor_file: Optional[str]) -> str:
    """Return the state file used by automatic mode to resume the active main log."""
    if cursor_file:
        return os.path.abspath(cursor_file)
    return os.path.join(os.path.abspath(output_dir), DEFAULT_CURSOR_FILE_NAME)


def load_scan_cursor(cursor_file: str, main_log_files: List[str], window_start: datetime) -> Dict[str, int]:
    """Load a saved main-log read position when it is safe for the current automatic window."""
    try:
        with open(cursor_file, "r", encoding="utf-8") as f:
            cursor = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: cannot read merge cursor {cursor_file}: {exc}", file=sys.stderr)
        return {}

    if not isinstance(cursor, dict):
        return {}

    log_file = cursor.get("log_file")
    position = cursor.get("position")
    cursor_time = cursor.get("log_time")
    if not isinstance(log_file, str) or not isinstance(position, int) or position <= 0:
        return {}
    if log_file not in main_log_files:
        return {}
    if isinstance(cursor_time, (int, float)) and cursor_time > window_start.timestamp():
        return {}

    try:
        if os.path.getsize(log_file) < position:
            return {}
    except OSError as exc:
        print(f"warning: cannot stat merge cursor log {log_file}: {exc}", file=sys.stderr)
        return {}

    return {log_file: position}


def save_scan_cursor(cursor_file: str, cursor: Dict[str, Any]) -> None:
    """Persist the next automatic-mode scan position."""
    try:
        cursor_dir = os.path.dirname(cursor_file)
        if cursor_dir:
            os.makedirs(cursor_dir, exist_ok=True)
        with open(cursor_file, "w", encoding="utf-8") as f:
            json.dump(cursor, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
    except OSError as exc:
        print(f"warning: cannot write merge cursor {cursor_file}: {exc}", file=sys.stderr)


def clear_scan_cursor(cursor_file: str) -> None:
    """Remove the automatic-mode scan cursor when the tracked log reached EOF."""
    try:
        os.remove(cursor_file)
    except FileNotFoundError:
        return
    except OSError as exc:
        print(f"warning: cannot remove merge cursor {cursor_file}: {exc}", file=sys.stderr)


def update_scan_cursor(
    cursor_file: str,
    main_log_files: List[str],
    file_positions: Dict[str, Dict[str, Any]],
) -> None:
    """Keep a cursor only for the latest main log that stopped before EOF."""
    for log_file in reversed(main_log_files):
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


def write_output_file(output_dir: str, output_text: str, output_dt: datetime) -> str:
    """Write this run to clk_stat_merge.YYYYMMDD-HHMM and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    output_file = get_output_file_path(output_dir, output_dt)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)
        f.write("\n")
    return output_file


def get_output_file_path(output_dir: str, run_dt: datetime) -> str:
    """按运行时间拼出对应的 clk_stat_merge 文件路径。"""
    return os.path.join(output_dir, f"{OUTPUT_FILE_PREFIX}.{run_dt.strftime('%Y%m%d-%H%M')}")


def read_total_clicks_from_output(path: str) -> Optional[int]:
    """读取 clk_stat_merge 文件里的 total_clicks；兼容历史追加文件，取最后一次结果。"""
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
        print(f"warning: cannot read yesterday {OUTPUT_FILE_PREFIX} {path}: {exc}", file=sys.stderr)
        return None

    if not totals:
        print(f"warning: cannot find total_clicks in yesterday {OUTPUT_FILE_PREFIX}: {path}", file=sys.stderr)
        return None
    return totals[-1]


def ensure_send_mail_module_path() -> None:
    """Add the adjacent send_mail directory to sys.path for alert helpers."""
    send_mail_dir = os.path.abspath(os.path.join(script_dir(), "..", "send_mail"))
    if send_mail_dir not in sys.path:
        sys.path.insert(0, send_mail_dir)


def send_alert_mail(subject: str, content: str, warning_name: str) -> str:
    """Send an alert mail and keep errors non-fatal for monitor runs."""
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
    """Return configured Telegram chat ids from the script constant."""
    if isinstance(TG_CHAT_IDS, str):
        return [chat_id.strip() for chat_id in TG_CHAT_IDS.split(",") if chat_id.strip()]
    return [str(chat_id).strip() for chat_id in TG_CHAT_IDS if str(chat_id).strip()]


def send_alert_tg(content: str, warning_name: str) -> str:
    """Send a Telegram alert with the same body content as the alert mail."""
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
    """Send an alert through mail and Telegram using the same body content."""
    return {
        "mail": send_alert_mail(subject, content, warning_name),
        "tg": send_alert_tg(content, warning_name),
    }


def maybe_send_zero_clicks_alert(
    minutes: int,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[Dict[str, str]]:
    """满足 30 分钟以上且零点击时，发送邮件和 Telegram 报警。"""
    if minutes < MAIL_ALERT_MINUTES or total_clicks != 0:
        return None

    subject = f"[clk_monitor] {ALERT_TARGET_NAME} {minutes} minutes zero clicks alert"
    content = "\n".join(
        [
            f"！{ALERT_TARGET_NAME}已经{minutes}分钟没有点击了！",
            f"线上总计: {ALERT_TARGET_NAME}",
            f"统计时间窗 minutes: {minutes}",
            f"总点击 total_clicks: {total_clicks}",
            f"日志文件 log_file: {latest_log_file}",
            f"扫描时间窗 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
        ]
    )
    return send_alert_notifications(subject, content, "zero clicks alert")


def maybe_send_click_drop_alert(
    output_dir: str,
    run_dt: datetime,
    total_clicks: int,
    latest_log_file: str,
    scanned_range: str,
    output_file: str,
) -> Optional[Dict[str, str]]:
    """对比昨天同时间总点击，下降超过阈值时发送邮件和 Telegram 报警。"""
    yesterday_dt = run_dt - timedelta(days=1)
    yesterday_file = get_output_file_path(output_dir, yesterday_dt)
    yesterday_total_clicks = read_total_clicks_from_output(yesterday_file)
    if yesterday_total_clicks is None:
        print(f"info: no yesterday {OUTPUT_FILE_PREFIX} data for same time: {yesterday_file}; skip click drop alert")
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
    subject = f"[clk_monitor] {ALERT_TARGET_NAME} clicks dropped {drop_percent:.1f}% alert"
    content = "\n".join(
        [
            f"！{ALERT_TARGET_NAME}当轮点击较昨天同时间下降超过{CLICK_DROP_ALERT_THRESHOLD:.0%}！",
            f"线上总计: {ALERT_TARGET_NAME}",
            f"当前时间 current_time: {run_dt.strftime('%Y-%m-%d %H:%M')}",
            f"昨日同期 yesterday_same_time: {yesterday_dt.strftime('%Y-%m-%d %H:%M')}",
            f"本轮总点击 current_total_clicks: {total_clicks}",
            f"昨日同期总点击 yesterday_total_clicks: {yesterday_total_clicks}",
            f"下跌比例 drop_percent: {drop_percent:.2f}%",
            f"日志文件 log_file: {latest_log_file}",
            f"扫描时间段 scanned_log_time_range: {scanned_range}",
            f"输出文件 output_file: {output_file}",
            f"昨日文件 yesterday_output_file: {yesterday_file}",
        ]
    )
    return send_alert_notifications(subject, content, "click drop alert")


def cleanup_old_outputs(output_dir: str, retention_days: int, now_dt: datetime) -> int:
    """Remove old clk_stat_merge.* files from output_dir."""
    cutoff_ts = (now_dt - timedelta(days=retention_days)).timestamp()
    deleted = 0
    try:
        names = os.listdir(output_dir)
    except OSError as exc:
        print(f"warning: cannot list output dir for cleanup: {output_dir}: {exc}", file=sys.stderr)
        return deleted

    for name in names:
        if not name.startswith(f"{OUTPUT_FILE_PREFIX}."):
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
            print(f"warning: cannot remove old merge output {path}: {exc}", file=sys.stderr)
    return deleted


def join_log_file_names(paths: List[str]) -> str:
    """Format selected input files without changing the original output field name."""
    if not paths:
        return "N/A"
    return ", ".join(paths)


def run_window(
    args: argparse.Namespace,
    log_dir: str,
    increase_dir: str,
    bundle_map: dict,
    window_start: datetime,
    anchor: datetime,
    send_alerts: bool,
    use_cursor: bool = False,
) -> None:
    """扫描一个半小时窗口，输出统计结果并按需发送报警。"""
    window_end = display_window_end(anchor)
    main_log_files = find_main_log_files(log_dir, window_start.strftime("%Y-%m-%d"), window_start, window_end)
    # 跨零点窗口要额外带上结束日期的主日志，避免 23:30-23:59 这类窗口附近漏文件。
    if window_end.strftime("%Y-%m-%d") != window_start.strftime("%Y-%m-%d"):
        main_log_files.extend(find_main_log_files(log_dir, window_end.strftime("%Y-%m-%d"), window_start, window_end))
    increase_log_files = find_increase_log_files(increase_dir, window_start, anchor)
    selected_log_files = main_log_files + increase_log_files
    selected_log_file_text = join_log_file_names(selected_log_files)
    scanned_range = f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> {window_end.strftime('%Y-%m-%d %H:%M:%S')}"
    cursor_file = get_cursor_file_path(args.output_dir, args.cursor_file)
    start_positions = load_scan_cursor(cursor_file, main_log_files, window_start) if use_cursor else {}

    if selected_log_files:
        # 统计规则完全复用原脚本：解析 postshow、过滤域名、click_id 去重并归因 bundle。
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
    output_file = write_output_file(args.output_dir, output_text, anchor)
    print(f"output_file: {output_file}")

    if not send_alerts:
        return

    drop_alert_result = maybe_send_click_drop_alert(
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
    alert_result = maybe_send_zero_clicks_alert(
        30,
        len(window_events),
        selected_log_file_text,
        scanned_range,
        output_file,
    )
    if alert_result:
        print(f"alert_mail: {alert_result.get('mail')}")
        print(f"alert_tg: {alert_result.get('tg')}")


def parse_args() -> argparse.Namespace:
    """Define command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor merged half-hour click counts by bundle.")
    parser.add_argument("--top", type=int, default=20, help="number of bundles to display")
    parser.add_argument("--time", dest="replay_time", type=parse_replay_time, help="replay anchor time, e.g. '20260615 1600' scans the previous 30 minutes")
    parser.add_argument("--all", action="store_true", help="show all bundles")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="directory containing info.prod0320.*.part_*.log")
    parser.add_argument(
        "--increase-dir",
        default=None,
        help="directory containing increase_info_log files; default is log-dir/increase_info_log",
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="directory to write clk_stat_merge.YYYYMMDD-hhmm")
    parser.add_argument("--retention-days", type=int, default=3, help="days to keep clk_stat_merge.* outputs")
    parser.add_argument("--cursor-file", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--run-at", type=parse_replay_time, default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    """Script entry: choose the previous half-hour slot, scan logs, and write stats."""
    args = parse_args()
    run_dt = args.run_at or datetime.now()
    if args.top is not None and args.top <= 0:
        print("error: --top must be positive", file=sys.stderr)
        return 2
    if args.retention_days <= 0:
        print("error: --retention-days must be positive", file=sys.stderr)
        return 2
    if args.replay_time and not is_half_hour_boundary(args.replay_time):
        print("error: --time must be on a 00 or 30 minute boundary", file=sys.stderr)
        return 2

    log_dir = os.path.abspath(args.log_dir)
    increase_dir = os.path.abspath(args.increase_dir or os.path.join(log_dir, DEFAULT_INCREASE_DIR_NAME))

    # bundle 映射文件仍放在日志根目录，与原 bundle_clk_monitor.py 的运行方式保持一致。
    bundle_map = load_bundle_map(os.path.join(log_dir, DEFAULT_BUNDLE_MAP_FILE))

    if args.replay_time:
        anchor = args.replay_time
        window_start = anchor - timedelta(minutes=30)
        print(
            "replay_window: "
            f"{window_start.strftime('%Y-%m-%d %H:%M:%S')} -> "
            f"{display_window_end(anchor).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        run_window(args, log_dir, increase_dir, bundle_map, window_start, anchor, send_alerts=False)
        return 0

    anchor, window_start, _ = previous_half_hour_window(run_dt)
    run_window(
        args,
        log_dir,
        increase_dir,
        bundle_map,
        window_start,
        anchor,
        send_alerts=True,
        use_cursor=args.run_at is None,
    )
    print(f"cleanup_deleted: {cleanup_old_outputs(args.output_dir, args.retention_days, run_dt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
