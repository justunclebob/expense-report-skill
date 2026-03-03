#!/usr/bin/env python3
import argparse
import json
import mimetypes
import smtplib
import uuid
from email.message import EmailMessage
from pathlib import Path
from urllib.request import Request, urlopen


def latest_file(report_dir: Path, suffix: str):
    files = sorted(report_dir.glob(f"*{suffix}"))
    return files[-1] if files else None


def build_multipart(fields: dict[str, str], file_field: str, file_path: Path, file_name: str | None = None):
    boundary = f"----OpenClawBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for k, v in fields.items():
        parts.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(),
            str(v).encode("utf-8"),
            b"\r\n",
        ])

    ctype, _ = mimetypes.guess_type(str(file_path))
    ctype = ctype or "application/octet-stream"
    fname = file_name or file_path.name
    parts.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{fname}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])

    return boundary, b"".join(parts)


def send_email(sender, password, host, port, recipients, subject, body, attachment: Path, dry_run=False):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    ctype, _ = mimetypes.guess_type(str(attachment))
    maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
    msg.add_attachment(attachment.read_bytes(), maintype=maintype, subtype=subtype, filename=attachment.name)

    if dry_run:
        print(f"[dry-run] email -> {recipients} | attachment={attachment}")
        return

    with smtplib.SMTP_SSL(host, port) as s:
        s.login(sender, password)
        s.send_message(msg)
    print(f"email sent -> {recipients}")


def send_discord_via_bot(bot_token: str, channel_id: str, message: str, attachment: Path, dry_run=False):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    boundary, body = build_multipart(
        fields={"payload_json": json.dumps({"content": message}, ensure_ascii=False)},
        file_field="files[0]",
        file_path=attachment,
    )

    if dry_run:
        print(f"[dry-run] discord(bot) -> channel:{channel_id} | attachment={attachment}")
        return

    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(req, timeout=20) as r:
        _ = r.read()
    print(f"discord sent -> channel:{channel_id}")


def send_discord_via_webhook(webhook_url: str, message: str, attachment: Path, dry_run=False):
    boundary, body = build_multipart(
        fields={"content": message},
        file_field="file",
        file_path=attachment,
    )

    if dry_run:
        print(f"[dry-run] discord(webhook) -> {webhook_url} | attachment={attachment}")
        return

    req = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(req, timeout=20) as r:
        _ = r.read()
    print("discord sent -> webhook")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, help="shared/expense-report")
    p.add_argument("--period", choices=["daily", "weekly", "monthly", "yearly"], required=True)
    p.add_argument("--format", choices=["pdf", "html", "json"], default="html")
    p.add_argument("--dry-run", action="store_true")

    # Email options
    p.add_argument("--smtp-host")
    p.add_argument("--smtp-port", type=int, default=465)
    p.add_argument("--smtp-user")
    p.add_argument("--smtp-pass")
    p.add_argument("--from", dest="sender")
    p.add_argument("--to", help="comma-separated recipients")

    # Discord options (choose webhook OR bot token + channel)
    p.add_argument("--discord-webhook-url")
    p.add_argument("--discord-bot-token")
    p.add_argument("--discord-channel-id")
    p.add_argument("--discord-message", default="自动账单报告已生成，见附件。")

    args = p.parse_args()

    root = Path(args.root)
    report_dir = root / "reports" / args.period
    if not report_dir.exists():
        raise SystemExit(f"report dir not found: {report_dir}")

    target = latest_file(report_dir, f".{args.format}")
    if not target:
        raise SystemExit(f"no .{args.format} report found in {report_dir}")

    cfg_path = root / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    # email delivery
    recipients = [x.strip() for x in (args.to or ",".join(cfg.get("emailRecipients", []))).split(",") if x.strip()]
    smtp_host = args.smtp_host or cfg.get("smtpHost")
    smtp_user = args.smtp_user or cfg.get("smtpUser")
    smtp_pass = args.smtp_pass or cfg.get("smtpPass")
    sender = args.sender or cfg.get("smtpFrom") or smtp_user

    if recipients:
        required = [smtp_host, smtp_user, smtp_pass, sender]
        if not all(required):
            raise SystemExit("email recipients configured, but SMTP fields are incomplete")
        subject = f"Expense report ({args.period}) - {target.stem}"
        body = "自动账单报告已生成，附件见报告文件。\n\nThis email is sent by expense-report skill."
        send_email(
            sender=sender,
            password=smtp_pass,
            host=smtp_host,
            port=args.smtp_port,
            recipients=recipients,
            subject=subject,
            body=body,
            attachment=target,
            dry_run=args.dry_run,
        )

    # discord delivery
    webhook_url = args.discord_webhook_url or cfg.get("discordWebhookUrl")
    bot_token = args.discord_bot_token or cfg.get("discordBotToken")
    channel_id = args.discord_channel_id
    if not channel_id:
        t = cfg.get("discordTarget", "")
        if isinstance(t, str) and t.startswith("channel:"):
            channel_id = t.split(":", 1)[1]

    if webhook_url:
        send_discord_via_webhook(webhook_url, args.discord_message, target, dry_run=args.dry_run)
    elif bot_token and channel_id:
        send_discord_via_bot(bot_token, channel_id, args.discord_message, target, dry_run=args.dry_run)

    if not recipients and not webhook_url and not (bot_token and channel_id):
        if args.dry_run:
            print(f"[dry-run] no delivery target configured; validated report file only: {target}")
            return
        raise SystemExit("no delivery target configured: provide email recipients and/or discord target")


if __name__ == "__main__":
    main()
