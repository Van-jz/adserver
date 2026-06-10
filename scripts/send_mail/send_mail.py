"""
python调用示例：
    from send_mail import send_mail

    result = send_mail(
        "subject",
        "context",
        "name1@xxx.com,name2@xxx.com"
    )
"""

import smtplib
import os
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path

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

    # 发送邮件所需的 SMTP 配置必须全部存在。
    missing = [
        key
        for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS")
        if not config.get(key)
    ]
    if missing:
        raise ValueError(f"Missing mail config: {', '.join(missing)}")

    return config


def send_mail(subject, content, to):
    server = None

    try:
        config = load_config()
        if isinstance(to, str):
            recipients = [
                recipient.strip()
                for recipient in to.split(",")
                if recipient.strip()
            ]
        else:
            recipients = [
                recipient.strip()
                for recipient in to
                if recipient.strip()
            ]
        if not recipients:
            return "failed"

        # 构造 UTF-8 纯文本邮件，标题、正文和收件人由调用方传入。
        msg = MIMEText(
            content,
            "plain",
            "utf-8"
        )

        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = config["SMTP_USER"]
        msg["To"] = ",".join(recipients)

        server = smtplib.SMTP_SSL(
            config["SMTP_HOST"],
            int(config["SMTP_PORT"])
        )

        server.login(
            config["SMTP_USER"],
            config["SMTP_PASS"]
        )

        server.sendmail(
            config["SMTP_USER"],
            recipients,
            msg.as_string()
        )
    except Exception:
        return "failed"
    finally:
        if server:
            # 无论发送是否成功，都关闭 SMTP 连接。
            server.quit()

    return "sent"
