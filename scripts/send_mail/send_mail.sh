#!/usr/bin/env bash
# 调用示例：
#   bash send_mail.sh "subject" "context" "name1@xxx.com,name2@xxx.com"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SEND_MAIL_CONFIG:-$SCRIPT_DIR/send_mail.conf}"

# 默认读取同目录配置，也可以用 SEND_MAIL_CONFIG 指定其他配置文件。
if [[ ! -f "$CONFIG_FILE" ]]; then
    printf 'Mail config not found: %s\n' "$CONFIG_FILE" >&2
    exit 1
fi

source "$CONFIG_FILE"

# 发送邮件所需的 SMTP 配置必须全部存在。
for name in SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASS; do
    if [[ -z "${!name:-}" ]]; then
        printf 'Missing mail config: %s\n' "$name" >&2
        exit 1
    fi
done

if [[ $# -lt 3 ]]; then
    printf 'Usage: %s <subject> <content> <to>\n' "$0" >&2
    exit 1
fi

SUBJECT="${1:-Hello Test}"
CONTENT="${2:-Hello Test 1993}"
TO="$3"
IFS=',' read -ra RECIPIENTS <<< "$TO"

MAIL_FILE="$(mktemp)"

cleanup() {
    rm -f "$MAIL_FILE"
}

trap cleanup EXIT

# 生成临时邮件内容文件，供 curl 通过 SMTPS 上传。
{
    printf 'From: %s\r\n' "$SMTP_USER"
    printf 'To: %s\r\n' "$TO"
    printf 'Subject: %s\r\n' "$SUBJECT"
    printf 'Content-Type: text/plain; charset=UTF-8\r\n'
    printf 'Content-Transfer-Encoding: 8bit\r\n'
    printf '\r\n'
    printf '%s\r\n' "$CONTENT"
} > "$MAIL_FILE"

# 使用 SMTP 配置登录并发送邮件。
CURL_ARGS=(
    --silent
    --show-error
    --fail
    --ssl-reqd
    --url "smtps://${SMTP_HOST}:${SMTP_PORT}"
    --user "${SMTP_USER}:${SMTP_PASS}"
    --mail-from "$SMTP_USER"
)

recipient_count=0
for recipient in "${RECIPIENTS[@]}"; do
    recipient="${recipient#"${recipient%%[![:space:]]*}"}"
    recipient="${recipient%"${recipient##*[![:space:]]}"}"
    if [[ -n "$recipient" ]]; then
        CURL_ARGS+=(--mail-rcpt "$recipient")
        recipient_count=$((recipient_count + 1))
    fi
done

if [[ "$recipient_count" -eq 0 ]]; then
    printf 'failed\n'
    exit 1
fi

if curl "${CURL_ARGS[@]}" --upload-file "$MAIL_FILE"; then
    printf 'sent\n'
else
    printf 'failed\n'
    exit 1
fi
