#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import uuid
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

SUPPORTED = {"CNY", "USD", "EUR", "HKD", "JPY", "KRW", "GBP", "SGD"}
DEFAULT_CATEGORIES = ["餐饮", "居住", "交通出行", "通讯网络", "生活日用", "医疗健康", "运动户外", "服饰美妆", "教育学习", "娱乐休闲", "人情往来", "金融与保险", "订阅会员", "数码产品"]
ALIASES = {
    "元": "CNY", "块": "CNY", "人民币": "CNY", "rmb": "CNY", "cny": "CNY",
    "美元": "USD", "usd": "USD", "$": "USD",
    "欧元": "EUR", "eur": "EUR",
    "港币": "HKD", "hkd": "HKD",
    "日元": "JPY", "jpy": "JPY",
    "韩元": "KRW", "krw": "KRW",
    "英镑": "GBP", "gbp": "GBP",
    "新加坡元": "SGD", "sgd": "SGD",
}

CATEGORY_KEYWORDS = {
    "餐饮": ["吃饭", "午饭", "午餐", "晚饭", "早餐", "咖啡", "奶茶", "外卖"],
    "居住": ["房租", "水电", "燃气", "物业", "家政"],
    "交通出行": ["打车", "地铁", "公交", "高铁", "机票", "加油", "停车"],
    "通讯网络": ["话费", "流量", "宽带", "手机套餐"],
    "生活日用": ["日用品", "清洁", "超市", "家居"],
    "医疗健康": ["医院", "药", "体检", "牙科"],
    "运动户外": ["健身", "跑步", "球类", "户外装备"],
    "服饰美妆": ["衣服", "鞋", "护肤", "化妆"],
    "教育学习": ["课程", "培训", "书", "考试"],
    "娱乐休闲": ["电影", "游戏", "演出", "旅游门票"],
    "人情往来": ["红包", "礼物", "请客", "礼金"],
    "金融与保险": ["保费", "手续费", "利息"],
    "订阅会员": ["会员", "年费", "订阅", "saas"],
    "数码产品": ["手机", "电脑", "配件", "电子产品"],
}

SUGGESTION_HINTS = {
    "生活日用": ["宠物", "猫", "狗", "猫砂", "猫粮", "狗粮", "纸巾", "洗衣液", "牙膏"],
    "医疗健康": ["疫苗", "挂号", "看病", "诊疗", "体检", "药"],
    "交通出行": ["通勤", "路费", "车费"],
}


def ensure(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(exist_ok=True)
    for p in ["daily", "weekly", "monthly", "yearly"]:
        (root / "reports" / p).mkdir(parents=True, exist_ok=True)


def load_entries(root: Path):
    p = root / "entries.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def load_config(root: Path):
    p = root / "config.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_entry(root: Path, item):
    p = root / "entries.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def save_entries(root: Path, entries):
    p = root / "entries.jsonl"
    lines = [json.dumps(x, ensure_ascii=False) for x in entries]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_custom_keywords(root: Path):
    p = root / "custom-keywords.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_custom_keywords(root: Path, mapping):
    p = root / "custom-keywords.json"
    p.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_date(text: str, today: dt.date):
    if "昨天" in text:
        return today - dt.timedelta(days=1)
    if "前天" in text:
        return today - dt.timedelta(days=2)
    m_full = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m_full:
        return dt.date(int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3)))
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        return dt.date(today.year, int(m.group(1)), int(m.group(2)))
    return today


def parse_amount_currency(text: str):
    nums = re.findall(r"(-?\d+(?:\.\d+)?)", text)
    if not nums:
        raise ValueError("未识别到金额")
    amount = float(nums[-1])

    cur = "CNY"
    lower = text.lower()

    # Handle '$' explicitly: word-boundary is unreliable for symbol tokens.
    if re.search(r"(?:^|\s)\$\s*-?\d| -?\d+(?:\.\d+)?\s*\$", text):
        cur = "USD"
    else:
        # longest token first to avoid "美元" being matched by "元"
        for k in sorted(ALIASES.keys(), key=len, reverse=True):
            v = ALIASES[k]
            if k == "$":
                continue
            if re.fullmatch(r"[a-zA-Z]+", k):
                if re.search(rf"\b{re.escape(k.lower())}\b", lower):
                    cur = v
                    break
            else:
                if k in text:
                    cur = v
                    break

    if cur not in SUPPORTED:
        raise ValueError(f"不支持币种: {cur}")
    return amount, cur


def parse_note(text: str):
    t = re.sub(r"补录", "", text, flags=re.IGNORECASE)
    t = re.sub(r"\d{4}-\d{1,2}-\d{1,2}", "", t)
    t = re.sub(r"\d{1,2}月\d{1,2}日", "", t)
    t = re.sub(r"昨天|前天", "", t)
    t = re.sub(r"-?\d+(?:\.\d+)?", "", t)
    # remove currency words/symbols case-insensitively
    t = re.sub(r"\b(cny|rmb|usd|eur|hkd|jpy|krw|gbp|sgd)\b", "", t, flags=re.IGNORECASE)
    for k in sorted(ALIASES.keys(), key=len, reverse=True):
        t = re.sub(re.escape(k), "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "消费"


def infer_category(text: str, note: str, custom_keywords=None):
    hay = f"{text} {note}".lower()

    # user-learned keywords have highest priority
    custom_keywords = custom_keywords or {}
    for cat, kws in custom_keywords.items():
        for kw in kws:
            if kw and kw.lower() in hay:
                return cat

    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in hay:
                return cat
    return "待分类"


def suggest_categories(text: str, note: str, topn: int = 3):
    # lightweight heuristic ranking for fallback suggestions
    # score by partial token overlap with built-in keywords
    hay = f"{text} {note}".lower()
    scores = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in kws:
            k = kw.lower()
            if not k:
                continue
            if k in hay or hay in k:
                score += max(2, len(k))
            else:
                # character-level fuzzy overlap for Chinese short words
                overlap = len(set(k) & set(hay))
                score += overlap

        # extra domain hints for better suggestions (e.g. pet-related items)
        for h in SUGGESTION_HINTS.get(cat, []):
            if h.lower() in hay:
                score += 8

        scores.append((cat, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    # always return 3 options for better UX
    return [c for c, _ in scores[:topn]]


def cmd_init(args):
    root = Path(args.root)
    ensure(root)
    cfg = root / "config.json"
    if not cfg.exists():
        cfg.write_text(json.dumps({
            "timezone": "Asia/Shanghai",
            "categories": DEFAULT_CATEGORIES,
            "reminderTimes": ["09:30", "14:00", "20:30"],
            "dailySummaryTime": "22:30",
            "largeExpenseThresholdCny": 500,
            "discordTarget": "",
            "emailRecipients": []
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(root))


def cmd_add(args):
    root = Path(args.root)
    ensure(root)
    today = dt.date.today()
    text = args.text.strip()
    d = parse_date(text, today)
    amount, cur = parse_amount_currency(text)
    note = parse_note(text)
    custom_keywords = load_custom_keywords(root)
    category = infer_category(text, note, custom_keywords=custom_keywords)
    item = {
        "id": f"{d.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        "occurredAt": d.isoformat(),
        "recordedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "amount": amount,
        "currency": cur,
        "amountCny": None,
        "category": category,
        "note": note,
        "sourceText": text,
    }
    save_entry(root, item)

    out = {"entry": item}
    if category == "待分类":
        options = suggest_categories(text, note, topn=3)
        out["needsCategoryConfirmation"] = True
        out["categorySuggestions"] = options
        out["followUpPrompt"] = (
            "这笔消费暂时是‘待分类’，你想把它归到哪一类？"
            + f" 可选建议：{', '.join(options)}"
        )
    print(json.dumps(out, ensure_ascii=False))


def _valid_categories(root: Path):
    cfg = load_config(root)
    cats = cfg.get("categories") if isinstance(cfg, dict) else None
    if isinstance(cats, list) and cats:
        return [str(x).strip() for x in cats if str(x).strip()]
    return DEFAULT_CATEGORIES


def _parse_anchor_date(value: str | None):
    if not value:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise SystemExit("--date 格式错误，请使用 YYYY-MM-DD")


def cmd_confirm_category(args):
    root = Path(args.root)
    ensure(root)

    entries = load_entries(root)
    if not entries:
        raise SystemExit("no entries found")

    target = None
    if args.entry_id:
        for e in entries:
            if e.get("id") == args.entry_id:
                target = e
                break
        if target is None:
            raise SystemExit(f"entry not found: {args.entry_id}")
    else:
        for e in reversed(entries):
            if e.get("category") == "待分类":
                target = e
                break
        if target is None:
            raise SystemExit("no uncategorized entries found")

    valid_categories = _valid_categories(root)
    if args.category not in valid_categories:
        raise SystemExit(f"非法分类: {args.category}. 可选: {', '.join(valid_categories)}")

    target["category"] = args.category
    save_entries(root, entries)

    learned = None
    if args.learn:
        keyword = (args.keyword or target.get("note") or "").strip()
        if keyword:
            mapping = load_custom_keywords(root)
            bucket = mapping.get(args.category, [])
            if keyword not in bucket:
                bucket.append(keyword)
                mapping[args.category] = bucket
                save_custom_keywords(root, mapping)
            learned = keyword

    out = {"updatedEntryId": target.get("id"), "category": args.category}
    if learned:
        out["learnedKeyword"] = learned
    print(json.dumps(out, ensure_ascii=False))


def cmd_rates(args):
    root = Path(args.root)
    ensure(root)

    sources = [
        "https://open.er-api.com/v6/latest/CNY",           # primary
        "https://api.exchangerate-api.com/v4/latest/CNY",  # backup
    ]

    last_err = None
    data = None
    used_source = None
    for url in sources:
        try:
            with urlopen(url, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict) and isinstance(data.get("rates"), dict):
                used_source = url
                break
        except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as e:
            last_err = str(e)

    if not data or "rates" not in data:
        # fallback to cached fx-rates.json
        cache_path = root / "fx-rates.json"
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached["stale"] = True
            cached["staleReason"] = f"live fx fetch failed: {last_err or 'unknown error'}"
            print(json.dumps(cached, ensure_ascii=False))
            return
        raise SystemExit(f"汇率拉取失败且无本地缓存可回退: {last_err or 'unknown error'}")

    rates = {k: data["rates"][k] for k in SUPPORTED if k in data.get("rates", {})}
    rates["CNY"] = 1.0
    obj = {
        "base": "CNY",
        "updatedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": used_source,
        "rates": rates,
    }
    (root / "fx-rates.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(obj, ensure_ascii=False))


def period_range(period: str, today: dt.date):
    if period == "daily":
        return today, today
    if period == "weekly":
        start = today - dt.timedelta(days=today.weekday())
        return start, start + dt.timedelta(days=6)
    if period == "monthly":
        start = today.replace(day=1)
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1, day=1)
        else:
            nxt = start.replace(month=start.month + 1, day=1)
        return start, nxt - dt.timedelta(days=1)
    if period == "yearly":
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
        return start, end
    raise ValueError("invalid period")


def previous_period_range(period: str, start: dt.date, end: dt.date):
    if period == "daily":
        prev = start - dt.timedelta(days=1)
        return prev, prev
    if period == "weekly":
        return start - dt.timedelta(days=7), end - dt.timedelta(days=7)
    if period == "monthly":
        prev_end = start - dt.timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return prev_start, prev_end
    if period == "yearly":
        return start.replace(year=start.year - 1), end.replace(year=end.year - 1)
    raise ValueError("invalid period")


def to_cny(amount, cur, rates):
    if cur == "CNY":
        return amount
    rate = rates.get(cur)
    if not rate:
        return None
    return amount / rate


def _rows_in_range(entries, start: dt.date, end: dt.date, rates):
    rows = []
    for e in entries:
        d = dt.date.fromisoformat(e["occurredAt"])
        if start <= d <= end:
            cny = to_cny(float(e["amount"]), e["currency"], rates)
            rows.append({**e, "amountCny": cny})
    return rows


def cmd_report(args):
    root = Path(args.root)
    ensure(root)
    cfg = load_config(root)
    threshold = float(cfg.get("largeExpenseThresholdCny", 500))

    entries = load_entries(root)
    anchor = _parse_anchor_date(args.date)
    start, end = period_range(args.period, anchor)

    rates_obj = {}
    rp = root / "fx-rates.json"
    if rp.exists():
        rates_obj = json.loads(rp.read_text(encoding="utf-8"))
    rates = rates_obj.get("rates", {"CNY": 1.0})

    rows = _rows_in_range(entries, start, end, rates)
    total = sum(x["amountCny"] for x in rows if isinstance(x["amountCny"], (int, float)))

    by_cat = {}
    for r in rows:
        k = r.get("category", "待分类")
        by_cat[k] = by_cat.get(k, 0) + (r["amountCny"] or 0)

    large = [
        x for x in sorted(rows, key=lambda x: x.get("amountCny") or 0, reverse=True)
        if (x.get("amountCny") or 0) >= threshold
    ]

    prev_start, prev_end = previous_period_range(args.period, start, end)
    prev_rows = _rows_in_range(entries, prev_start, prev_end, rates)
    prev_total = sum(x["amountCny"] for x in prev_rows if isinstance(x["amountCny"], (int, float)))
    delta = total - prev_total
    delta_pct = None if prev_total == 0 else (delta / prev_total * 100)

    out = {
        "period": args.period,
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "generatedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "fxMeta": {
            "updatedAt": rates_obj.get("updatedAt"),
            "source": rates_obj.get("source"),
            "stale": bool(rates_obj.get("stale", False)),
            "staleReason": rates_obj.get("staleReason"),
        },
        "totalCny": round(total, 2),
        "count": len(rows),
        "byCategory": {k: round(v, 2) for k, v in sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)},
        "topExpenses": sorted(rows, key=lambda x: x.get("amountCny") or 0, reverse=True)[:10],
        "largeExpenseThresholdCny": threshold,
        "largeExpenses": large,
        "trendVsPrevious": {
            "previousRange": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
            "previousTotalCny": round(prev_total, 2),
            "deltaCny": round(delta, 2),
            "deltaPct": None if delta_pct is None else round(delta_pct, 2),
        },
    }

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = root / "reports" / args.period / stamp
    (base.with_suffix(".json")).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"<h1>Expense Report ({args.period})</h1>",
        f"<p>Range: {start} ~ {end}</p>",
        f"<p>Total (CNY): <b>{out['totalCny']}</b> | Count: {out['count']}</p>",
        f"<p>Trend vs previous: {out['trendVsPrevious']['deltaCny']:+.2f} CNY"
        + ("" if out['trendVsPrevious']['deltaPct'] is None else f" ({out['trendVsPrevious']['deltaPct']:+.2f}%)")
        + "</p>",
        "<h2>By Category</h2>",
        "<ul>",
    ]
    for k, v in out["byCategory"].items():
        pct = (v / total * 100) if total > 0 else 0
        lines.append(f"<li>{k}: {v:.2f} ({pct:.1f}%)</li>")
    lines.extend(["</ul>", "<h2>Large Expenses</h2>", "<ul>"])
    if large:
        for x in large:
            lines.append(f"<li>{x['occurredAt']} | {x['note']} | {x['amount']} {x['currency']} (~{(x.get('amountCny') or 0):.2f} CNY)</li>")
    else:
        lines.append("<li>None</li>")
    lines.extend(["</ul>", "<h2>Top Expenses</h2>", "<ol>"])
    for x in out["topExpenses"]:
        lines.append(f"<li>{x['occurredAt']} | {x['note']} | {x['amount']} {x['currency']} (~{(x.get('amountCny') or 0):.2f} CNY)</li>")
    lines.append("</ol>")
    html = "\n".join(lines)
    (base.with_suffix(".html")).write_text(html, encoding="utf-8")
    print(json.dumps({"json": str(base.with_suffix('.json')), "html": str(base.with_suffix('.html'))}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--root", required=True)
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add")
    p_add.add_argument("--root", required=True)
    p_add.add_argument("--text", required=True)
    p_add.set_defaults(func=cmd_add)

    p_confirm = sub.add_parser("confirm-category")
    p_confirm.add_argument("--root", required=True)
    p_confirm.add_argument("--category", required=True)
    p_confirm.add_argument("--entry-id")
    p_confirm.add_argument("--learn", action="store_true", help="learn keyword for future auto classification")
    p_confirm.add_argument("--keyword", help="custom keyword to learn (default: note text)")
    p_confirm.set_defaults(func=cmd_confirm_category)

    p_rates = sub.add_parser("rates")
    p_rates.add_argument("--root", required=True)
    p_rates.set_defaults(func=cmd_rates)

    p_report = sub.add_parser("report")
    p_report.add_argument("--root", required=True)
    p_report.add_argument("--period", choices=["daily", "weekly", "monthly", "yearly"], required=True)
    p_report.add_argument("--date", help="anchor date for report period (YYYY-MM-DD), default=today")
    p_report.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
