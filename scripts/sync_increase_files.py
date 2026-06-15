#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备机增量日志同步脚本。

脚本功能：
1. 在备机按 orchestrator_unified.py 的日志文件定位点规则读取 info 日志增量。
2. 只保留 orchestrator_unified.py 实际需要解析的 postshow 请求日志行。
3. 将过滤后的增量文件 rsync 到主机 increase_info_log 目录。
4. 从主机拉取 click_id_bundle_map.json 并通过临时文件校验后原子替换本地文件。

脚本参数；主备 IP、日志目录、状态文件等都在 CONFIG 中配置。
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shlex


CONFIG = {
    # 备机产生日志，主机接收过滤后的增量日志。
    "backup_ip": "47.245.111.231",
    "main_host": "root@47.236.3.20",
    # 日志发现规则保持和 orchestrator_unified.py 一致。
    "log_dir": "/data/disk0/home/luoxun/logs/springboot-scaffold",
    "log_prefix": "info.prod0320",
    "increase_dir": "/data/disk0/home/luoxun/logs/springboot-scaffold/increase_info_log",
    "remote_increase_dir": "/data/disk0/home/luoxun/logs/springboot-scaffold/increase_info_log",
    "state_file": "/data/disk0/home/luoxun/logs/springboot-scaffold/sync_increase_files_state.json",
    "remote_bundle_map": "/data/disk0/home/luoxun/logs/springboot-scaffold/click_id_bundle_map.json",
    "local_bundle_map": "/data/disk0/home/luoxun/logs/springboot-scaffold/click_id_bundle_map.json",
    "rsync_options": ["-av", "--partial"],
    "read_chunk_size": 1024 * 1024,
    # orchestrator_unified.py 只从包含该 marker 的日志行提取 requestBody。
    "orchestrator_request_marker": "收到 kwaiadsinfo postshow 请求数据: ",
}


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("sync_increase_files")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    # 只输出到控制台，由 cron 或调用方决定是否重定向到日志文件。
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def run_cmd(cmd: List[str], logger: logging.Logger, step: str) -> subprocess.CompletedProcess:
    logger.info("%s: %s", step, " ".join(shlex.quote(part) for part in cmd))
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.stdout.strip():
        logger.info("%s stdout: %s", step, result.stdout.strip())
    if result.stderr.strip():
        logger.info("%s stderr: %s", step, result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"{step} failed with exit code {result.returncode}")
    return result


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required command not found: {name}")


def load_state(logger: logging.Logger) -> Dict[str, Any]:
    # 状态文件记录每个日志文件的字节定位点，避免重复扫描。
    state_file = Path(CONFIG["state_file"])
    try:
        with state_file.open("r", encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        logger.info("state file not found, using empty state: %s", state_file)
        return {"last_run": None, "log_positions": {}}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"state file is not valid JSON: {state_file}: {exc}") from exc

    if not isinstance(state, dict):
        raise RuntimeError(f"state file root must be an object: {state_file}")
    if not isinstance(state.get("log_positions"), dict):
        state["log_positions"] = {}
    state.pop("synced_increase_files", None)
    if not isinstance(state.get("pending_increase_files"), dict):
        state["pending_increase_files"] = {}
    return state


def save_state(state: Dict[str, Any], logger: logging.Logger) -> None:
    # 先写临时文件再原子替换，避免进程中断留下半截 JSON。
    state_file = Path(CONFIG["state_file"])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = state_file.with_name(f"{state_file.name}.tmp.{os.getpid()}")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_file, state_file)
    logger.info("state saved: %s", state_file)


def parse_log_filename(filename: str) -> Optional[Dict[str, Any]]:
    log_prefix = re.escape(CONFIG["log_prefix"])
    pattern = re.compile(
        rf"^{log_prefix}(?:\.(?P<ip>[^_]+))?_(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.part_(?P<part>\d+)\.log$"
    )
    match = pattern.match(filename)
    if not match:
        return None
    return {
        "date": match.group("date"),
        "part": int(match.group("part")),
        "ip": match.group("ip") or "",
    }


def find_log_files_for_latest_date(logger: logging.Logger) -> List[Dict[str, Any]]:
    # 只处理最新日期的日志文件，排序规则与 orchestrator_unified.py 保持一致。
    log_dir = Path(CONFIG["log_dir"])
    log_prefix = CONFIG["log_prefix"]
    if not log_dir.is_dir():
        raise RuntimeError(f"log_dir does not exist or is not a directory: {log_dir}")

    log_files = []
    unmatched = []
    for path in log_dir.iterdir():
        if not path.is_file():
            continue
        filename = path.name
        if not (filename.startswith(log_prefix) and filename.endswith(".log")):
            continue
        parsed = parse_log_filename(filename)
        if not parsed:
            unmatched.append(filename)
            continue
        log_files.append({
            "path": str(path),
            "name": filename,
            "date": parsed["date"],
            "part": parsed["part"],
            "ip": parsed["ip"],
            "mtime": path.stat().st_mtime,
        })

    if not log_files:
        raise RuntimeError(f"no parseable info log files found in {log_dir}")
    if unmatched:
        logger.warning(
            "skipped %d unmatched log files: %s",
            len(unmatched),
            ", ".join(sorted(unmatched)[:5]),
        )

    latest_date = max(item["date"] for item in log_files)
    selected = [item for item in log_files if item["date"] == latest_date]
    selected.sort(key=lambda item: (item["date"], item["part"], item["ip"], item["name"]))
    return selected


def get_log_start_position(state: Dict[str, Any], log_file: str) -> int:
    # 只从 log_positions 读取指定日志文件的字节定位点。
    log_file_abs = str(Path(log_file).resolve())
    log_positions = state.get("log_positions", {})
    if isinstance(log_positions, dict):
        for key in (log_file, log_file_abs):
            if key in log_positions:
                try:
                    return int(log_positions[key])
                except (TypeError, ValueError):
                    return 0
    return 0


def next_increase_path() -> Path:
    increase_dir = Path(CONFIG["increase_dir"])
    timestamp = datetime.now().strftime("%Y%m%d.%H%M")
    base_name = f"increase_info_log.{CONFIG['backup_ip']}.{timestamp}"
    candidate = increase_dir / base_name
    if not candidate.exists():
        return candidate

    suffix = 1
    while True:
        candidate = increase_dir / f"{base_name}.{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def plan_log_increments(log_files: List[Dict[str, Any]], state: Dict[str, Any], logger: logging.Logger) -> List[Dict[str, Any]]:
    # 这里仅规划每个日志文件的新字节范围，真正过滤在写增量文件时完成。
    increments = []
    for item in log_files:
        log_path = Path(item["path"])
        file_size = log_path.stat().st_size
        start_position = get_log_start_position(state, str(log_path))
        if start_position > file_size:
            logger.warning(
                "log file is smaller than saved position, reset to 0: %s, position=%s, size=%s",
                log_path,
                start_position,
                file_size,
            )
            start_position = 0

        end_position = file_size
        logger.info(
            "log increment planned: path=%s, date=%s, part=%s, ip=%s, start=%s, end=%s, bytes=%s",
            log_path,
            item["date"],
            item["part"],
            item["ip"] or "(no ip)",
            start_position,
            end_position,
            end_position - start_position,
        )
        if end_position > start_position:
            increments.append({
                "path": log_path,
                "start": start_position,
                "end": end_position,
                "bytes": end_position - start_position,
            })
    return increments


def serialize_increments(increments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "path": str(increment["path"]),
            "start": int(increment["start"]),
            "end": int(increment["end"]),
            "bytes": int(increment["bytes"]),
        }
        for increment in increments
    ]


def deserialize_increments(items: Any, source: str) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        raise RuntimeError(f"pending increase increments must be a list: {source}")

    increments = []
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError(f"invalid pending increase item: {source}")
        increments.append({
            "path": Path(str(item["path"])),
            "start": int(item["start"]),
            "end": int(item["end"]),
            "bytes": int(item["bytes"]),
        })
    return increments


def register_pending_increase_file(
    state: Dict[str, Any],
    increase_file: Path,
    increments: List[Dict[str, Any]],
    written_bytes: int,
    matched_lines: int,
    reason: str,
    logger: logging.Logger,
) -> None:
    # 待同步文件的恢复信息写入 state 和运行日志，不再额外生成 .meta.json 文件。
    pending = state.setdefault("pending_increase_files", {})
    pending[increase_file.name] = {
        "size": increase_file.stat().st_size,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "written_bytes": int(written_bytes),
        "matched_lines": int(matched_lines),
        "reason": reason,
        "increments": serialize_increments(increments),
    }
    logger.info(
        "pending increase registered: file=%s, size=%s, written_bytes=%s, matched_lines=%s, reason=%s, increments=%s",
        increase_file.name,
        increase_file.stat().st_size,
        written_bytes,
        matched_lines,
        reason,
        json.dumps(pending[increase_file.name]["increments"], ensure_ascii=False),
    )


def line_has_orchestrator_request(line: bytes) -> bool:
    # 过滤口径直接参考 orchestrator_unified.py 的 extract_request_body 入口。
    marker = CONFIG["orchestrator_request_marker"].encode("utf-8")
    return marker in line


def write_empty_increase_file(increments: List[Dict[str, Any]], reason: str, logger: logging.Logger) -> Path:
    # 即使本轮没有可同步内容，也创建 0 字节文件作为本次运行的心跳标记。
    output_path = next_increase_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.touch()
    logger.info("empty increase file touched: %s, reason=%s", output_path, reason)
    return output_path


def write_increase_file(increments: List[Dict[str, Any]], logger: logging.Logger) -> Tuple[Path, int, int]:
    # 扫描完整增量区间，但只把 orchestrator 需要的 postshow 请求日志行写入文件。
    output_path = next_increase_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_written = 0
    matched_lines = 0
    scanned_bytes = 0
    with output_path.open("wb") as out_f:
        for increment in increments:
            remaining = increment["end"] - increment["start"]
            with increment["path"].open("rb") as in_f:
                in_f.seek(increment["start"])
                while remaining > 0:
                    line = in_f.readline(remaining)
                    if not line:
                        raise RuntimeError(f"log file ended before planned position: {increment['path']}")
                    remaining -= len(line)
                    scanned_bytes += len(line)
                    if line_has_orchestrator_request(line):
                        out_f.write(line)
                        total_written += len(line)
                        matched_lines += 1

    size = output_path.stat().st_size
    if size <= 0:
        logger.info(
            "no orchestrator-relevant log lines found; scanned_bytes=%s, matched_lines=%s",
            scanned_bytes,
            matched_lines,
        )
        return output_path, 0, 0
    if size != total_written:
        raise RuntimeError(f"increase file size mismatch: {output_path}, stat={size}, written={total_written}")

    logger.info(
        "increase file written: %s, bytes=%s, scanned_bytes=%s, matched_lines=%s",
        output_path,
        size,
        scanned_bytes,
        matched_lines,
    )
    return output_path, total_written, matched_lines


def ensure_remote_dir(logger: logging.Logger) -> None:
    remote_dir = CONFIG["remote_increase_dir"]
    cmd = ["ssh", CONFIG["main_host"], f"test -d {shlex.quote(remote_dir)}"]
    run_cmd(cmd, logger, "check remote increase dir")
    logger.info("remote increase dir exists: %s:%s", CONFIG["main_host"], remote_dir)


def remote_file_size(remote_path: str, logger: logging.Logger) -> int:
    cmd = ["ssh", CONFIG["main_host"], f"stat -c %s {shlex.quote(remote_path)}"]
    result = run_cmd(cmd, logger, f"remote stat {remote_path}")
    try:
        return int(result.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"failed to parse remote file size for {remote_path}: {result.stdout!r}") from exc


def rsync_to_main(local_file: Path, logger: logging.Logger) -> None:
    if not local_file.is_file():
        raise RuntimeError(f"local file does not exist: {local_file}")
    local_size = local_file.stat().st_size

    remote_dir = CONFIG["remote_increase_dir"].rstrip("/") + "/"
    cmd = ["rsync", *CONFIG["rsync_options"], str(local_file), f"{CONFIG['main_host']}:{remote_dir}"]
    run_cmd(cmd, logger, f"rsync push {local_file.name}")

    remote_path = f"{remote_dir}{local_file.name}"
    pushed_size = remote_file_size(remote_path, logger)
    if pushed_size != local_size:
        raise RuntimeError(
            f"remote size mismatch after rsync push: {local_file.name}, local={local_size}, remote={pushed_size}"
        )
    logger.info("rsync push verified: %s, bytes=%s", local_file.name, local_size)


def sync_pending_increase_files(state: Dict[str, Any], logger: logging.Logger) -> bool:
    # 上次写出但未成功推送的增量文件，会在本次处理新日志前先补推。
    increase_dir = Path(CONFIG["increase_dir"])
    increase_dir.mkdir(parents=True, exist_ok=True)
    pending = state.setdefault("pending_increase_files", {})
    if not pending:
        logger.info("no pending increase files to push")
        return False

    logger.info("found %d pending increase files to push", len(pending))
    changed = False
    for filename in sorted(pending):
        local_file = increase_dir / filename
        if not local_file.is_file():
            raise RuntimeError(f"pending increase file is missing: {local_file}")

        rsync_to_main(local_file, logger)
        increments = deserialize_increments(pending[filename].get("increments", []), filename)
        if increments:
            update_positions_after_success(state, increments)
        del pending[filename]
        changed = True
    return changed


def update_positions_after_success(state: Dict[str, Any], increments: List[Dict[str, Any]]) -> None:
    # 只有对应增量文件已推送成功，或增量区间没有任何相关日志行时，才推进定位点。
    log_positions = state.setdefault("log_positions", {})
    for increment in increments:
        log_file_abs = str(increment["path"].resolve())
        end_position = int(increment["end"])
        log_positions[log_file_abs] = end_position

    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def refresh_bundle_map(logger: logging.Logger) -> None:
    # 拉取主机上的 bundle map，校验大小和 JSON 格式后再替换本地文件。
    remote_path = CONFIG["remote_bundle_map"]
    local_path = Path(CONFIG["local_bundle_map"])
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = local_path.with_name(f"{local_path.name}.tmp.{os.getpid()}")

    remote_size_before = remote_file_size(remote_path, logger)
    if remote_size_before <= 0:
        raise RuntimeError(f"remote bundle map is empty: {remote_path}")

    cmd = [
        "rsync",
        *CONFIG["rsync_options"],
        f"{CONFIG['main_host']}:{remote_path}",
        str(tmp_path),
    ]
    try:
        run_cmd(cmd, logger, "rsync pull click_id_bundle_map")
        if not tmp_path.is_file():
            raise RuntimeError(f"bundle map temp file was not created: {tmp_path}")

        local_size = tmp_path.stat().st_size
        remote_size_after = remote_file_size(remote_path, logger)
        if local_size != remote_size_after:
            raise RuntimeError(
                "bundle map size mismatch after rsync pull: "
                f"local={local_size}, remote_before={remote_size_before}, remote_after={remote_size_after}"
            )

        with tmp_path.open("r", encoding="utf-8") as f:
            parsed = json.load(f)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"bundle map JSON root must be an object: {tmp_path}")

        os.replace(tmp_path, local_path)
        logger.info("bundle map refreshed: %s, bytes=%s, entries=%s", local_path, local_size, len(parsed))
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        finally:
            raise


def main() -> int:
    logger = setup_logger()
    logger.info("=" * 80)
    logger.info("sync increase files started")

    try:
        require_tool("ssh")
        require_tool("rsync")

        Path(CONFIG["increase_dir"]).mkdir(parents=True, exist_ok=True)
        state = load_state(logger)

        ensure_remote_dir(logger)
        if sync_pending_increase_files(state, logger):
            save_state(state, logger)

        log_files = find_log_files_for_latest_date(logger)
        logger.info("latest log date: %s, files=%d", log_files[0]["date"], len(log_files))
        for item in log_files:
            logger.info(
                "selected log file: %s (date=%s, part=%s, ip=%s)",
                item["path"],
                item["date"],
                item["part"],
                item["ip"] or "(no ip)",
            )

        increments = plan_log_increments(log_files, state, logger)
        if increments:
            increase_file, written_bytes, matched_lines = write_increase_file(increments, logger)
            register_pending_increase_file(
                state,
                increase_file,
                increments,
                written_bytes,
                matched_lines,
                "log_increment",
                logger,
            )
            save_state(state, logger)
            rsync_to_main(increase_file, logger)
            update_positions_after_success(state, increments)
            state.setdefault("pending_increase_files", {}).pop(increase_file.name, None)
            save_state(state, logger)
        else:
            logger.info("no new info log bytes found; touch empty increase file")
            increase_file = write_empty_increase_file([], "no_new_info_log_bytes", logger)
            register_pending_increase_file(
                state,
                increase_file,
                [],
                0,
                0,
                "no_new_info_log_bytes",
                logger,
            )
            save_state(state, logger)
            rsync_to_main(increase_file, logger)
            state.setdefault("pending_increase_files", {}).pop(increase_file.name, None)
            state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_state(state, logger)

        refresh_bundle_map(logger)
        logger.info("sync increase files completed")
        logger.info("=" * 80)
        return 0
    except Exception as exc:
        logger.exception("sync increase files failed: %s", exc)
        logger.info("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
