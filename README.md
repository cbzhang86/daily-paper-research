# daily-paper-research

> Daily paper collection, analysis and report pipeline with PaperClaw scoring integration

## 项目概述

这是一个完整的论文研究自动化系统，整合了以下功能：

- **多源数据采集**：国际源（arXiv, PubMed, Semantic Scholar）+ 国内源（ncpssd, 学术世界）
- **PaperClaw 四维评分**：工程应用、架构创新、理论贡献、可靠性
- **Date-Citation 影响力调整**：基于引用数和论文年龄的动态评分
- **去重注册表**：避免重复分析同一论文
- **Semantic Scholar API**：引用数据自动补充
- **论文图片提取**：从 arXiv 源码包或 PDF 提取架构图

## 项目结构

```
├── skills/daily-paper-research/
│   ├── scripts/
│   │   ├── run_daily_pipeline.py      # 主流程脚本
│   │   ├── scoring.py                 # PaperClaw 四维评分
│   │   ├── registry.py                # 去重注册表
│   │   ├── semantic_scholar_api.py    # 引用数据获取
│   │   ├── extract_images.py          # 图片提取
│   │   ├── run_with_scoring.py        # 增强版 Pipeline
│   │   ├── ncpssd_adapter.py          # 国内源：中国社科
│   │   └── xueshushijie_adapter.py    # 国内源：学术世界
│   ├── config/
│   │   ├── topics.json                # 主题配置
│   │   └── sources.zh.json            # 中文源配置
│   ├── docs/
│   │   └── INTEGRATION.md             # 整合文档
│   └── data/
│       └── daily/                     # 日报输出
├── skills/hipocampus-compaction/      # 记忆压缩系统
├── skills/summarize/                   # 摘要技能
└── memory/                             # 记忆系统
```

## 快速开始

### 基础用法

```bash
# 运行基础 pipeline（采集 + 归一化 + 报告）
python skills/daily-paper-research/scripts/run_daily_pipeline.py --date 2026-03-19

# 运行增强版 pipeline（含评分 + 去重）
python skills/daily-paper-research/scripts/run_with_scoring.py --date 2026-03-19
```

### 单独模块调用

```bash
# 仅评分测试
python skills/daily-paper-research/scripts/scoring.py

# 图片提取
python skills/daily-paper-research/scripts/extract_images.py --arxiv-id 2301.12345

# 引用数据补充
python skills/daily-paper-research/scripts/semantic_scholar_api.py
```

## 核心功能

### 1. PaperClaw 四维评分

```python
from scoring import calculate_paper_score

score = calculate_paper_score(
    title="论文标题",
    abstract="摘要内容",
    venue="会议/期刊",
    citations=50,
    published_date="2024-06-15"
)

# 输出：
# {
#   "dimensions": {
#     "engineering_application": 5.3,
#     "architecture_innovation": 7.4,
#     "theoretical_contribution": 4.5,
#     "reliability": 7.0
#   },
#   "final_score": 5.45
# }
```

### 2. 去重注册表

```python
from registry import update_registry, filter_duplicates

# 过滤重复
unique_papers = filter_duplicates(papers, registry_path)

# 更新注册表
added, skipped = update_registry(unique_papers, registry_path)
```

### 3. 引用数据补充

```python
from semantic_scholar_api import enrich_paper_with_citations

paper = enrich_paper_with_citations(paper)
# paper["citations"] = 45
# paper["influential_citations"] = 12
```

## 整合来源

| 功能 | 来源项目 |
|------|----------|
| 四维评分系统 | [PaperClaw](https://github.com/guhaohao0991/PaperClaw) |
| 去重注册表 | [PaperClaw](https://github.com/guhaohao0991/PaperClaw) |
| Semantic Scholar API | [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv) |
| 图片提取 | [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv) |

## 配置说明

### 主题配置 (`config/topics.json`)

```json
{
  "topics": [
    {
      "key": "management",
      "label": "管理学大类",
      "keywords": ["管理", "组织", "治理"],
      "domestic_keywords": ["管理", "组织行为"],
      "arxiv_categories": ["cs.AI", "cs.LG"]
    }
  ]
}
```

### 环境变量

```bash
# 国内源凭证（可选）
export NCPSSD_USERNAME="your_username"
export NCPSSD_PASSWORD="your_password"

# Semantic Scholar API（可选）
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"
```

## 提交历史

| 提交 | 内容 |
|------|------|
| `7773406` | 四维评分 + 去重注册表 |
| `6cfaa62` | Semantic Scholar API |
| `d77e7ca` | 图片提取工具 |
| `b0e49e6` | 整合文档 |

## 许可证

MIT License

## 致谢

- [PaperClaw](https://github.com/guhaohao0991/PaperClaw) - 四维评分系统
- [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv) - Semantic Scholar API 和图片提取
- [OpenClaw](https://github.com/openclaw/openclaw) - Agent 框架
