# Expense Report Skill

**Version:** v1.0.2

[简体中文文档](./README.zh-CN.md)

OpenClaw skill for local-first personal expense tracking with proactive reminders, natural-language entry parsing, multi-currency support, and periodic reports.

## Features

- **Natural-language bookkeeping**
  - Examples: `午饭 32元`, `咖啡 USD 4.5`, `补录 3月1日 打车 45`
- **Smarter classification UX**
  - If an entry is uncategorized (`待分类`), the tool returns top-3 category suggestions.
  - You can confirm + learn category mapping so similar entries auto-classify next time.
- **Safer currency parsing**
  - Longest-token-first detection avoids mis-parsing cases like `美元` being matched as `元`.
- **FX reliability fallback**
  - Uses primary + backup FX APIs, and falls back to local cached rates if live fetch fails.
  - Report output includes `fxMeta` (`updatedAt`, `source`, `stale`) for transparency.
- **Local storage (editable, portable)**
  - `shared/expense-report/config.json`
  - `shared/expense-report/entries.jsonl`
  - `shared/expense-report/reports/`
- **Periodic reporting**
  - Daily / Weekly / Monthly / Yearly
  - JSON + HTML output (PDF can be rendered from HTML)
- **Visual report template (Weekly/Monthly/Yearly)**
  - Unified Chinese layout for weekly, monthly, yearly reports
  - Includes summary block, pie chart with straight leader lines, large-expense block, and Top 10 list
  - Daily report stays text-first (no screenshot required)
- **Multi-currency support**
  - CNY, USD, EUR, HKD, JPY, KRW, GBP, SGD
  - Unified CNY output at report generation time

## Directory Structure

```text
expense-report/
├── SKILL.md
├── scripts/
│   └── ledger.py
└── references/
    ├── category-rules.md
    └── data-contract.md
```

Runtime data:

```text
shared/expense-report/
├── config.json
├── entries.jsonl
├── fx-rates.json
└── reports/
    ├── daily/
    ├── weekly/
    ├── monthly/
    └── yearly/
```

## Quick Start

From workspace root:

```bash
python3 skills/expense-report/scripts/ledger.py init --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py add --root shared/expense-report --text "补录 3月1日 午饭 32元"
python3 skills/expense-report/scripts/ledger.py rates --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period daily
```

## Visual Report (Weekly / Monthly / Yearly)

Current visual template is unified across weekly/monthly/yearly:

- Header summary: date range, total CNY, count, period-over-period delta, comparison range
- Category share: pie chart with external straight-line labels
- Large expenses: `>500 CNY`
- Top 10 expenses list

Period comparison labels:

- Weekly: vs previous week
- Monthly: vs previous month
- Yearly: vs previous year

Generation examples:

```bash
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period weekly
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period monthly
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period yearly
```

## Report Delivery (runnable)

Use OpenClaw cron + scripts to:

- send reminders multiple times per day,
- generate reports at configured times,
- deliver report files to Discord and email.

### Email (SMTP)

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

Tip: run with `--dry-run` first. In dry-run mode, no delivery target is required; it will validate report-file readiness only.

### Discord delivery

```bash
# via webhook
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-webhook-url <WEBHOOK_URL>

# via bot token + channel id
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-bot-token <BOT_TOKEN> \
  --discord-channel-id <CHANNEL_ID>
```

## Scheduled behavior (current)

- Daily report: send daily, text summary only (no screenshot)
- Weekly report: visual template + report path + screenshot
- Monthly report: only on month-end; silent skip on non-month-end days
- Yearly report: only on year-end; silent skip on non-year-end days

## Notes

- FX conversion happens at **report time** (not entry time).
- If category cannot be inferred, mark as `待分类` and return top-3 suggestions.
- Use `confirm-category --learn` to persist a keyword-category mapping for future auto-classification.
- For destructive edits (deleting historical entries), require explicit confirmation.

## Uncategorized confirmation & learning

```bash
# confirm latest uncategorized entry and learn keyword from note
python3 skills/expense-report/scripts/ledger.py confirm-category \
  --root shared/expense-report \
  --category 生活日用 \
  --learn

# or specify entry id
python3 skills/expense-report/scripts/ledger.py confirm-category \
  --root shared/expense-report \
  --entry-id 20260303-abc12345 \
  --category 生活日用 \
  --learn \
  --keyword 宠物零食
```

## Packaging

```bash
python3 /opt/homebrew/lib/node_modules/openclaw/skills/skill-creator/scripts/package_skill.py \
  skills/expense-report \
  skills/dist
```

Output: `skills/dist/expense-report.skill`


## v1.0.2 patch highlights

- Friendly validation message when amount is missing (no traceback).
- Correct decimal parsing for inputs like `.5` (now parsed as `0.5`).
- Refund semantics: `退款/报销/返现/退货` or negative amounts are classified as `退款与冲减`.
- Minor note-cleaning fix for decimal-format inputs.

## v1.0.1 patch highlights

- Added Discord delivery in `deliver_report.py` (webhook or bot token + channel id).
- Added category validation in `confirm-category` (rejects invalid categories).
- Hardened `$` (USD symbol) parsing logic to avoid boundary pitfalls.
- Added `report --date YYYY-MM-DD` for historical settlement/report generation.
