#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = SKILL_DIR / "data" / "daily"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build topic-oriented research brief from accumulated daily outputs")
    parser.add_argument("--topic", required=True, help="topic keyword or label")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    folders = sorted([p for p in DAILY_DIR.iterdir() if p.is_dir()], reverse=True)[: args.days]
    topic = args.topic.lower()

    matched = []
    for folder in folders:
        analysis_file = folder / "analysis.json"
        if not analysis_file.exists():
            continue
        analysis = load_json(analysis_file)
        for paper in analysis.get("selected_papers", []):
            text = " ".join([
                paper.get("title", ""),
                paper.get("abstract", ""),
                " ".join(paper.get("topic_labels", [])),
                paper.get("venue", ""),
            ]).lower()
            if topic in text:
                matched.append({
                    "date": folder.name,
                    "title": paper.get("title", ""),
                    "venue": paper.get("venue", ""),
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract", ""),
                    "topic_labels": paper.get("topic_labels", []),
                    "url": paper.get("url", ""),
                })

    lines = [f"# 研究辅助简报 - {args.topic}", ""]
    lines.append(f"- 统计窗口：最近 {args.days} 天")
    lines.append(f"- 命中论文：{len(matched)}")
    lines.append("")

    lines.append("## 可直接用于后续写作的材料")
    for item in matched[:20]:
        lines.append(f"### {item['title']}")
        lines.append(f"- 日期：{item['date']}")
        lines.append(f"- 来源：{item['venue']}")
        lines.append(f"- 主题：{', '.join(item['topic_labels'])}")
        if item.get('abstract'):
            text = item['abstract'][:260] + ('...' if len(item['abstract']) > 260 else '')
            lines.append(f"- 摘要：{text}")
        if item.get('url'):
            lines.append(f"- 链接：{item['url']}")
        lines.append("")

    lines.append("## 交给 AutoResearchClaw / 深度研究阶段的建议输入")
    lines.append(f"- 研究主题候选：围绕“{args.topic}”在最近文献中的问题意识、方法路径、政策含义与研究空白")
    lines.append("- 建议先做：文献综述 → 研究空白提炼 → 研究问题分解 → 可验证假设")
    lines.append("- 如果做实证论文：优先抽取变量、样本、识别策略、政策背景")
    lines.append("- 如果做综述论文：优先抽取主题分支、方法谱系、共识与争议")

    out = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        out_path = SKILL_DIR / "data" / f"research-brief-{args.topic}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        out_path.write_text(out, encoding="utf-8")
        print(f"Saved to {out_path}")
    print(out)


if __name__ == "__main__":
    main()
