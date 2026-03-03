#!/usr/bin/env python3
import argparse
import json
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path


def latest_file(report_dir: Path, suffix: str):
    files = sorted(report_dir.glob(f"*{suffix}"))
    return files[-1] if files else None


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, help="shared/expense-report")
    p.add_argument("--period", choices=["daily", "weekly", "monthly", "yearly"], required=True)
    p.add_argument("--format", choices=["pdf", "html", "json"], default="html")
    p.add_argument("--dry-run", action="store_true")

    # SMTP options (or keep in env and pass from wrapper)
    p.add_argument("--smtp-host", required=True)
    p.add_argument("--smtp-port", type=int, default=465)
    p.add_argument("--smtp-user", required=True)
    p.add_argument("--smtp-pass", required=True)
    p.add_argument("--from", dest="sender", required=True)
    p.add_argument("--to", required=True, help="comma-separated recipients")

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

    recipients = [x.strip() for x in args.to.split(",") if x.strip()]
    subject = f"Expense report ({args.period}) - {target.stem}"
    body = "自动账单报告已生成，附件见报告文件。\n\nThis email is sent by expense-report skill."

    send_email(
        sender=args.sender,
        password=args.smtp_pass,
        host=args.smtp_host,
        port=args.smtp_port,
        recipients=recipients,
        subject=subject,
        body=body,
        attachment=target,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
