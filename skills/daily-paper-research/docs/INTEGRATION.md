# daily-paper-research 整合文档

## 整合来源

- **PaperClaw** (https://github.com/guhaohao0991/PaperClaw)
  - 四维评分系统
  - Date-Citation 影响力调整
  - 去重注册表

- **evil-read-arxiv** (https://github.com/juliye2025/evil-read-arxiv)
  - Semantic Scholar API 集成
  - 论文图片提取
  - 推荐评分权重

---

## 模块说明

### 1. scoring.py — 四维评分系统

**来源：** PaperClaw

**功能：**
- 四维基础评分 (1-10 分)
  - engineering_application：工程应用价值
  - architecture_innovation：架构创新
  - theoretical_contribution：理论贡献
  - reliability：可靠性
- Date-Citation 影响力调整
- 领域定制评分规则

**评分公式：**
```
final_score = base_score × 0.9 + impact_score × 0.1
base_score = (dim1 + dim2 + dim3 + dim4) / 4
```

**Date-Citation 调整规则：**
- ≤3个月新论文：+0.2
- 3-24个月 + 引用≥50：+0.5
- >24个月 + 引用≥200：+0.5
- 引用密度≥10次/月：额外 +0.2

**使用方法：**
```python
from scoring import calculate_paper_score, score_papers_batch

# 单篇评分
score = calculate_paper_score(
    title="论文标题",
    abstract="摘要内容",
    venue="会议/期刊",
    citations=50,
    published_date="2024-06-15"
)

# 批量评分
scored_papers = score_papers_batch(papers)
```

---

### 2. registry.py — 去重注册表

**来源：** PaperClaw (update_registry.py)

**功能：**
- 基于 arXiv ID 去重
- 基于标题去重
- 文件锁安全写入（跨平台）
- 批量更新支持

**使用方法：**
```python
from registry import update_registry, filter_duplicates

# 更新注册表
added, skipped = update_registry(papers, registry_path)

# 过滤重复
unique_papers = filter_duplicates(papers, registry_path)
```

**注册表格式：**
```json
{
  "papers": [
    {
      "arxiv_id": "2301.12345",
      "doi": "10.1234/xxx",
      "title": "论文标题",
      "source": "arxiv",
      "evaluated_date": "2026-03-19T...",
      "final_score": 7.5
    }
  ],
  "last_updated": "2026-03-19T..."
}
```

---

### 3. semantic_scholar_api.py — 引用数据获取

**来源：** evil-read-arxiv

**功能：**
- 按 arXiv ID/DOI/标题搜索
- 获取 citations 和 influential_citations
- 计算引用趋势 (hot/rising/stable/low)
- 速率限制处理

**使用方法：**
```python
from semantic_scholar_api import get_paper_by_arxiv_id, enrich_paper_with_citations

# 按 arXiv ID 获取
paper = get_paper_by_arxiv_id("2301.12345")

# 为论文补充引用数据
enriched = enrich_paper_with_citations(paper)
```

**引用趋势判断：**
- monthly_rate ≥ 10：hot（热门）
- monthly_rate ≥ 5：rising（上升）
- monthly_rate ≥ 1：stable（稳定）
- monthly_rate < 1：low（低迷）

---

### 4. extract_images.py — 图片提取

**来源：** evil-read-arxiv

**功能：**
- 从 arXiv 源码包提取高质量图片（优先）
- 从 PDF 提取图片（备选）
- 生成图片索引 Markdown

**使用方法：**
```bash
python extract_images.py --arxiv-id 2301.12345 --output images/
```

**依赖：**
- PyMuPDF（推荐）：`pip install PyMuPDF`
- 或 pdfimages 命令行工具

---

### 5. run_with_scoring.py — 增强版 Pipeline

**功能：**
- 运行基础 pipeline
- 为所有论文添加评分
- 去重检查
- 更新注册表

**使用方法：**
```bash
# 先运行基础 pipeline
python skills/daily-paper-research/scripts/run_daily_pipeline.py --date 2026-03-19

# 然后增强输出
python skills/daily-paper-research/scripts/run_with_scoring.py --date 2026-03-19
```

---

## 完整工作流

```
                    ┌─────────────────────────────────────┐
                    │  1. 收集论文 (run_daily_pipeline)   │
                    │     - 国际源：arXiv, PubMed, etc.   │
                    │     - 国内源：ncpssd, 学术世界       │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  2. 补充引用数据 (semantic_scholar) │
                    │     - 按 arXiv ID/DOI 查询          │
                    │     - 获取 citationCount            │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  3. 四维评分 (scoring.py)           │
                    │     - 计算四维基础分                │
                    │     - Date-Citation 调整            │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  4. 去重检查 (registry.py)          │
                    │     - 检查已处理论文                │
                    │     - 更新注册表                    │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  5. 生成报告                        │
                    │     - report.md                     │
                    │     - analysis.json                 │
                    │     - scored.json                   │
                    └─────────────────────────────────────┘
```

---

## 配置说明

### 评分权重调整

编辑 `scoring.py` 中的常量：

```python
# 各维度权重
WEIGHTS_NORMAL = {
    'relevance': 0.40,
    'recency': 0.20,
    'popularity': 0.30,
    'quality': 0.10,
}

# 基础评分和影响力评分权重
# final_score = base_score × 0.9 + impact_score × 0.1
```

### 领域定制评分

在 `scoring.py` 的 `DOMAIN_RUBRICS` 中添加：

```python
DOMAIN_RUBRICS = {
    "your_domain": {
        "dimensions": [
            ("维度1", "说明1"),
            ("维度2", "说明2"),
            ("维度3", "说明3"),
            ("维度4", "说明4"),
        ]
    }
}
```

---

## 提交记录

| 提交 | 内容 | 日期 |
|------|------|------|
| `7773406` | 四维评分 + 去重注册表 | 2026-03-19 |
| `6cfaa62` | Semantic Scholar API | 2026-03-19 |
| `d77e7ca` | 图片提取工具 | 2026-03-19 |

---

## 后续优化

1. **性能优化**：批量 Semantic Scholar API 调用
2. **评分校准**：基于用户反馈调整评分权重
3. **图片筛选**：智能选择核心架构图
4. **报告模板**：按领域定制报告格式
