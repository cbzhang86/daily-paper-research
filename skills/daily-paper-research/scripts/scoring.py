#!/usr/bin/env python3
"""
PaperClaw-style 4-dimension scoring system
整合自 PaperClaw 项目的评分体系

评分公式：
final_score = base_score × 0.9 + impact_score × 0.1
base_score = (dim1 + dim2 + dim3 + dim4) / 4
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PaperScore:
    """论文四维评分结果"""

    # 四维基础评分 (1-10)
    engineering_application: float = 0.0
    architecture_innovation: float = 0.0
    theoretical_contribution: float = 0.0
    reliability: float = 0.0

    # 影响力评分
    date_citation_adjustment: float = 0.0

    # 最终评分
    final_score: float = 0.0

    # 元数据
    citations: int = 0
    age_months: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": {
                "engineering_application": round(self.engineering_application, 2),
                "architecture_innovation": round(self.architecture_innovation, 2),
                "theoretical_contribution": round(self.theoretical_contribution, 2),
                "reliability": round(self.reliability, 2),
            },
            "impact": {
                "date_citation_adjustment": round(self.date_citation_adjustment, 2),
                "citations": self.citations,
                "age_months": round(self.age_months, 1),
            },
            "final_score": round(self.final_score, 2),
        }


def calculate_date_citation_adjustment(
    citations: int, 
    age_months: float
) -> float:
    """
    计算 Date-Citation 影响力调整分数
    
    规则（来自 PaperClaw）：
    - ≤3个月新论文：+0.2
    - 3-24个月 + 引用≥50：+0.5
    - >24个月 + 引用≥200：+0.5
    - 引用密度≥10次/月：额外 +0.2
    
    Returns:
        float: 影响力调整分数 (0-1)
    """
    adjustment = 0.0
    
    # 新论文奖励
    if age_months <= 3:
        adjustment += 0.2
    
    # 中期论文引用奖励
    elif 3 < age_months <= 24 and citations >= 50:
        adjustment += 0.5
    
    # 长期高引用奖励
    elif age_months > 24 and citations >= 200:
        adjustment += 0.5
    
    # 引用密度奖励
    if age_months > 0:
        citation_density = citations / age_months
        if citation_density >= 10:
            adjustment += 0.2
    
    return min(adjustment, 1.0)


def score_engineering_application(
    title: str,
    abstract: str,
    venue: str = ""
) -> float:
    """
    工程应用价值评分 (1-10)
    
    评估标准：
    - 是否有明确的实际应用场景
    - 是否解决了工程问题
    - 是否有可复用的方法/工具
    """
    text = f"{title} {abstract} {venue}".lower()
    score = 5.0  # 基准分
    
    # 应用场景关键词
    application_keywords = [
        "application", "deployment", "production", "system",
        "framework", "toolkit", "pipeline", "platform",
        "应用", "部署", "系统", "平台", "框架", "工具"
    ]
    for kw in application_keywords:
        if kw in text:
            score += 0.5
    
    # 工程价值指标
    engineering_indicators = [
        "scalable", "efficient", "robust", "practical",
        "real-world", "industry", "production-ready",
        "可扩展", "高效", "鲁棒", "实用", "实际应用"
    ]
    for kw in engineering_indicators:
        if kw in text:
            score += 0.3
    
    # 开源/复用性
    if any(kw in text for kw in ["open source", "github", "code available", "开源"]):
        score += 1.0
    
    return min(max(score, 1.0), 10.0)


def score_architecture_innovation(
    title: str,
    abstract: str,
    venue: str = ""
) -> float:
    """
    架构创新评分 (1-10)
    
    评估标准：
    - 是否提出新的架构/模型
    - 是否有方法论创新
    - 是否改进现有方法
    """
    text = f"{title} {abstract} {venue}".lower()
    score = 5.0
    
    # 强创新词
    strong_innovation = [
        "novel", "new architecture", "new framework", "new method",
        "propose", "introduce", "pioneering", "breakthrough",
        "创新", "新架构", "新方法", "首次提出"
    ]
    for kw in strong_innovation:
        if kw in text:
            score += 0.8
    
    # 架构相关
    architecture_keywords = [
        "transformer", "attention", "encoder-decoder", "gan",
        "diffusion", "vae", "graph neural", "reinforcement",
        "注意力", "编码器", "生成对抗", "扩散模型"
    ]
    for kw in architecture_keywords:
        if kw in text:
            score += 0.4
    
    # 改进型工作
    improvement_keywords = [
        "improve", "enhance", "extend", "adapt", "modify",
        "改进", "增强", "扩展", "改进"
    ]
    for kw in improvement_keywords:
        if kw in text:
            score += 0.3
    
    return min(max(score, 1.0), 10.0)


def score_theoretical_contribution(
    title: str,
    abstract: str,
    venue: str = ""
) -> float:
    """
    理论贡献评分 (1-10)
    
    评估标准：
    - 是否有理论分析
    - 是否提出新定理/证明
    - 是否有收敛性/复杂度分析
    """
    text = f"{title} {abstract} {venue}".lower()
    score = 5.0
    
    # 理论贡献关键词
    theory_keywords = [
        "theorem", "proof", "convergence", "complexity",
        "bound", "guarantee", "theoretical", "analysis",
        "定理", "证明", "收敛", "复杂度", "理论"
    ]
    for kw in theory_keywords:
        if kw in text:
            score += 0.6
    
    # 数学严谨性
    math_keywords = [
        "formal", "rigorous", "mathematical", "derivation",
        "公式", "推导", "数学"
    ]
    for kw in math_keywords:
        if kw in text:
            score += 0.4
    
    # 实证为主的研究（降低理论评分）
    empirical_keywords = [
        "empirical", "experiment", "only", "no theory",
        "实证", "实验", "无理论"
    ]
    for kw in empirical_keywords:
        if kw in text:
            score -= 0.5
    
    return min(max(score, 1.0), 10.0)


def score_reliability(
    title: str,
    abstract: str,
    venue: str = "",
    citations: int = 0
) -> float:
    """
    可靠性评分 (1-10)
    
    评估标准：
    - 是否有充分的实验验证
    - 是否使用标准基准
    - 是否有消融实验
    - 引用数是否足够
    """
    text = f"{title} {abstract} {venue}".lower()
    score = 5.0
    
    # 实验充分性
    experiment_keywords = [
        "extensive", "comprehensive", "benchmark", "ablation",
        "baseline", "comparison", "reproducibility",
        "广泛", "全面", "基准", "消融", "对比"
    ]
    for kw in experiment_keywords:
        if kw in text:
            score += 0.5
    
    # 标准数据集
    benchmark_keywords = [
        "imagenet", "coco", "squad", "glue", "mnist",
        "cifar", "pascal", "标准数据集", "基准测试"
    ]
    for kw in benchmark_keywords:
        if kw in text:
            score += 0.6
    
    # 引用数加成
    if citations >= 100:
        score += 1.5
    elif citations >= 50:
        score += 1.0
    elif citations >= 20:
        score += 0.5
    
    # 可复现性
    if any(kw in text for kw in ["code", "data", "reproducible", "代码", "数据"]):
        score += 0.5
    
    return min(max(score, 1.0), 10.0)


def calculate_paper_score(
    title: str,
    abstract: str,
    venue: str = "",
    citations: int = 0,
    published_date: str | None = None
) -> PaperScore:
    """
    计算论文的完整四维评分
    
    Args:
        title: 论文标题
        abstract: 摘要
        venue: 发表场所
        citations: 引用数
        published_date: 发布日期 (YYYY-MM-DD)
    
    Returns:
        PaperScore: 完整评分结果
    """
    # 计算论文年龄
    age_months = 0.0
    if published_date:
        try:
            pub_date = datetime.strptime(published_date, "%Y-%m-%d")
            now = datetime.now()
            age_months = (now - pub_date).days / 30.0
        except (ValueError, TypeError):
            pass
    
    # 四维评分
    dim1 = score_engineering_application(title, abstract, venue)
    dim2 = score_architecture_innovation(title, abstract, venue)
    dim3 = score_theoretical_contribution(title, abstract, venue)
    dim4 = score_reliability(title, abstract, venue, citations)
    
    # 基础分
    base_score = (dim1 + dim2 + dim3 + dim4) / 4
    
    # 影响力调整
    impact_score = calculate_date_citation_adjustment(citations, age_months)
    
    # 最终评分
    final_score = base_score * 0.9 + impact_score * 10 * 0.1
    
    return PaperScore(
        engineering_application=dim1,
        architecture_innovation=dim2,
        theoretical_contribution=dim3,
        reliability=dim4,
        date_citation_adjustment=impact_score,
        final_score=final_score,
        citations=citations,
        age_months=age_months
    )


def score_papers_batch(
    papers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    批量为论文添加评分
    
    Args:
        papers: 论文列表
    
    Returns:
        list: 带评分的论文列表
    """
    scored_papers = []
    
    for p in papers:
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        venue = p.get("venue", "")
        citations = p.get("citations") or p.get("citation_count") or 0
        published_date = p.get("published_date") or p.get("year")
        
        # 处理年份格式
        if isinstance(published_date, int):
            published_date = f"{published_date}-01-01"
        
        score = calculate_paper_score(
            title=title,
            abstract=abstract,
            venue=venue,
            citations=citations if isinstance(citations, int) else 0,
            published_date=published_date if isinstance(published_date, str) else None
        )
        
        p["paper_score"] = score.to_dict()
        scored_papers.append(p)
    
    # 按评分排序
    scored_papers.sort(
        key=lambda x: x.get("paper_score", {}).get("final_score", 0),
        reverse=True
    )
    
    return scored_papers


# 领域定制评分维度示例
DOMAIN_RUBRICS = {
    "management": {
        "dimensions": [
            ("管理实践价值", "是否解决实际管理问题，有明确应用场景"),
            ("方法论严谨性", "研究设计是否科学，方法是否适当"),
            ("理论贡献度", "是否推进管理理论发展"),
            ("证据可靠性", "数据来源、样本量、分析方法是否可靠"),
        ]
    },
    "social_security": {
        "dimensions": [
            ("政策相关性", "是否涉及社会保障政策，有政策建议"),
            ("实证充分性", "是否使用可靠数据，方法是否恰当"),
            ("社会价值", "是否有助于改善民生福祉"),
            ("方法创新", "是否引入新的研究方法或视角"),
        ]
    },
    "ai_energy": {
        "dimensions": [
            ("工程应用", "是否有实际部署或应用场景"),
            ("架构创新", "是否提出新的模型架构或优化方法"),
            ("理论贡献", "是否有能效分析或理论保证"),
            ("实验可靠性", "是否有充分对比和消融实验"),
        ]
    }
}


def get_domain_rubric(domain: str) -> dict:
    """获取领域定制评分规则"""
    return DOMAIN_RUBRICS.get(domain, DOMAIN_RUBRICS["management"])


if __name__ == "__main__":
    # 测试示例
    test_paper = {
        "title": "Efficient Transformers for Long-Range Dependencies",
        "abstract": "We propose a novel attention mechanism that scales linearly with sequence length while maintaining strong performance on long-range dependencies. Extensive experiments on benchmark datasets show our method achieves state-of-the-art results.",
        "venue": "NeurIPS 2024",
        "citations": 45,
        "year": "2024-06-15"
    }
    
    score = calculate_paper_score(
        title=test_paper["title"],
        abstract=test_paper["abstract"],
        venue=test_paper["venue"],
        citations=test_paper["citations"],
        published_date=test_paper["year"]
    )
    
    import json
    print(json.dumps(score.to_dict(), indent=2, ensure_ascii=False))
