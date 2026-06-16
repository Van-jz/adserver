#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SEND_MAIL_CONFIG:-$SCRIPT_DIR/send_mail.conf}"

# 默认读取同目录配置，也可以用 SEND_MAIL_CONFIG 指定其他配置文件。
if [[ ! -f "$CONFIG_FILE" ]]; then
  printf 'Telegram config not found: %s\n' "$CONFIG_FILE" >&2
  return 1 2>/dev/null || exit 1
fi

source "$CONFIG_FILE"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  printf 'Missing telegram config: TELEGRAM_BOT_TOKEN\n' >&2
  return 1 2>/dev/null || exit 1
fi

send_telegram() {
  local chat_id="$1"
  local msg="$2"

  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${chat_id}" \
    -d text="${msg}"
}

#exsample:
#send_telegram "ChatID" "test message"
