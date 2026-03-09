#!/usr/bin/env python3
import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


def pick_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url: str, timeout: float = 5.0) -> None:
    end = time.time() + timeout
    last_err = None
    while time.time() < end:
        try:
            with urlopen(url, timeout=1.5) as r:
                if r.status == 200:
                    return
        except Exception as e:
            last_err = e
            time.sleep(0.2)
    raise SystemExit(f"http server not ready: {last_err}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--html", required=True)
    p.add_argument("--title", required=True, help="expected title text in html")
    args = p.parse_args()

    html_path = Path(args.html).resolve()
    if not html_path.exists():
        raise SystemExit(f"html not found: {html_path}")

    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    if args.title not in html_text:
        raise SystemExit(f"html validation failed: missing title {args.title}")
    if "cat-svg" not in html_text and "分类占比" not in html_text:
        raise SystemExit("html validation failed: missing chart markup")

    port = pick_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(html_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{port}/{html_path.name}"
    try:
        wait_http(url)
        print(json.dumps({
            "html": str(html_path),
            "url": url,
            "title": args.title,
            "serverPid": proc.pid,
            "validated": True,
        }, ensure_ascii=False))
    except Exception:
        proc.terminate()
        raise


if __name__ == "__main__":
    main()
