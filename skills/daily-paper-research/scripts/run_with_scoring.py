#!/usr/bin/env python3
"""
增强版 Pipeline 运行器
集成 PaperClaw 四维评分 + 去重注册表

使用方法：
python run_with_scoring.py --date 2026-03-19
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加 scripts 目录到路径
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scoring import score_papers_batch, calculate_paper_score
from registry import update_registry, filter_duplicates, load_registry


def enhance_pipeline_output(
    date_str: str,
    output_dir: Path,
    registry_path: Path | None = None
) -> dict:
    """
    增强已有的 pipeline 输出
    
    Args:
        date_str: 日期字符串
        output_dir: 输出目录
        registry_path: 注册表路径（可选）
    
    Returns:
        dict: 处理统计
    """
    # 加载已有数据
    normalized_file = output_dir / "normalized.json"
    analysis_file = output_dir / "analysis.json"
    
    if not normalized_file.exists():
        print(f"错误: 找不到 {normalized_file}")
        return {"error": "normalized.json not found"}
    
    # 读取归一化数据
    with open(normalized_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    
    stats = {
        "date": date_str,
        "input_papers": len(papers),
        "scored_papers": 0,
        "unique_papers": 0,
        "duplicate_skipped": 0,
    }
    
    # 1. 添加四维评分
    print(f"正在为 {len(papers)} 篇论文添加评分...")
    papers_with_scores = score_papers_batch(papers)
    stats["scored_papers"] = len(papers_with_scores)
    
    # 2. 去重检查（如果提供了注册表）
    if registry_path:
        print(f"检查去重注册表...")
        unique_papers = filter_duplicates(papers_with_scores, registry_path)
        stats["unique_papers"] = len(unique_papers)
        stats["duplicate_skipped"] = len(papers_with_scores) - len(unique_papers)
        
        # 更新注册表
        added, skipped = update_registry(unique_papers, registry_path)
        print(f"注册表更新: 新增 {added}, 跳过 {skipped}")
    else:
        unique_papers = papers_with_scores
        stats["unique_papers"] = len(unique_papers)
    
    # 3. 按评分排序
    sorted_papers = sorted(
        unique_papers,
        key=lambda x: x.get("paper_score", {}).get("final_score", 0),
        reverse=True
    )
    
    # 4. 更新 analysis.json
    if analysis_file.exists():
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        # 添加评分信息到 selected_papers
        for i, paper in enumerate(sorted_papers[:12]):
            if i < len(analysis.get("selected_papers", [])):
                analysis["selected_papers"][i]["paper_score"] = paper.get("paper_score")
        
        # 添加评分统计
        analysis["scoring_stats"] = {
            "avg_final_score": sum(
                p.get("paper_score", {}).get("final_score", 0) 
                for p in sorted_papers[:12]
            ) / min(12, len(sorted_papers)) if sorted_papers else 0,
            "top_score": sorted_papers[0].get("paper_score", {}) if sorted_papers else {},
        }
        
        # 写回 analysis.json
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    # 5. 写入带评分的数据
    scored_file = output_dir / "scored.json"
    with open(scored_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_papers, f, ensure_ascii=False, indent=2)
    
    # 6. 更新 manifest
    manifest_file = output_dir / "manifest.json"
    if manifest_file.exists():
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        manifest["scored_count"] = len(sorted_papers)
        manifest["scoring_integrated"] = True
        manifest["scoring_version"] = "paperclaw-v1"
        
        if registry_path:
            manifest["registry_updated"] = True
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成:")
    print(f"  输入: {stats['input_papers']} 篇")
    print(f"  评分: {stats['scored_papers']} 篇")
    print(f"  去重后: {stats['unique_papers']} 篇")
    if registry_path:
        print(f"  跳过重复: {stats['duplicate_skipped']} 篇")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="运行带评分和去重的 pipeline")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--run-pipeline", action="store_true", help="先运行基础 pipeline")
    
    args = parser.parse_args()
    
    # 确定输出目录
    skill_dir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir) if args.output_dir else skill_dir / "data" / "daily" / args.date
    
    # 确定注册表路径
    registry_path = Path(args.registry) if args.registry else skill_dir / "data" / "evaluated_papers.json"
    
    # 如果需要，先运行基础 pipeline
    if args.run_pipeline:
        import subprocess
        print("运行基础 pipeline...")
        result = subprocess.run(
            [sys.executable, str(skill_dir / "scripts" / "run_daily_pipeline.py"), "--date", args.date],
            cwd=str(skill_dir)
        )
        if result.returncode != 0:
            print(f"基础 pipeline 失败: {result.returncode}")
            return 1
    
    # 增强 pipeline 输出
    stats = enhance_pipeline_output(args.date, output_dir, registry_path)
    
    if "error" in stats:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
