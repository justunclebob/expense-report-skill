---
name: expense-report
description: Personal expense bookkeeping with proactive reminder setup, natural-language entry parsing, local-first storage, multi-currency normalization, and daily/weekly/monthly/yearly summaries. Use when the user wants to build or run a lightweight expense system in OpenClaw (especially with cron reminders, category management, backfill entries like “补录 3月1日…”, or PDF/JSON report generation and delivery to Discord/email).
---

# Expense Report

## Overview

Use this skill to run a local-first bookkeeping flow inside OpenClaw: remind user to记账, ingest short text entries, store normalized records locally, and generate periodic reports in CNY.

Canonical storage root (workspace-relative): `shared/expense-report/`

- `config.json` - user settings (reminders, categories, delivery targets)
- `entries.jsonl` - normalized expense rows (append-only)
- `reports/` - generated JSON/HTML/PDF reports

## Standard categories (default 15)

餐饮、居住、交通出行、通讯网络、生活日用、医疗健康、运动户外、服饰美妆、教育学习、娱乐休闲、人情往来、金融与保险、订阅会员、数码产品、退款与冲减

During setup, ask whether to keep all defaults or provide custom adds/removes.

## Workflow

### 1) Initial setup

Collect and save to `shared/expense-report/config.json`:

- timezone (default `Asia/Shanghai`)
- reminder times per day (e.g. `09:30, 14:00, 20:30`)
- daily summary time (e.g. `22:30`)
- weekly/monthly/yearly summary schedule (default week end / month end / year end)
- categories (default 15 + optional edits)
- discord report target (`channel:<id>`)
- email recipients (optional list)
- large-expense threshold CNY (default 500)

Then create cron jobs:

- Multiple daily reminder jobs (systemEvent)
- One daily summary job
- Weekly summary (`Sun 23:59`)
- Monthly summary (`last day 23:59`, implement as daily end-of-day job with month-end guard)
- Yearly summary (`Dec 31 23:59`, implement as daily end-of-day job with year-end guard)

Reminder text must read as a reminder and include context, e.g.:

- `记账提醒：这是你今天第2次消费记录提醒。随手发一句“午饭 32 元”就行。`

### 2) Entry ingestion (user-driven)

Accept short messages like:

- `午饭 32`
- `咖啡 USD 4.5`
- `补录 3月1日 打车 45`
- `昨天 晚饭 88 港币`

Rules:

- If no date provided: default today
- If “补录/昨天/前天/3月1日” present: resolve explicit date
- If currency omitted: default CNY
- Supported currencies: CNY, USD, EUR, HKD, JPY, KRW, GBP, SGD

Normalize and append to `entries.jsonl` with fields:

`id, occurredAt, recordedAt, amount, currency, amountCny(nullable), category, note, sourceText`

### 3) Cleaning and categorization

- Prefer explicit user category if present
- Else map keywords to default categories (see `references/category-rules.md`)
- If uncertain, keep `category="待分类"` and ask one follow-up question only when necessary

### 4) FX normalization

At report generation time (not entry time), convert all non-CNY to CNY using the latest available rates.

Use `scripts/ledger.py rates` to fetch/store rates into `shared/expense-report/fx-rates.json`.

### 5) Analysis and report generation

Use `scripts/ledger.py report` for `daily|weekly|monthly|yearly`:

- total spend (CNY)
- category totals + percentage
- top N expenses
- large-expense alerts (>= threshold)
- trend comparison vs previous period (if data exists)

Outputs:

- JSON: `shared/expense-report/reports/<period>/<stamp>.json`
- HTML: `shared/expense-report/reports/<period>/<stamp>.html`

### 6) PDF and delivery

Generate PDF from HTML (preferred) and deliver:

- Post PDF to Discord report channel
- Send via email if recipients configured

If PDF toolchain unavailable, send JSON + concise markdown summary and state fallback clearly.

## Commands / script usage

Run from workspace root (or any directory; scripts now resolve relative `--root` against the skill's workspace to avoid split data paths):

```bash
python3 skills/expense-report/scripts/ledger.py init --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py add --root shared/expense-report --text "补录 3月1日 午饭 32"
python3 skills/expense-report/scripts/ledger.py rates --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period daily
```

## Operational rules

- Keep everything local-first under workspace.
- Do not silently drop malformed entries; return a fix suggestion.
- For deletion/edits of historical entries, ask for confirmation.
- Never require third-party bookkeeping apps.
- Prefer minimal interaction friction: short messages should work.

## References

- Category mapping + keyword rules: `references/category-rules.md`
- Data model and file contract: `references/data-contract.md`
- Delivery details (SMTP + Discord): `references/delivery.md`
