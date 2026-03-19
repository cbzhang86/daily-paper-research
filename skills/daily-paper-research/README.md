# Daily Paper Research Pipeline

基于 OpenClaw 的论文研究自动化系统，支持论文爬取、分析、评分和日报生成。

## 项目来源

本项目整合了以下开源项目的核心功能：

- **PaperClaw** - 四维评分系统、去重注册表
- **evil-read-arxiv** - Semantic Scholar API、图片提取

## 核心功能

### 1. 论文采集
- **国际源**：arXiv, PubMed, Crossref, Semantic Scholar
- **国内源**：ncpssd (中国社科), 学术世界 (公共PDF)

### 2. 智能评分
- 四维评分系统（工程应用、架构创新、理论贡献、可靠性）
- Date-Citation 影响力调整
- 领域定制评分规则

### 3. 数据增强
- Semantic Scholar 引用数据补充
- 自动去重（基于 arXiv ID/DOI/标题）
- 引用趋势分析

### 4. 报告生成
- Markdown 格式日报
- 主题分布分析
- 研究空白识别

### 5. 图片提取（可选）
- arXiv 源码包图片提取
- PDF 图片提取

## 目录结构

```
skills/daily-paper-research/
├── config/
│   ├── topics.json          # 研究主题配置
│   └── sources.zh.json      # 中文源配置
├── scripts/
│   ├── run_daily_pipeline.py    # 主流程脚本
│   ├── run_with_scoring.py      # 增强版流程
│   ├── scoring.py               # 四维评分模块
│   ├── registry.py              # 去重注册表
│   ├── semantic_scholar_api.py  # 引用数据模块
│   ├── extract_images.py        # 图片提取模块
│   ├── ncpssd_adapter.py        # ncpssd 适配器
│   └── xueshushijie_adapter.py  # 学术世界适配器
├── templates/
│   └── report_template.md   # 报告模板
├── docs/
│   ├── ARCHITECTURE.md      # 架构文档
│   └── INTEGRATION.md       # 整合文档
└── data/
    └── daily/               # 每日输出
```

## 快速开始

### 1. 配置环境变量

```bash
# ncpssd 登录凭证（可选）
export NCPSSD_USERNAME="your_username"
export NCPSSD_PASSWORD="your_password"

# Semantic Scholar API Key（可选，提高速率限制）
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"
```

### 2. 配置研究主题

编辑 `config/topics.json`：

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

### 3. 运行流程

```bash
# 基础流程
python skills/daily-paper-research/scripts/run_daily_pipeline.py --date 2026-03-19

# 增强流程（含评分）
python skills/daily-paper-research/scripts/run_with_scoring.py --date 2026-03-19
```

## 评分系统

### 四维评分

| 维度 | 名称 | 评估内容 |
|------|------|----------|
| dim1 | engineering_application | 工程应用价值、实际场景 |
| dim2 | architecture_innovation | 架构创新、方法论 |
| dim3 | theoretical_contribution | 理论贡献、数学分析 |
| dim4 | reliability | 可靠性、实验充分性 |

### 评分公式

```
final_score = base_score × 0.9 + impact_score × 0.1

base_score = (dim1 + dim2 + dim3 + dim4) / 4

impact_score = date_citation_adjustment(citations, age_months)
```

### Date-Citation 调整

- ≤3个月新论文：+0.2
- 3-24个月 + 引用≥50：+0.5
- >24个月 + 引用≥200：+0.5
- 引用密度≥10次/月：额外 +0.2

## 输出示例

### 日报结构

```markdown
# 每日论文抓取分析日报 - 2026-03-19

## 一、今日概况
- 抓取总量：198
- 重点入选：12

## 二、今日重点论文
### 1. [论文标题]
- 年份：2024
- 评分：7.5
- 摘要：...

## 三、主题观察
## 四、方法与趋势
## 五、可跟进研究问题
## 六、后续写作可复用资产
```

## 依赖安装

```bash
# 基础依赖
pip install asyncio aiohttp

# 图片提取（可选）
pip install PyMuPDF

# YAML 配置
pip install pyyaml
```

## 技术架构

```
数据采集 → 归一化 → 引用补充 → 四维评分 → 去重 → 报告生成
   │          │          │          │        │        │
   ▼          ▼          ▼          ▼        ▼        ▼
 国际源    normalize   semantic   scoring  registry  render
 国内源    dedup       scholar             update    report
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

- [PaperClaw](https://github.com/guhaohao0991/PaperClaw) - 评分系统
- [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv) - API 和图片提取
- [OpenClaw](https://github.com/openclaw/openclaw) - 框架支持
