#!/usr/bin/env python3
"""
Semantic Scholar API 集成
用于获取论文引用数据，增强 Date-Citation 影响力评分

来源：整合自 evil-read-arxiv 项目
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Any, Optional

# API 配置
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,abstract,publicationDate,citationCount,influentialCitationCount,url,authors,externalIds"

# 速率限制
S2_RATE_LIMIT_WAIT = 30  # 429 错误后等待秒数
S2_REQUEST_INTERVAL = 3  # 请求间隔

# API Key（可选）
S2_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")


def search_semantic_scholar(
    query: str,
    limit: int = 20,
    year_range: Optional[tuple[int, int]] = None
) -> list[dict[str, Any]]:
    """
    搜索 Semantic Scholar
    
    Args:
        query: 搜索关键词
        limit: 返回结果数
        year_range: 年份范围 (start, end)
    
    Returns:
        list: 论文列表
    """
    params = {
        "query": query,
        "limit": limit,
        "fields": SEMANTIC_SCHOLAR_FIELDS
    }
    
    if year_range:
        start_year, end_year = year_range
        params["year"] = f"{start_year}-{end_year}"
    
    headers = {
        "User-Agent": "DailyPaperResearch/1.0"
    }
    
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    
    query_string = urllib.parse.urlencode(params)
    url = f"{SEMANTIC_SCHOLAR_API_URL}?{query_string}"
    
    print(f"[S2] 搜索: {query}")
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            papers = data.get("data", [])
            
            # 标准化数据
            for p in papers:
                p["source"] = "semantic_scholar"
                p["citations"] = p.get("citationCount", 0)
                p["influential_citations"] = p.get("influentialCitationCount", 0)
                
                # 提取 arXiv ID
                ext_ids = p.get("externalIds", {}) or {}
                p["arxiv_id"] = ext_ids.get("ArXiv", "")
                p["doi"] = ext_ids.get("DOI", "")
            
            print(f"[S2] 找到 {len(papers)} 篇论文")
            return papers
    
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"[S2] 速率限制，等待 {S2_RATE_LIMIT_WAIT} 秒...")
            time.sleep(S2_RATE_LIMIT_WAIT)
            return search_semantic_scholar(query, limit, year_range)
        print(f"[S2] HTTP 错误: {e.code}")
        return []
    except Exception as e:
        print(f"[S2] 错误: {e}")
        return []


def get_paper_by_arxiv_id(arxiv_id: str) -> Optional[dict[str, Any]]:
    """
    根据 arXiv ID 获取论文详情
    
    Args:
        arxiv_id: arXiv ID
    
    Returns:
        dict: 论文信息（含引用数）
    """
    # 清理 arXiv ID
    arxiv_id = re.sub(r'^ar[xX]iv[:\s]*', '', arxiv_id).strip()
    
    # 搜索
    papers = search_semantic_scholar(f"arXiv:{arxiv_id}", limit=1)
    
    if papers:
        paper = papers[0]
        # 验证 arXiv ID 匹配
        paper_arxiv = paper.get("arxiv_id", "")
        if paper_arxiv == arxiv_id:
            return paper
    
    return None


def get_paper_by_doi(doi: str) -> Optional[dict[str, Any]]:
    """
    根据 DOI 获取论文详情
    
    Args:
        doi: DOI
    
    Returns:
        dict: 论文信息
    """
    papers = search_semantic_scholar(f"DOI:{doi}", limit=1)
    return papers[0] if papers else None


def enrich_paper_with_citations(
    paper: dict[str, Any]
) -> dict[str, Any]:
    """
    为论文补充引用数据
    
    Args:
        paper: 论文信息
    
    Returns:
        dict: 补充后的论文信息
    """
    # 尝试多种方式获取
    result = None
    
    # 1. arXiv ID
    arxiv_id = paper.get("arxiv_id") or paper.get("arxivId")
    if arxiv_id:
        result = get_paper_by_arxiv_id(arxiv_id)
        if result:
            time.sleep(S2_REQUEST_INTERVAL)
    
    # 2. DOI
    if not result and paper.get("doi"):
        result = get_paper_by_doi(paper["doi"])
        if result:
            time.sleep(S2_REQUEST_INTERVAL)
    
    # 3. 标题搜索
    if not result and paper.get("title"):
        results = search_semantic_scholar(paper["title"], limit=5)
        for r in results:
            # 标题相似度匹配
            if titles_similar(paper["title"], r.get("title", "")):
                result = r
                break
        time.sleep(S2_REQUEST_INTERVAL)
    
    # 合并数据
    if result:
        paper["citations"] = result.get("citations", 0)
        paper["influential_citations"] = result.get("influential_citations", 0)
        paper["publication_date"] = result.get("publicationDate", "")
        paper["s2_url"] = result.get("url", "")
    
    return paper


def titles_similar(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    判断两个标题是否相似
    
    Args:
        title1: 标题1
        title2: 标题2
        threshold: 相似度阈值
    
    Returns:
        bool: 是否相似
    """
    # 标准化
    t1 = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', title1.lower())
    t2 = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', title2.lower())
    
    if not t1 or not t2:
        return False
    
    # 简单匹配：包含关系或高重叠
    if t1 == t2:
        return True
    if t1 in t2 or t2 in t1:
        return True
    
    # 计算重叠率
    shorter = min(len(t1), len(t2))
    longer = max(len(t1), len(t2))
    
    # 字符重叠
    common = sum(1 for c in t1 if c in t2)
    similarity = common / longer
    
    return similarity >= threshold


def batch_enrich_papers(
    papers: list[dict[str, Any]],
    max_papers: int = 50
) -> list[dict[str, Any]]:
    """
    批量为论文补充引用数据
    
    Args:
        papers: 论文列表
        max_papers: 最大处理数
    
    Returns:
        list: 补充后的论文列表
    """
    enriched = []
    
    for i, paper in enumerate(papers[:max_papers]):
        print(f"[S2] 处理 {i+1}/{min(len(papers), max_papers)}")
        
        enriched_paper = enrich_paper_with_citations(paper)
        enriched.append(enriched_paper)
    
    return enriched


def get_citation_trend(
    paper: dict[str, Any]
) -> dict[str, Any]:
    """
    计算引用趋势
    
    Args:
        paper: 论文信息（含 citations 和 publication_date）
    
    Returns:
        dict: 引用趋势数据
    """
    citations = paper.get("citations", 0)
    pub_date_str = paper.get("publication_date", "")
    
    if not pub_date_str:
        return {"trend": "unknown", "monthly_rate": 0}
    
    try:
        pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d")
        now = datetime.now()
        age_months = (now - pub_date).days / 30.0
        
        if age_months <= 0:
            return {"trend": "new", "monthly_rate": citations}
        
        monthly_rate = citations / age_months
        
        # 趋势判断
        if monthly_rate >= 10:
            trend = "hot"
        elif monthly_rate >= 5:
            trend = "rising"
        elif monthly_rate >= 1:
            trend = "stable"
        else:
            trend = "low"
        
        return {
            "trend": trend,
            "monthly_rate": round(monthly_rate, 2),
            "age_months": round(age_months, 1)
        }
    
    except (ValueError, TypeError):
        return {"trend": "unknown", "monthly_rate": 0}


if __name__ == "__main__":
    # 测试
    test_arxiv = "2301.07041"
    print(f"\n测试获取 arXiv:{test_arxiv}")
    paper = get_paper_by_arxiv_id(test_arxiv)
    
    if paper:
        print(json.dumps({
            "title": paper.get("title", "")[:80],
            "citations": paper.get("citations", 0),
            "influential_citations": paper.get("influential_citations", 0),
            "publication_date": paper.get("publicationDate", ""),
            "trend": get_citation_trend(paper)
        }, indent=2, ensure_ascii=False))
    else:
        print("未找到论文")
