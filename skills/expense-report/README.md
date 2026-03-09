# Expense Report Skill

**Version:** v1.0.2

[简体中文文档](./README.zh-CN.md)

An OpenClaw skill for local-first personal expense tracking with proactive reminders, natural-language entry parsing, multi-currency support, and periodic reports — including visual weekly / monthly / yearly reports.

## Features

- **Natural-language bookkeeping**
  - Examples: `午饭 32元`, `咖啡 USD 4.5`, `补录 3月1日 打车 45`
- **Smarter classification UX**
  - If an entry is uncategorized (`待分类`), the tool returns top-3 category suggestions
  - You can confirm + learn category mapping so similar entries auto-classify next time
- **Safer currency parsing**
  - Longest-token-first detection avoids mis-parsing cases like `美元` being matched as `元`
- **FX reliability fallback**
  - Uses primary + backup FX APIs, and falls back to local cached rates if live fetch fails
  - Report output includes `fxMeta` (`updatedAt`, `source`, `stale`) for transparency
- **Local storage (editable, portable)**
  - All bookkeeping data stays in local files
- **Multi-currency support**
  - CNY / USD / EUR / HKD / JPY / KRW / GBP / SGD
  - Unified CNY output at report time
- **Periodic reporting**
  - Daily / Weekly / Monthly / Yearly
  - JSON + HTML output
- **Visual reporting (weekly / monthly / yearly)**
  - Unified Chinese visual layout
  - Includes summary block, category pie chart, trend dot chart, large-expense block, and Top 10 list
  - Daily report remains text-first by default (no screenshot required)

## Directory Structure

```text
skills/expense-report/
├── SKILL.md
├── scripts/
│   ├── ledger.py
│   ├── render_visual_report.py
│   └── capture_visual_report.py
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

## Code Entrypoints

### 1) Main bookkeeping entrypoint: `ledger.py`

Handles:
- init config
- add entries
- confirm category + learn keywords
- refresh FX rates
- generate JSON / HTML reports by period

Common commands:

```bash
python3 skills/expense-report/scripts/ledger.py init --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py add --root shared/expense-report --text "补录 3月1日 午饭 32元"
python3 skills/expense-report/scripts/ledger.py rates --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period daily
```

### 2) Visual report entrypoint: `render_visual_report.py`

Handles:
- calling `ledger.py report`
- validating the expected visual title (`支出周报 / 支出月报 / 支出年报`)
- validating chart markup exists
- failing fast instead of continuing with a broken render

Examples:

```bash
python3 skills/expense-report/scripts/render_visual_report.py --root shared/expense-report --period weekly
python3 skills/expense-report/scripts/render_visual_report.py --root shared/expense-report --period monthly
python3 skills/expense-report/scripts/render_visual_report.py --root shared/expense-report --period yearly
```

### 3) Capture-prep entrypoint: `capture_visual_report.py`

Handles:
- validating the target HTML title and chart markup
- starting a local HTTP server automatically
- returning a stable `http://127.0.0.1:<port>/...html` URL for screenshot capture

Example:

```bash
python3 skills/expense-report/scripts/capture_visual_report.py \
  --html shared/expense-report/reports/weekly/<stamp>.html \
  --title 支出周报
```

## Report Types and Presentation

### Daily report

- Intended for same-day summary
- Text-first by default
- No visual screenshot required

### Weekly / Monthly / Yearly reports

These are treated as **default visual reports**, not optional enhancements.

Unified template includes:
- Header summary
  - date range
  - total CNY
  - record count
  - period-over-period delta
  - comparison range
- Category share
  - pie chart
  - external straight-line labels
- Spending trend
  - Weekly: daily trend
  - Monthly: daily trend (X-axis shows day numbers only, with smaller labels)
  - Yearly: monthly trend
- Large expenses
  - threshold: `>500 CNY`
- Top 10 expense list

Comparison labels:
- Weekly: vs previous week
- Monthly: vs previous month
- Yearly: vs previous year

## Report Delivery

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

Tip: use `--dry-run` first. In dry-run mode, no delivery target is required; it only validates report-file readiness.

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

## Scheduled Behavior (Current)

- Daily report: sent daily, text summary only
- Weekly report: every Sunday, expected to send text summary + report path + image attachment
- Monthly report: sent only on month-end; silent skip otherwise
- Yearly report: sent only on year-end; silent skip otherwise

For weekly / monthly / yearly:
- Never screenshot `file://...` directly
- Always open the HTML through local HTTP first
- If page render fails, title mismatches, chart is missing, or screenshot fails: stop with error instead of degrading to text-only delivery

## Data Flow

1. Init config
   - set reminder times, summary times, categories, and delivery targets (Discord / Email)
2. Add entries
   - supports same-day and backfill records
3. Clean data
   - parse amount, currency, date, note; uncertain category becomes `待分类`
4. FX conversion
   - fetch rates at report time and convert to CNY
5. Generate reports
   - summarize totals, category share, trend, large expenses, etc.
6. Deliver reports
   - use OpenClaw cron + messaging to send to Discord / email

## Example Inputs

- `晚饭 88`
- `地铁 4元`
- `补录 3月1日 打车 45`
- `昨天 咖啡 USD 4.5`
- `买书 39 欧元`

## Notes

- Recommended to run from the `workspace-expense` root; if run elsewhere, scripts still resolve relative `--root` against the skill workspace
- FX conversion happens at report time, not entry time
- Require confirmation before destructive edits to historical records
- Uncategorized entries can be confirmed and learned for future auto-classification:

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

- All core data stays local for long-term portability and maintenance

## Packaging

```bash
python3 /opt/homebrew/lib/node_modules/openclaw/skills/skill-creator/scripts/package_skill.py \
  skills/expense-report \
  skills/dist
```

Output:
- `skills/dist/expense-report.skill`

## Version Notes

### v1.0.2
- Friendly validation message when amount is missing (no traceback)
- Correct decimal parsing for inputs like `.5` (now parsed as `0.5`)
- Refund semantics: `退款/报销/返现/退货` or negative amounts are classified as `退款与冲减`
- Minor note-cleaning fix for decimal-format inputs

### v1.0.1
- Added Discord delivery in `deliver_report.py` (webhook or bot token + channel id)
- Added category validation in `confirm-category` (rejects invalid categories)
- Hardened `$` (USD symbol) parsing logic to avoid boundary pitfalls
- Added `report --date YYYY-MM-DD` for historical settlement/report generation
