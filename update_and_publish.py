#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大安大甲聯合運用－原水費計價情境互動樹
半自動更新工具

日常流程：
1. 修改 Google Sheet「網頁樹狀資料」
2. 雙擊「更新並發布.bat」
3. 讀取 CSV、驗證資料、重建 index.html
4. 自動 git commit + push

若驗證失敗，會在發布前停止。
"""

from pathlib import Path
import csv
import io
import json
import subprocess
import sys
import urllib.request
from datetime import datetime

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
TEMPLATE_PATH = ROOT / "template.html"
OUTPUT_PATH = ROOT / "index.html"

REQUIRED_COLUMNS = [
    "node_id", "parent_id", "sort_order", "level", "node_type",
    "title", "status", "summary", "details", "source_tab", "source_key"
]
ALLOWED_TYPES = {"root", "group", "scenario", "topic"}
ALLOWED_STATUSES = {
    "", "已確認", "待正式會議", "待試運轉",
    "待營運驗證", "原則不發生", "操作背景"
}

def fail(message):
    print("\n[停止發布]")
    print(message)
    sys.exit(1)

def load_config():
    if not CONFIG_PATH.exists():
        fail("找不到 config.json")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    url = str(cfg.get("sheet_csv_url", "")).strip()
    if not url:
        fail("config.json 尚未設定 sheet_csv_url。")
    return cfg

def fetch_csv(url):
    print("1/4 讀取 Google Sheet 最新資料...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        fail(f"無法讀取 Google Sheet：{e}")
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    fail("CSV 編碼無法辨識。")

def parse_rows(text):
    reader = list(csv.reader(io.StringIO(text)))
    header_idx = None
    for i, row in enumerate(reader):
        normalized = [c.strip() for c in row]
        if "node_id" in normalized and "parent_id" in normalized:
            header_idx = i
            break
    if header_idx is None:
        fail("找不到 node_id / parent_id 欄位。請確認發布的是「網頁樹狀資料」。")

    headers = [c.strip() for c in reader[header_idx]]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        fail("缺少必要欄位：" + "、".join(missing))

    idx = {h: headers.index(h) for h in REQUIRED_COLUMNS}
    nodes = []

    for row_no, row in enumerate(reader[header_idx + 1:], start=header_idx + 2):
        def cell(name):
            j = idx[name]
            return row[j].strip() if j < len(row) else ""

        node_id = cell("node_id")
        if not node_id:
            continue

        try:
            sort_order = int(float(cell("sort_order")))
            level = int(float(cell("level")))
        except ValueError:
            fail(f"第 {row_no} 列 sort_order 或 level 不是有效數字。")

        nodes.append({
            "node_id": node_id,
            "parent_id": cell("parent_id") or None,
            "sort_order": sort_order,
            "level": level,
            "node_type": cell("node_type"),
            "title": cell("title"),
            "status": cell("status") or None,
            "summary": cell("summary") or None,
            "details": cell("details") or None,
            "source_tab": cell("source_tab") or None,
            "source_key": cell("source_key") or None,
        })
    return nodes

def validate(nodes):
    print("2/4 檢查樹狀資料結構...")
    if not nodes:
        fail("沒有讀到任何節點。")

    ids = set()
    for n in nodes:
        if n["node_id"] in ids:
            fail(f"node_id 重複：{n['node_id']}")
        ids.add(n["node_id"])
        if n["node_type"] not in ALLOWED_TYPES:
            fail(f"{n['node_id']} 的 node_type 不支援：{n['node_type']}")
        if (n["status"] or "") not in ALLOWED_STATUSES:
            fail(f"{n['node_id']} 的 status 不支援：{n['status']}")

    roots = [n for n in nodes if not n["parent_id"]]
    if len(roots) != 1:
        fail(f"根節點數量應為 1，目前為 {len(roots)}。")

    by_id = {n["node_id"]: n for n in nodes}
    sibling_orders = set()

    for n in nodes:
        if n["parent_id"]:
            if n["parent_id"] not in by_id:
                fail(f"{n['node_id']} 找不到父節點：{n['parent_id']}")
            parent = by_id[n["parent_id"]]
            if n["level"] != parent["level"] + 1:
                fail(
                    f"{n['node_id']} 的 level={n['level']}，"
                    f"但父節點 {n['parent_id']} 的 level={parent['level']}。"
                )

        key = (n["parent_id"], n["sort_order"])
        if key in sibling_orders:
            fail(
                f"同一父節點下 sort_order 重複："
                f"parent_id={n['parent_id']}, sort_order={n['sort_order']}"
            )
        sibling_orders.add(key)

    print(f"    通過：{len(nodes)} 個節點。")

def build_html(nodes):
    print("3/4 產生 index.html...")
    if not TEMPLATE_PATH.exists():
        fail("找不到 template.html")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    marker = "__NODES_JSON__"
    if marker not in template:
        fail("template.html 缺少資料插入標記。")
    payload = json.dumps(nodes, ensure_ascii=False, separators=(",", ":"))
    output = template.replace(marker, payload)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print("    已更新 index.html")

def run_git(args, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check
    )

def git_publish():
    print("4/4 發布到 GitHub...")
    try:
        inside = run_git(["rev-parse", "--is-inside-work-tree"], check=False)
    except FileNotFoundError:
        fail("找不到 Git。請先安裝 Git，或將 auto_git_push 改為 false。")

    if inside.returncode != 0:
        fail("目前資料夾不是 Git repository。請從 GitHub clone 本專案後再執行。")

    run_git(["add", "index.html"])
    diff = run_git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        print("    網頁內容沒有變更，不需要發布。")
        return

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit = run_git(["commit", "-m", f"Update web snapshot {stamp}"], check=False)
    if commit.returncode != 0:
        fail("Git commit 失敗：\n" + (commit.stderr or commit.stdout))

    push = run_git(["push"], check=False)
    if push.returncode != 0:
        fail("Git push 失敗：\n" + (push.stderr or push.stdout))

    print("    已推送。GitHub Pages 通常會在短時間內更新。")

def main():
    print("=" * 58)
    print("大安大甲聯合運用－原水費計價情境互動樹")
    print("更新並發布")
    print("=" * 58)

    cfg = load_config()
    text = fetch_csv(cfg["sheet_csv_url"])
    nodes = parse_rows(text)
    validate(nodes)
    build_html(nodes)

    if bool(cfg.get("auto_git_push", True)):
        git_publish()
    else:
        print("4/4 auto_git_push=false：只更新本機 index.html。")

    print("\n完成。")

if __name__ == "__main__":
    main()
