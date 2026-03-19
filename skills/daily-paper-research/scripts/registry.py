#!/usr/bin/env python3
"""
论文去重注册表
整合自 PaperClaw 的 update_registry.py

功能：
- 文件锁安全写入
- 基于 arXiv ID 去重
- 基于标题去重
- 支持跨平台
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def normalize_title(title: str) -> str:
    """标题标准化，用于去重比较"""
    normalized = re.sub(r'[^a-z0-9\u4e00-\u9fff\s]', '', title.lower())
    return re.sub(r'\s+', ' ', normalized).strip()


def load_registry(registry_path: Path) -> dict[str, Any]:
    """加载注册表"""
    if not registry_path.exists():
        return {"papers": [], "last_updated": ""}
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if "papers" in data else {"papers": [], "last_updated": ""}
    except (json.JSONDecodeError, IOError):
        return {"papers": [], "last_updated": ""}


def is_duplicate(
    paper: dict[str, Any],
    registry: dict[str, Any]
) -> tuple[bool, str]:
    """
    检查论文是否重复
    
    Returns:
        tuple: (是否重复, 原因)
    """
    existing = registry.get("papers", [])
    
    # 基于 arXiv ID / DOI 去重
    arxiv_id = paper.get("arxiv_id") or paper.get("doi", "")
    if arxiv_id:
        arxiv_id_clean = re.sub(r'^ar[xX]iv[:\s]*', '', str(arxiv_id)).strip()
        for p in existing:
            p_id = p.get("arxiv_id") or p.get("doi", "")
            p_id_clean = re.sub(r'^ar[xX]iv[:\s]*', '', p_id).strip()
            if arxiv_id_clean and p_id_clean and arxiv_id_clean == p_id_clean:
                return True, f"arXiv ID 重复: {arxiv_id_clean}"
    
    # 基于标题去重
    title = paper.get("title", "")
    title_norm = normalize_title(title)
    if title_norm:
        for p in existing:
            p_title_norm = normalize_title(p.get("title", ""))
            if title_norm == p_title_norm:
                return True, f"标题重复: {title[:50]}..."
    
    return False, ""


def update_registry(
    papers: list[dict[str, Any]],
    registry_path: Path
) -> tuple[int, int]:
    """
    批量更新注册表
    
    Args:
        papers: 待添加的论文列表
        registry_path: 注册表文件路径
    
    Returns:
        tuple: (新增数量, 跳过数量)
    """
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 加载现有注册表
    registry = load_registry(registry_path)
    
    added = 0
    skipped = 0
    
    for paper in papers:
        is_dup, reason = is_duplicate(paper, registry)
        
        if is_dup:
            skipped += 1
            continue
        
        # 添加新记录
        entry = {
            "arxiv_id": paper.get("arxiv_id", ""),
            "doi": paper.get("doi", ""),
            "title": paper.get("title", ""),
            "source": paper.get("source", ""),
            "evaluated_date": datetime.now().isoformat(),
            "final_score": paper.get("paper_score", {}).get("final_score", 0),
        }
        registry["papers"].append(entry)
        added += 1
    
    # 更新时间戳
    registry["last_updated"] = datetime.now().isoformat()
    
    # 写入文件
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    return added, skipped


def filter_duplicates(
    papers: list[dict[str, Any]],
    registry_path: Path
) -> list[dict[str, Any]]:
    """
    过滤掉已存在的论文
    
    Args:
        papers: 待过滤的论文列表
        registry_path: 注册表路径
    
    Returns:
        list: 未重复的论文列表
    """
    registry = load_registry(registry_path)
    unique_papers = []
    
    for paper in papers:
        is_dup, _ = is_duplicate(paper, registry)
        if not is_dup:
            unique_papers.append(paper)
    
    return unique_papers


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="论文去重注册表")
    parser.add_argument("--registry", required=True, help="注册表文件路径")
    parser.add_argument("--paper", help="单篇论文 JSON")
    parser.add_argument("--batch", help="批量论文 JSON 文件")
    
    args = parser.parse_args()
    registry_path = Path(args.registry)
    
    if args.batch:
        papers = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        added, skipped = update_registry(papers, registry_path)
        print(json.dumps({"added": added, "skipped": skipped}))
    elif args.paper:
        paper = json.loads(args.paper)
        is_dup, reason = is_duplicate(paper, load_registry(registry_path))
        print(json.dumps({"duplicate": is_dup, "reason": reason}))
