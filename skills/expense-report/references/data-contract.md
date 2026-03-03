# Data Contract

Storage root: `shared/expense-report/`

## config.json

```json
{
  "timezone": "Asia/Shanghai",
  "categories": ["餐饮", "居住"],
  "reminderTimes": ["09:30", "14:00", "20:30"],
  "dailySummaryTime": "22:30",
  "largeExpenseThresholdCny": 500,
  "discordTarget": "channel:1477494503920242709",
  "emailRecipients": []
}
```

## entries.jsonl

One JSON object per line:

```json
{
  "id": "20260303-8f3a1c2d",
  "occurredAt": "2026-03-03",
  "recordedAt": "2026-03-03T09:40:10+08:00",
  "amount": 45,
  "currency": "CNY",
  "amountCny": null,
  "category": "交通出行",
  "note": "打车",
  "sourceText": "打车 45"
}
```

`amountCny` is nullable at entry time; fill at report time with current FX.

## fx-rates.json

```json
{
  "base": "CNY",
  "updatedAt": "2026-03-03T10:00:00+08:00",
  "rates": {
    "CNY": 1,
    "USD": 0.139,
    "EUR": 0.128,
    "HKD": 1.087,
    "JPY": 20.4,
    "KRW": 191.7,
    "GBP": 0.109,
    "SGD": 0.185
  }
}
```

Interpretation: `1 CNY = rates[CUR] CUR`.
Conversion from CUR to CNY: `amount / rates[CUR]`.

## reports/

- `reports/daily/*.json|*.html`
- `reports/weekly/*.json|*.html`
- `reports/monthly/*.json|*.html`
- `reports/yearly/*.json|*.html`
