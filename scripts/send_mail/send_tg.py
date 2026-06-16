"""
python调用示例：
    from send_tg import send_telegram

    result = send_telegram("ChatID", "test message")
"""

import os
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

CONFIG_PATH = Path(__file__).with_name("send_mail.conf")


def load_config(path=None):
    # 默认读取同目录配置，也可以用 SEND_MAIL_CONFIG 指定其他配置文件。
    config_path = Path(path or os.environ.get("SEND_MAIL_CONFIG") or CONFIG_PATH)
    config = {}

    with config_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]

            config[key.strip()] = value

    if not config.get("TELEGRAM_BOT_TOKEN"):
        raise ValueError("Missing telegram config: TELEGRAM_BOT_TOKEN")

    return config


def send_telegram(chat_id, message, bot_token=None, timeout=10):
    try:
        config = load_config()
    except Exception as exc:
        print(f"warning: send_telegram failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return "failed"

    token = bot_token or config["TELEGRAM_BOT_TOKEN"]

    if not token or not chat_id:
        print("warning: send_telegram failed: missing bot token or chat id", file=sys.stderr)
        return "failed"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
        }
    ).encode("utf-8")

    request = urllib.request.Request(url, data=data, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"warning: send_telegram failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return "failed"

    return "sent"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <chat_id> <message>", file=sys.stderr)
        sys.exit(1)

    result = send_telegram(sys.argv[1], sys.argv[2])
    print(result)
    sys.exit(0 if result == "sent" else 1)
