# Delivery (Runnable)

## Email delivery

`deliver_report.py` uses SMTP over SSL and sends the latest report file from the selected period.

Example:

```bash
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --smtp-host smtp.qq.com \
  --smtp-port 465 \
  --smtp-user your_account@qq.com \
  --smtp-pass YOUR_SMTP_AUTH_CODE \
  --from your_account@qq.com \
  --to a@example.com,b@example.com
```

Use `--dry-run` first to verify attachment selection without actually sending.

## Discord delivery

Send the generated report file to a channel via OpenClaw message tool from agent workflow.
Target format: `channel:<id>`.


## Discord delivery (runnable)

Via bot token + channel id:

```bash
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-bot-token <BOT_TOKEN> \
  --discord-channel-id <CHANNEL_ID>
```

Via incoming webhook URL:

```bash
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-webhook-url <WEBHOOK_URL>
```

You can combine email + Discord in one run.
