"""从 aiguanchao.com 的 RSS 取最新日报和 AI 类精选,写进 README.md 两对标记之间。

只用标准库,GitHub Actions 定时跑(见 .github/workflows/update.yml)。
取不到某个 RSS 时保留 README 里原来的那段,不清空。
"""
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

SITE = "https://aiguanchao.com"
BJ = timezone(timedelta(hours=8))
README = "README.md"


def fetch_items(path):
    req = urllib.request.Request(SITE + path, headers={"User-Agent": "aiguanchao-readme-bot (+https://github.com/AmbroseX/aiguanchao)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read()).findall("./channel/item")


def bj_time(item):
    raw = (item.findtext("pubDate") or "").replace("UTC", "GMT")
    try:
        return parsedate_to_datetime(raw).astimezone(BJ)
    except (TypeError, ValueError):
        return None


def one_line(text):
    return re.sub(r"\s+", " ", text or "").replace("|", "/").strip()


def daily_block(n=6):
    lines = []
    for it in fetch_items("/feed/daily.xml")[:n]:
        lines.append(f"- [{one_line(it.findtext('title'))}]({it.findtext('link')})")
    return "\n".join(lines)


# 只留 AI 和科技类:带这几个分类之一的才进(纯时政、社会、经济的不进,和"AI 观潮"对不上)
AI_CATEGORIES = {"模型", "产品", "技巧", "论文", "行业"}


def picks_block(n=20):
    # 精选 RSS 的 guid 就是本站单条页编号,链接指向本站总结页
    rows = ["| 时间(北京) | 新闻 | 来源 |", "|---|---|---|"]
    items = [it for it in fetch_items("/feed/featured.xml") if AI_CATEGORIES & {c.text for c in it.findall("category")}]
    for it in items[:n]:
        t = bj_time(it)
        when = t.strftime("%m-%d %H:%M") if t else ""
        url = f"{SITE}/items/{it.findtext('guid')}"
        rows.append(f"| {when} | [{one_line(it.findtext('title'))}]({url}) | {one_line(it.findtext('author'))} |")
    return "\n".join(rows)


def replace_between(text, name, body):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: f"{start}\n{body}\n{end}", text, flags=re.S)


def main():
    text = open(README, encoding="utf-8").read()
    old = text
    for name, build in (("daily", daily_block), ("picks", picks_block)):
        try:
            text = replace_between(text, name, build())
        except Exception as e:  # 网络或格式出错:这一段保留原样
            print(f"{name} 没更新: {e}", file=sys.stderr)
    if text != old:
        now = datetime.now(BJ).strftime("%Y-%m-%d %H:%M")
        text = replace_between(text, "updated", f"最后更新:{now}(北京时间)")
        open(README, "w", encoding="utf-8").write(text)
        print("README 已更新")
    else:
        print("没有变化")


if __name__ == "__main__":
    main()
