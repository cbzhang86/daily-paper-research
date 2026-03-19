#!/usr/bin/env python3
"""
每日论文日报自动推送脚本
每天早上九点运行，生成日报并推送
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加 scripts 目录到路径
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from run_daily_pipeline import main as run_pipeline, SKILL_DIR


def generate_daily_report() -> str:
    """运行论文采集并生成日报"""
    import asyncio
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[{date_str}] 开始生成每日论文日报...")
    
    # 运行 pipeline
    asyncio.run(run_pipeline())
    
    # 读取生成的报告
    output_dir = SKILL_DIR / "data" / "daily" / date_str
    report_file = output_dir / "report.md"
    
    if report_file.exists():
        report = report_file.read_text(encoding="utf-8")
        print(f"[{date_str}] 日报生成完成")
        return report
    else:
        return f"[{date_str}] 日报生成失败"


def send_to_feishu(report: str) -> bool:
    """发送日报到飞书"""
    # TODO: 配置飞书 webhook
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
    
    if not webhook_url:
        print("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        return False
    
    # 这里可以调用飞书 API 发送消息
    # 暂时打印到控制台
    print("=" * 50)
    print("日报内容：")
    print("=" * 50)
    print(report[:1000] + "..." if len(report) > 1000 else report)
    print("=" * 50)
    
    return True


def main():
    """主函数"""
    # 1. 生成日报
    report = generate_daily_report()
    
    # 2. 推送到飞书
    send_to_feishu(report)
    
    # 3. 输出统计
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = SKILL_DIR / "data" / "daily" / date_str
    manifest_file = output_dir / "manifest.json"
    
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        print(f"\n统计信息：")
        print(f"  采集论文: {manifest.get('raw_count', 0)} 篇")
        print(f"  归一化: {manifest.get('normalized_count', 0)} 篇")
        print(f"  重点推荐: {manifest.get('selected_count', 0)} 篇")


if __name__ == "__main__":
    main()
