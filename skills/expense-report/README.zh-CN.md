# Expense Report（支出统计）Skill

**版本号：** v1.0.2

[一页版说明（面向非技术用户）](./README.zh-CN.onepage.md)

一个面向 OpenClaw 的本地优先记账 Skill：支持自然语言记账、主动提醒、多币种记录、按日/周/月/年生成报告。

## 功能概览

- 自然语言记账
  - 例如：`午饭 32元`、`咖啡 USD 4.5`、`补录 3月1日 打车 45`
- 分类交互优化
  - 若落到“待分类”，会自动给出 3 个最可能分类建议
  - 你确认后可“学习关键词”，下次同类名目自动归类
- 币种识别优化
  - 采用“最长词优先”规则，避免 `美元` 被误判成 `元`
- 汇率拉取容灾
  - 主接口失败会自动切换备用接口；都失败则回退本地缓存汇率
  - 报告会输出 `fxMeta`（更新时间、来源、是否过期）
- 本地可编辑存储
  - 数据与规则都在本地文件，避免第三方 App 停更或数据丢失
- 多币种支持
  - 支持：CNY / USD / EUR / HKD / JPY / KRW / GBP / SGD
  - 报告统一折算为人民币（CNY）
- 定期报告
  - 日报 / 周报 / 月报 / 年报
  - 输出 JSON + HTML（可进一步渲染 PDF）

## 目录结构

```text
skills/expense-report/
├── SKILL.md
├── scripts/
│   └── ledger.py
└── references/
    ├── category-rules.md
    └── data-contract.md
```

运行时数据（本地）：

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

## 快速开始

在 workspace 根目录执行：

```bash
python3 skills/expense-report/scripts/ledger.py init --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py add --root shared/expense-report --text "补录 3月1日 午饭 32元"
python3 skills/expense-report/scripts/ledger.py rates --root shared/expense-report
python3 skills/expense-report/scripts/ledger.py report --root shared/expense-report --period daily
```

## 报告投递（可执行）

```bash
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --smtp-host smtp.qq.com \
  --smtp-port 465 \
  --smtp-user your_account@qq.com \
  --smtp-pass YOUR_SMTP授权码 \
  --from your_account@qq.com \
  --to a@example.com,b@example.com
```

建议先加 `--dry-run` 进行演练。`dry-run` 模式下允许不配置投递目标，仅验证报告文件可用性。

### Discord 投递

```bash
# Webhook 方式
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-webhook-url <WEBHOOK_URL>

# Bot Token + 频道 ID 方式
python3 skills/expense-report/scripts/deliver_report.py \
  --root shared/expense-report \
  --period daily \
  --format html \
  --discord-bot-token <BOT_TOKEN> \
  --discord-channel-id <CHANNEL_ID>
```

## 数据流程

1. 初始化配置
   - 设置提醒时间、总结时间、分类、报告投递目标（Discord / Email）
2. 输入记账
   - 支持当天记录和补录历史记录
3. 数据清洗
   - 解析金额、币种、日期、备注；分类不明确时标记“待分类”
4. 汇率换算
   - 在生成报告时拉取汇率并折算为 CNY
5. 报告生成
   - 按周期汇总总支出、分类占比、大额消费等
6. 报告投递
   - 可通过 OpenClaw 的 cron 与消息能力发送到 Discord / 邮箱

## 支持输入示例

- `晚饭 88`
- `地铁 4元`
- `补录 3月1日 打车 45`
- `昨天 咖啡 USD 4.5`
- `买书 39 欧元`

## 注意事项

- 汇率在出报告时计算（不是录入时）
- 删除或修改历史记录建议二次确认
- 对“待分类”条目可确认并学习关键词，后续自动归类：

```bash
# 确认最近一条待分类，并学习关键词（默认使用 note）
python3 skills/expense-report/scripts/ledger.py confirm-category \
  --root shared/expense-report \
  --category 生活日用 \
  --learn

# 指定 entry id，并手动指定学习关键词
python3 skills/expense-report/scripts/ledger.py confirm-category \
  --root shared/expense-report \
  --entry-id 20260303-abc12345 \
  --category 生活日用 \
  --learn \
  --keyword 宠物零食
```

- 所有核心数据默认本地存储，方便长期维护和迁移

## 打包 Skill

```bash
python3 /opt/homebrew/lib/node_modules/openclaw/skills/skill-creator/scripts/package_skill.py \
  skills/expense-report \
  skills/dist
```

输出文件：

- `skills/dist/expense-report.skill`


## v1.0.2 补丁更新

- 无金额输入返回友好提示（不再抛 traceback）。
- 修复 `.5` 小数写法解析（现在会正确记为 `0.5`）。
- 增加退款语义：`退款/报销/返现/退货` 或负数金额会归类到 `退款与冲减`。
- 修复小数输入场景下的备注清洗细节。

## v1.0.1 补丁更新

- `deliver_report.py` 新增 Discord 投递闭环（Webhook 或 Bot Token + Channel ID）。
- `confirm-category` 新增分类合法性校验（拒绝写入非法分类）。
- 优化 `$`（美元符号）识别逻辑，规避边界匹配问题。
- `report` 新增 `--date YYYY-MM-DD`，支持历史日期结算报表。
