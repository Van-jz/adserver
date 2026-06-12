#!/bin/bash

# Upload prod0320 info/error logs in the current log directory to OSS.
# Intended cron: run once per hour; error logs are uploaded only when hour == 01.

set -o pipefail

renice +10 $$ >/dev/null 2>&1 || true

OSS_PREFIX="${OSS_PREFIX:-oss://sg-ads/logs/}"
LOG_DIR="$PWD"
ENV_NAME="${ENV_NAME:-prod0320}"
LOG_KEEP_MAX="${LOG_KEEP_MAX:-20}"
ERROR_LOG_KEEP_MAX="${ERROR_LOG_KEEP_MAX:-10}"
ERROR_UPLOAD_HOUR="${ERROR_UPLOAD_HOUR:-01}"
DRY_RUN=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_DIR="/tmp/sync_${ENV_NAME}_logs_to_oss.lock"

show_help() {
    cat << EOF
用法: $0 [选项]

选项:
    --log-dir DIR            日志目录（默认: 当前目录）
    --oss-prefix PREFIX      OSS 目标前缀（默认: ${OSS_PREFIX}）
    --env ENV                环境名（默认: ${ENV_NAME}）
    --keep-max N             info 日志本地保留数量（默认: ${LOG_KEEP_MAX}）
    --error-keep-max N       error 日志本地保留数量（默认: ${ERROR_LOG_KEEP_MAX}）
    --error-hour HH          error 日志上传小时点（默认: ${ERROR_UPLOAD_HOUR}）
    --dry-run                只打印将处理的文件，不上传/删除
    -h, --help               显示此帮助信息

说明:
    - 每次运行都会执行 syncInfoLogOss。
    - 只有当前小时等于 --error-hour 时，才执行 syncErrorLogOss。
    - cron: 10 * * * * cd /data/disk0/home/luoxun/logs/springboot-scaffold && bash scripts/upload_log_to_oss.sh >> logs/upload_log_to_oss.log 2>&1
EOF
}

log_time() {
    date "+%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo "$(log_time) $1"
}

log_warn() {
    echo "$(log_time) $1"
}

log_error() {
    echo "$(log_time) $1"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --log-dir)
                if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                    log_error "选项 --log-dir 需要指定目录"
                    exit 1
                fi
                LOG_DIR="$2"
                shift 2
                ;;
            --oss-prefix)
                if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                    log_error "选项 --oss-prefix 需要指定 OSS 前缀"
                    exit 1
                fi
                OSS_PREFIX="$2"
                shift 2
                ;;
            --env)
                if [[ -z "${2:-}" ]] || [[ "$2" =~ ^- ]]; then
                    log_error "选项 --env 需要指定环境名"
                    exit 1
                fi
                ENV_NAME="$2"
                shift 2
                ;;
            --keep-max)
                if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_error "选项 --keep-max 需要指定非负整数"
                    exit 1
                fi
                LOG_KEEP_MAX="$2"
                shift 2
                ;;
            --error-keep-max)
                if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_error "选项 --error-keep-max 需要指定非负整数"
                    exit 1
                fi
                ERROR_LOG_KEEP_MAX="$2"
                shift 2
                ;;
            --error-hour)
                if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]{1,2}$ ]]; then
                    log_error "选项 --error-hour 需要指定小时，例如 01"
                    exit 1
                fi
                if (( 10#$2 > 23 )); then
                    log_error "选项 --error-hour 必须在 0-23 之间"
                    exit 1
                fi
                ERROR_UPLOAD_HOUR=$(printf "%02d" "$((10#$2))")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [[ "${OSS_PREFIX}" != */ ]]; then
        OSS_PREFIX="${OSS_PREFIX}/"
    fi

    LOCK_DIR="/tmp/sync_${ENV_NAME}_logs_to_oss.lock"
}

current_hour() {
    if [[ -n "${CURRENT_HOUR_OVERRIDE:-}" ]]; then
        printf "%02d" "$((10#$CURRENT_HOUR_OVERRIDE))"
    else
        date +"%H"
    fi
}

validate_log_dir() {
    if [[ ! -d "$LOG_DIR" ]]; then
        log_warn "无效目录路径=${LOG_DIR}"
        return 1
    fi
    return 0
}

collect_logs() {
    local level=$1
    local date_filter=${2:-}
    local files=()

    while IFS= read -r -d '' file; do
        local name
        name=$(basename "$file")

        if [[ "$name" != ${level}.${ENV_NAME}_*.log && "$name" != ${level}.${ENV_NAME}.*.log ]]; then
            continue
        fi

        if [[ -n "$date_filter" && "$name" != *"$date_filter"* ]]; then
            continue
        fi

        files+=("$file")
    done < <(find "$LOG_DIR" -maxdepth 1 -type f -name "${level}.${ENV_NAME}*.log" -print0 2>/dev/null)

    printf '%s\n' "${files[@]}"
}

sort_logs_by_date_and_seq() {
    awk '
        {
            file=$0
            name=file
            sub(/^.*\//, "", name)
            date="9999-99-99"
            seq=0
            if (match(name, /[0-9]{4}-[0-9]{2}-[0-9]{2}/)) {
                date=substr(name, RSTART, RLENGTH)
            }
            if (match(name, /part_[0-9]+\.log$/)) {
                seq=substr(name, RSTART + 5, RLENGTH - 9)
            } else if (match(name, /_[0-9]+\.log$/)) {
                seq=substr(name, RSTART + 1, RLENGTH - 5)
            }
            printf "%s\t%010d\t%s\n", date, seq, file
        }
    ' | sort -k1,1 -k2,2n -k3,3 | cut -f3-
}

upload_file() {
    local file=$1
    local name
    name=$(basename "$file")

    log_info "name=${name}"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "dry-run: ossutil cp ${file} ${OSS_PREFIX}${name}"
        return 0
    fi

    if ! ossutil cp "$file" "${OSS_PREFIX}${name}"; then
        log_error "e=ossutil cp failed: ${file}"
        return 1
    fi

    log_info "OSS文件上传成功：${name}"
    return 0
}

syncErrorLogOss() {
    log_info "执行syncErrorLogOss"

    if ! validate_log_dir; then
        return 0
    fi

    local files=()
    mapfile -t files < <(collect_logs "error" "" | sort_logs_by_date_and_seq)

    if (( ${#files[@]} <= ERROR_LOG_KEEP_MAX )); then
        log_info "error日志文件数量太少"
        return 0
    fi

    local upload_count=$(( ${#files[@]} - ERROR_LOG_KEEP_MAX ))
    local index=0

    local file
    for file in "${files[@]}"; do
        [[ -z "$file" ]] && continue
        if (( index >= upload_count )); then
            break
        fi

        if upload_file "$file"; then
            if [[ "$DRY_RUN" == true ]]; then
                log_info "dry-run: rm -f ${file}"
            elif ! rm -f "$file"; then
                log_error "e=删除error日志失败: ${file}"
            fi
            index=$((index + 1))
        else
            log_error "e=上传error日志失败: $(basename "$file")"
        fi
    done
}

syncInfoLogOss() {
    log_info "执行syncInfoLogOss"

    if ! validate_log_dir; then
        return 0
    fi

    local files=()
    mapfile -t files < <(collect_logs "info" "" | sort_logs_by_date_and_seq)

    if (( ${#files[@]} <= LOG_KEEP_MAX )); then
        log_info "日志文件数量太少"
        return 0
    fi

    local upload_count=$(( ${#files[@]} - LOG_KEEP_MAX ))
    local index=0
    local file

    for file in "${files[@]}"; do
        [[ -z "$file" ]] && continue
        if (( index >= upload_count )); then
            break
        fi

        if upload_file "$file"; then
            if [[ "$DRY_RUN" == true ]]; then
                log_info "dry-run: rm -f ${file}"
            elif ! rm -f "$file"; then
                log_error "e=删除info日志失败: ${file}"
            fi
            index=$((index + 1))
        else
            log_error "e=上传info日志失败: $(basename "$file")"
        fi
    done
}

cleanup() {
    rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}

main() {
    parse_args "$@"

    if [[ "$DRY_RUN" != true ]] && ! command -v ossutil >/dev/null 2>&1; then
        log_error "ossutil 未安装，请先安装"
        exit 1
    fi

    if ! mkdir "$LOCK_DIR" >/dev/null 2>&1; then
        log_warn "已有任务正在运行，跳过本次执行"
        exit 0
    fi
    trap cleanup EXIT

    local hour
    hour=$(current_hour)

    log_info "当前小时=${hour}"
    log_info "dry_run=${DRY_RUN}"
    log_info "info_keep_max=${LOG_KEEP_MAX}"
    log_info "error_keep_max=${ERROR_LOG_KEEP_MAX}"
    log_info "日志目录=${LOG_DIR}"
    log_info "OSS目录=${OSS_PREFIX}"

    if [[ "$hour" == "$ERROR_UPLOAD_HOUR" ]]; then
        syncErrorLogOss
    fi

    syncInfoLogOss
}

main "$@"
