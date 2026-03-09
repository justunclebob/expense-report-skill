#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

PERIOD_TITLES = {
    "weekly": "支出周报",
    "monthly": "支出月报",
    "yearly": "支出年报",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--period", choices=["weekly", "monthly", "yearly"], required=True)
    p.add_argument("--date")
    args = p.parse_args()

    script_dir = Path(__file__).resolve().parent
    ledger = script_dir / "ledger.py"

    cmd = [sys.executable, str(ledger), "report", "--root", args.root, "--period", args.period]
    if args.date:
        cmd += ["--date", args.date]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"ledger.py failed: {proc.returncode}")

    payload = json.loads(proc.stdout.strip())
    html_path = Path(payload["html"])
    json_path = Path(payload["json"])
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    expected_title = PERIOD_TITLES[args.period]
    if expected_title not in html:
        raise SystemExit(f"render validation failed: missing title {expected_title}")
    if "cat-svg" not in html and "分类占比" not in html:
        raise SystemExit("render validation failed: missing chart markup")

    print(json.dumps({
        "period": args.period,
        "title": expected_title,
        "json": str(json_path),
        "html": str(html_path),
        "validated": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
