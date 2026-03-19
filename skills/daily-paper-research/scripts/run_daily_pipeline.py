#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE = SKILL_DIR.parent.parent
TEMP_DIR = WORKSPACE / "temp"
PAPER_DISTILL_DIR = TEMP_DIR / "paper-distill-mcp"
PAPER_SCRAPER_DIR = WORKSPACE / "skills" / "paper-scraper"

if str(PAPER_DISTILL_DIR) not in sys.path:
    sys.path.insert(0, str(PAPER_DISTILL_DIR))


@dataclass
class NormalizedPaper:
    title: str
    authors: list[str]
    abstract: str
    year: int | None
    doi: str
    url: str
    pdf_url: str
    venue: str
    citations: int | None
    source: str
    topic_keys: list[str]
    topic_labels: list[str]
    language: str
    collection_type: str
    raw_keywords: list[str]
    institution: str = ""
    subject_classification: str = ""
    pages: str = ""
    fulltext_available: bool = False
    research_object: str = ""
    method_guess: str = ""
    policy_signal: str = ""
    data_signal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def guess_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    return "en"


def infer_collection_type(title: str, abstract: str, venue: str) -> str:
    text = f"{title} {abstract} {venue}".lower()
    if any(k in text for k in ["review", "综述", "systematic review", "meta-analysis", "元分析"]):
        return "review"
    if any(k in text for k in ["policy", "governance", "制度", "政策", "治理"]):
        return "policy"
    if any(k in text for k in ["empirical", "survey", "调查", "panel", "回归", "实证"]):
        return "empirical"
    return "general"


def derive_fine_fields(title: str, abstract: str, venue: str, institution: str = "") -> dict[str, str]:
    text = f"{title} {abstract} {venue} {institution}".lower()
    method_guess = ""
    for kw, label in [
        ("difference-in-differences", "DID/政策评估"),
        ("did", "DID/政策评估"),
        ("panel", "面板数据分析"),
        ("regression", "回归分析"),
        ("structural equation", "结构方程"),
        ("survey", "问卷/调查研究"),
        ("case study", "案例研究"),
        ("meta-analysis", "元分析"),
        ("回归", "回归分析"),
        ("面板", "面板数据分析"),
        ("问卷", "问卷/调查研究"),
        ("案例研究", "案例研究"),
        ("元分析", "元分析"),
        ("结构方程", "结构方程"),
    ]:
        if kw in text:
            method_guess = label
            break

    research_object = ""
    for kw, label in [
        ("elderly", "老年群体"), ("older adults", "老年群体"), ("aging", "老龄化群体"),
        ("adolescent", "青少年/未成年人"), ("minor", "未成年人"), ("children", "儿童群体"),
        ("farmer", "农民群体"), ("resident", "居民群体"), ("enterprise", "企业/组织"),
        ("老年", "老年群体"), ("老龄", "老龄化群体"), ("未成年人", "未成年人"),
        ("青少年", "青少年/未成年人"), ("儿童", "儿童群体"), ("农民", "农民群体"),
        ("居民", "居民群体"), ("企业", "企业/组织"), ("组织", "企业/组织"),
    ]:
        if kw in text:
            research_object = label
            break

    policy_signal = "高" if any(k in text for k in ["policy", "governance", "制度", "政策", "治理", "保障机制", "法律"]) else "中" if any(k in text for k in ["public", "service", "welfare", "养老服务"]) else "低"
    data_signal = "明确" if any(k in text for k in ["cgss", "cfps", "clhls", "panel", "survey", "问卷", "数据库", "样本"]) else "待识别"

    return {
        "research_object": research_object,
        "method_guess": method_guess,
        "policy_signal": policy_signal,
        "data_signal": data_signal,
    }


def summarize_paper(p: dict[str, Any]) -> dict[str, Any]:
    abstract = norm_text(p.get("abstract", ""))
    title = norm_text(p.get("title", ""))
    venue = norm_text(p.get("venue", ""))
    text = f"{title} {abstract} {venue}".lower()

    methods = []
    for kw in [
        "regression", "panel", "difference-in-differences", "did", "survey", "case study",
        "machine learning", "deep learning", "structural equation", "meta-analysis",
        "回归", "面板", "问卷", "案例研究", "机器学习", "深度学习", "结构方程", "元分析"
    ]:
        if kw in text:
            methods.append(kw)
    methods = sorted(set(methods))

    themes = []
    for kw in [
        "aging", "elderly", "social security", "welfare", "minor", "adolescent", "management",
        "老龄化", "养老", "社会保障", "福利", "未成年人", "青少年", "管理"
    ]:
        if kw in text:
            themes.append(kw)
    themes = sorted(set(themes))

    return {
        "title": title,
        "one_line": (abstract[:180] + "...") if len(abstract) > 180 else abstract,
        "methods": methods,
        "themes": themes,
        "collection_type": p.get("collection_type", "general"),
        "why_relevant": f"与{', '.join(p.get('topic_labels', []))}相关" if p.get("topic_labels") else "主题相关",
        "research_object": p.get("research_object", ""),
        "method_guess": p.get("method_guess", ""),
        "policy_signal": p.get("policy_signal", ""),
        "data_signal": p.get("data_signal", ""),
        "fulltext_available": p.get("fulltext_available", False),
    }


async def collect_international(topics: list[dict], top_n: int) -> list[dict[str, Any]]:
    from search.query_all import search_all

    results: list[dict[str, Any]] = []
    for topic in topics:
        query = " ".join(topic.get("keywords", []))
        papers = await search_all(query, top=top_n)
        for p in papers:
            p["_topic_key"] = topic["key"]
            p["_topic_label"] = topic["label"]
            p["_source_type"] = "international"
            results.append(p)
    return results


def collect_domestic(topics: list[dict], top_n: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    ncpssd_user = os.getenv("NCPSSD_USERNAME", "")
    ncpssd_pass = os.getenv("NCPSSD_PASSWORD", "")
    ncpssd_adapter = SKILL_DIR / "scripts" / "ncpssd_adapter.py"
    xueshushijie_adapter = SKILL_DIR / "scripts" / "xueshushijie_adapter.py"

    if xueshushijie_adapter.exists():
        for topic in topics:
            kws = topic.get("domestic_keywords", [])[:1]
            for kw in kws:
                try:
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(xueshushijie_adapter),
                            "--keyword", kw,
                            "--limit", str(min(4, top_n)),
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        timeout=240,
                    )
                    if completed.returncode == 0 and completed.stdout.strip():
                        rows = json.loads(completed.stdout)
                        for p in rows:
                            p["_topic_key"] = topic["key"]
                            p["_topic_label"] = topic["label"]
                            p["_source_type"] = "domestic"
                            results.append(p)
                except Exception:
                    pass

    if ncpssd_user and ncpssd_pass and ncpssd_adapter.exists():
        for topic in topics:
            kws = topic.get("domestic_keywords", [])[:1]
            for kw in kws:
                try:
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(ncpssd_adapter),
                            "--keyword", kw,
                            "--limit", str(min(3, top_n)),
                            "--username", ncpssd_user,
                            "--password", ncpssd_pass,
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        timeout=180,
                    )
                    if completed.returncode == 0 and completed.stdout.strip():
                        rows = json.loads(completed.stdout)
                        for p in rows:
                            p["_topic_key"] = topic["key"]
                            p["_topic_label"] = topic["label"]
                            p["_source_type"] = "domestic"
                            results.append(p)
                except Exception:
                    pass
    if results:
        return results

    # fallback placeholder when site runs are not available
    for topic in topics:
        for kw in topic.get("domestic_keywords", [])[:1]:
            results.append({
                "title": f"[待接入国内站点抓取] {kw}",
                "authors": [],
                "abstract": "国内真实源接口已预留；当前环境未跑通浏览器适配时先输出占位。",
                "year": None,
                "doi": "",
                "url": "",
                "pdf_url": "",
                "venue": "",
                "citation_count": 0,
                "source": "domestic-planned",
                "_topic_key": topic["key"],
                "_topic_label": topic["label"],
                "_source_type": "domestic-plan",
                "fulltext_available": False,
            })
    return results[: max(1, top_n // 2)]


def normalize_papers(raw_papers: list[dict[str, Any]]) -> list[NormalizedPaper]:
    merged: dict[str, NormalizedPaper] = {}
    for p in raw_papers:
        title = norm_text(p.get("title", ""))
        doi = norm_text(p.get("doi", "")).lower()
        key = doi or re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())
        if not key:
            continue

        authors = p.get("authors", []) if isinstance(p.get("authors", []), list) else []
        venue = norm_text(p.get("venue") or p.get("journal") or "")
        abstract = norm_text(p.get("abstract") or p.get("tldr") or "")
        source = norm_text(p.get("source", ""))
        url = norm_text(p.get("url", ""))
        pdf_url = norm_text(p.get("pdf_url") or p.get("open_access_url") or "")
        citations = p.get("citation_count", p.get("citations"))
        year = p.get("year") if isinstance(p.get("year"), int) else None

        fine_fields = derive_fine_fields(title, abstract, venue, p.get("institution", ""))
        if key not in merged:
            merged[key] = NormalizedPaper(
                title=title,
                authors=authors[:8],
                abstract=abstract,
                year=year,
                doi=doi,
                url=url,
                pdf_url=pdf_url,
                venue=venue,
                citations=citations if isinstance(citations, int) else None,
                source=source,
                topic_keys=[p.get("_topic_key", "")],
                topic_labels=[p.get("_topic_label", "")],
                language=guess_language(f"{title} {abstract}"),
                collection_type=infer_collection_type(title, abstract, venue),
                raw_keywords=p.get("keywords", []) if isinstance(p.get("keywords", []), list) else [],
                institution=norm_text(p.get("institution", "")),
                subject_classification=norm_text(p.get("subject_classification", "")),
                pages=norm_text(p.get("pages", "")),
                fulltext_available=bool(p.get("fulltext_available") or p.get("pdf_url") or p.get("download_url")),
                research_object=fine_fields["research_object"],
                method_guess=fine_fields["method_guess"],
                policy_signal=fine_fields["policy_signal"],
                data_signal=fine_fields["data_signal"],
            )
        else:
            item = merged[key]
            item.topic_keys = sorted(set(item.topic_keys + [p.get("_topic_key", "")]))
            item.topic_labels = sorted(set(item.topic_labels + [p.get("_topic_label", "")]))
            if not item.abstract and abstract:
                item.abstract = abstract
            if not item.pdf_url and pdf_url:
                item.pdf_url = pdf_url
            if not item.url and url:
                item.url = url
            if not item.venue and venue:
                item.venue = venue
            if not item.institution and p.get("institution"):
                item.institution = norm_text(p.get("institution", ""))
            if not item.subject_classification and p.get("subject_classification"):
                item.subject_classification = norm_text(p.get("subject_classification", ""))
            if not item.pages and p.get("pages"):
                item.pages = norm_text(p.get("pages", ""))
            item.fulltext_available = item.fulltext_available or bool(p.get("fulltext_available") or p.get("pdf_url") or p.get("download_url"))
            if (citations or 0) > (item.citations or 0):
                item.citations = citations if isinstance(citations, int) else item.citations
    return list(merged.values())


def build_analysis(papers: list[NormalizedPaper], report_top_n: int) -> dict[str, Any]:
    selected = sorted(
        papers,
        key=lambda x: ((x.citations or 0), x.year or 0, len(x.topic_keys)),
        reverse=True,
    )[:report_top_n]

    paper_summaries = [summarize_paper(p.to_dict()) for p in selected]
    topic_counter = Counter(label for p in papers for label in p.topic_labels if label)
    method_counter = Counter(m for s in paper_summaries for m in s["methods"])
    type_counter = Counter(p.collection_type for p in papers)

    gaps = []
    if topic_counter:
        low_topics = [k for k, v in topic_counter.items() if v <= 2]
        if low_topics:
            gaps.append(f"这些主题今日结果偏少，值得补充垂直来源：{', '.join(low_topics)}")
    if not any(p.language == "zh" for p in papers):
        gaps.append("国内来源真实抓取结果仍不足，需优先补齐 ncpssd / 知网 / 万方 接入。")
    if not any(p.collection_type == "policy" for p in papers):
        gaps.append("政策型论文占比偏低，可增加政策评估、制度设计、治理研究相关检索词。")

    fine_stats = {
        "fulltext_count": sum(1 for p in papers if p.fulltext_available),
        "policy_high_count": sum(1 for p in papers if p.policy_signal == "高"),
        "empirical_like_count": sum(1 for p in papers if p.method_guess),
    }

    writing_assets = {
        "candidate_review_papers": [p.title for p in selected if p.collection_type == "review"][:5],
        "candidate_policy_papers": [p.title for p in selected if p.collection_type == "policy"][:5],
        "candidate_empirical_papers": [p.title for p in selected if p.collection_type == "empirical" or p.method_guess][:5],
        "fulltext_candidates": [p.title for p in selected if p.fulltext_available][:8],
    }

    return {
        "selected_papers": [p.to_dict() for p in selected],
        "paper_summaries": paper_summaries,
        "topic_distribution": dict(topic_counter),
        "method_trends": dict(method_counter.most_common(12)),
        "type_distribution": dict(type_counter),
        "fine_stats": fine_stats,
        "research_gaps": gaps,
        "writing_assets": writing_assets,
    }


def render_report(date_str: str, papers: list[NormalizedPaper], analysis: dict[str, Any]) -> str:
    lines = [f"# 每日论文抓取分析日报 - {date_str}", ""]
    lines.append("## 一、今日概况")
    lines.append(f"- 抓取总量：{len(papers)}")
    lines.append(f"- 重点入选：{len(analysis['selected_papers'])}")
    lines.append(f"- 主题分布：{json.dumps(analysis['topic_distribution'], ensure_ascii=False)}")
    lines.append("")

    lines.append("## 二、今日重点论文")
    for idx, p in enumerate(analysis["selected_papers"], 1):
        year = p.get("year") or ""
        venue = p.get("venue") or "未知来源"
        lines.append(f"### {idx}. {p['title']}")
        lines.append(f"- 年份：{year}")
        lines.append(f"- 来源：{venue}")
        lines.append(f"- 主题：{', '.join(p.get('topic_labels', []))}")
        if p.get("institution"):
            lines.append(f"- 机构：{p['institution']}")
        if p.get("method_guess"):
            lines.append(f"- 方法判断：{p['method_guess']}")
        if p.get("research_object"):
            lines.append(f"- 研究对象：{p['research_object']}")
        lines.append(f"- 政策相关度：{p.get('policy_signal', '')}")
        lines.append(f"- 原文可达：{'是' if p.get('fulltext_available') else '否'}")
        if p.get("abstract"):
            abstract = p['abstract'][:240] + ('...' if len(p['abstract']) > 240 else '')
            lines.append(f"- 摘要：{abstract}")
        if p.get("url"):
            lines.append(f"- 链接：{p['url']}")
        if p.get("pdf_url"):
            lines.append(f"- 原文/下载：{p['pdf_url']}")
        lines.append("")

    lines.append("## 三、主题观察")
    for k, v in analysis["topic_distribution"].items():
        lines.append(f"- {k}：{v} 篇")
    lines.append("")

    lines.append("## 四、方法与趋势")
    if analysis["method_trends"]:
        for k, v in analysis["method_trends"].items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- 暂无明显方法关键词聚集。")
    lines.append("")

    lines.append("## 五、可跟进研究问题")
    for item in analysis["research_gaps"] or ["暂无明显空白提示，可继续积累样本后再做趋势判断。"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 六、后续写作可复用资产")
    for bucket, titles in analysis["writing_assets"].items():
        lines.append(f"### {bucket}")
        if titles:
            for t in titles:
                lines.append(f"- {t}")
        else:
            lines.append("- 暂无")
        lines.append("")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Daily paper collection-analysis-report pipeline")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--config", default=str(SKILL_DIR / "config" / "topics.json"))
    parser.add_argument("--output", default="")
    parser.add_argument("--limit-per-topic", type=int, default=12)
    parser.add_argument("--skip-domestic", action="store_true")
    parser.add_argument("--skip-international", action="store_true")
    args = parser.parse_args()

    cfg = load_json(Path(args.config))
    topics = cfg.get("topics", [])
    output_dir = Path(args.output) if args.output else (SKILL_DIR / "data" / "daily" / args.date)
    ensure_dir(output_dir)

    raw_collected: list[dict[str, Any]] = []
    if not args.skip_international:
        raw_collected.extend(await collect_international(topics, cfg.get("international_top_n", args.limit_per_topic)))
    if not args.skip_domestic:
        raw_collected.extend(collect_domestic(topics, cfg.get("domestic_top_n", 6)))

    normalized = normalize_papers(raw_collected)
    analysis = build_analysis(normalized, cfg.get("daily_report_top_n", 12))
    report = render_report(args.date, normalized, analysis)

    (output_dir / "collected.json").write_text(json.dumps(raw_collected, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "normalized.json").write_text(json.dumps([p.to_dict() for p in normalized], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps({
        "date": args.date,
        "raw_count": len(raw_collected),
        "normalized_count": len(normalized),
        "selected_count": len(analysis['selected_papers']),
        "generated_at": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(report)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
