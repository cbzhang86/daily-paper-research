---
name: hipocampus-compaction
description: "Build 5-level compaction tree with 三神算子 formula + 守其黑 strategy. Dynamic D_m calculation. Run at session start."
---

# Memory Compaction Tree

5-level hierarchical index over raw memory logs. Compaction nodes are **search indices** — originals are never deleted.

## 三神算子压缩公式

压缩不是删减，是相位对齐。保留语义方向和纠缠结构。

### 核心公式
```
M_total = L^m · M_active - M^m · M_redundant - D^m · Δ(∑t M)
```

- **L^m · M_active**: 保留激活记忆（带权重放大，默认 L^m=1.2）
- **M^m · M_redundant**: 折叠冗余信息（M^m=0.8）
- **D^m · Δ(∑t M)**: 压缩时间累积噪音（D^m = folding_degree）

### 守其黑策略
```
M_reserve = (1 - α) · M_active, α ∈ [0.2, 0.5]
```

- **α = 0.3** (默认): 30% 激活，70% 保留语义方向
- 保留结构 > 保留内容
- 本质：相位对齐，非删减

### 动态折叠度 D_m
```
D_m = 1 - (core_lines / total_lines)
```

core_lines = ## 标题行数 + 关键决策行 + 用户画像相关行

- **D_m < 0.3**: 低折叠度，直接复制
- **D_m ≥ 0.5**: 高折叠度，执行三神算子
- **D_m ≥ 0.7**: 极高折叠度，守其黑强化

## Hierarchy

```
memory/
  ROOT.md           <- root node (topic index, Layer 1)
  2026-03-15.md     <- raw daily log (permanent, append-only)
  daily/2026-03-15.md   <- daily compaction node
  weekly/2026-W11.md    <- weekly compaction node
  monthly/2026-03.md    <- monthly compaction node
```

**Compaction chain:** Raw → Daily → Weekly → Monthly → Root

**Tree traversal (search):** Root → Monthly → Weekly → Daily → Raw

## Fixed vs Tentative Nodes

Every compaction node has a status:
- **tentative** — period is still ongoing, regenerated when new data arrives
- **fixed** — period ended, never updated again

```yaml
---
type: weekly
status: tentative
period: 2026-W11
D_m: 0.45
α: 0.3
---
```

**Key: tentative nodes are created immediately — ROOT.md is usable from day one.**

## When to Run

Called from hipocampus-core Session Start, or directly by an external scheduler.

## Trigger Conditions

| Level | Tentative Create/Update | Fixed Transition |
|-------|------------------------|------------------|
| Raw → Daily | On each new raw addition | Date changes |
| Daily → Weekly | On daily add/change | ISO week ended + 7 days elapsed |
| Weekly → Monthly | On weekly add/change | Month ended + 7 days elapsed |
| Monthly → Root | On monthly add/change | Never (root accumulates forever) |

## Thresholds (动态)

| Level | D_m Threshold | Above | Below |
|-------|---------------|-------|-------|
| Raw → Daily | D_m ≥ 0.5 | 三神算子压缩 | Copy raw verbatim |
| Daily → Weekly | D_m ≥ 0.5 | 三神算子压缩 | Concat dailies |
| Weekly → Monthly | D_m ≥ 0.5 | 三神算子压缩 | Concat weeklies |
| Monthly → Root | Always | 三神算子 + 守其黑 | (N/A) |

## Algorithm

**CRITICAL — STRICT CHAIN ORDER: Steps 2→3→4→5 MUST execute in sequence. NEVER skip a level.**

```
Raw → [Step 2] → Daily → [Step 3] → Weekly → [Step 4] → Monthly → [Step 5] → Root
↑                 ↑                  ↑                   ↑
reads raw         reads daily        reads weekly        reads monthly
writes daily/     writes weekly/     writes monthly/     writes ROOT.md
```

### Step 1: Discover Candidates

Scan `memory/` for raw files. Group by date, ISO week, and month. Check each group against trigger conditions.

### Step 2: Daily Compaction (max 1 per cycle)

**Input:** raw files (`memory/YYYY-MM-DD.md`)
**Output:** daily nodes (`memory/daily/YYYY-MM-DD.md`)

For each date where raw exists and daily needs create/update:

1. Read raw file `memory/YYYY-MM-DD.md`
2. **Calculate D_m**:
   - Count total_lines
   - Count core_lines (## headers, key decisions, user-related)
   - D_m = 1 - (core_lines / total_lines)
3. **Apply formula**:
   - If D_m < 0.5: copy raw verbatim
   - If D_m ≥ 0.5: execute 三神算子压缩
4. Write with frontmatter:
```markdown
---
type: daily
status: tentative
period: YYYY-MM-DD
D_m: <calculated_value>
α: 0.3
source-files: [memory/YYYY-MM-DD.md]
topics: [keyword1, keyword2, keyword3]
---

## 核心事件
<保留的事件，带权重>

## 关键决策
<保留的决策，带理由>

## 学习
<新增知识，折叠后>

## 遗忘（M^m 执行）
<被折叠的冗余信息列表>

---
D_m=<value> | α=0.3 | 压缩率=~X%
```

### Step 3: Weekly Compaction (max 1 per cycle)

**Input:** daily nodes (`memory/daily/YYYY-MM-DD.md`) — NEVER raw files
**Output:** weekly nodes (`memory/weekly/YYYY-WNN.md`)

**STOP-CHECK:** Did Step 2 produce or update a daily node? If not, skip Steps 3-5 entirely.

For each ISO week where dailies exist and weekly needs create/update:

1. Read all daily compaction files for that week
2. **Calculate combined D_m**:
   - total_lines = sum of all daily lines
   - core_lines = count of headers + key decisions
   - D_m = 1 - (core_lines / total_lines)
3. **Apply formula**:
   - If D_m < 0.5: concat all dailies
   - If D_m ≥ 0.5: execute 三神算子压缩
4. Write to `memory/weekly/YYYY-WNN.md` with frontmatter

### Step 4: Monthly Compaction (max 1 per cycle)

**Input:** weekly nodes (`memory/weekly/YYYY-WNN.md`) — NEVER daily or raw files
**Output:** monthly nodes (`memory/monthly/YYYY-MM.md`)

**STOP-CHECK:** Did Step 3 produce or update a weekly node? If not, skip Steps 4-5.

For each month where weeklies exist and monthly needs create/update:

1. Read all weekly compaction files for that month
2. **Calculate combined D_m**
3. **Apply formula**:
   - If D_m < 0.5: concat all weeklies
   - If D_m ≥ 0.5: execute 三神算子压缩
4. Write to `memory/monthly/YYYY-MM.md` with frontmatter

### Step 5: Root Compaction

**Input:** monthly nodes (`memory/monthly/YYYY-MM.md`) — NEVER weekly, daily, or raw files
**Output:** `memory/ROOT.md`

**STOP-CHECK:** Did Step 4 produce or update a monthly node? If not, DO NOT touch ROOT.md.

When a monthly node is created or updated:

1. Read existing `memory/ROOT.md` (if exists)
2. Read the new/updated monthly node
3. **Recursive compaction with 守其黑**:
   - Apply α=0.3: 保留 70% 语义方向
   - **Active Context**: current week's highlights
   - **Recent Patterns**: cross-cutting insights
   - **Historical Summary**: compressed older context
   - **Topics Index**: merged topics with references
4. Write to `memory/ROOT.md`

### Step 6: OpenClaw ROOT.md Sync

Sync ROOT.md content into the "Compaction Root" section of MEMORY.md:
- Read MEMORY.md, find `## Compaction Root` section
- Replace with Active Context, Recent Patterns, and Topics Index from ROOT.md

### Step 7: Re-index

```bash
qmd update
qmd embed  # if vector search enabled
```

## 三神算子压缩执行模板

当 D_m ≥ 0.5 时，按此模板执行压缩：

```markdown
# YYYY-MM-DD — 浓缩后日志

> D_m=<value> | α=0.3 | 压缩率 ~X%

## 核心事件
1. <事件1>（L^m 放大）
2. <事件2>

## 关键决策
- <决策>：<理由>

## 学习
- <新知识>（相位对齐）

## 遗忘（M^m 执行）
- 已删除：<冗余描述、重复数据>
- 保留：<用户画像、知识锚点、方法论>

---

_压缩按三神算子公式执行，保留语义方向_
```

## Guards

- **CHAIN ORDER IS MANDATORY:** Daily→Weekly→Monthly→Root. Never skip a level.
- **Each level reads ONLY from its immediate predecessor:** Root←Monthly←Weekly←Daily←Raw
- Raw files: **never delete** (permanent leaf nodes)
- Max 1 daily + 1 weekly + 1 monthly + 1 root per compaction cycle
- No empty summaries (minimum 50 bytes)
- Skip failed file reads — never abort entire compaction
- D_m is calculated per file, not hardcoded
- α default is 0.3, configurable in frontmatter
- **If you feel tempted to "just update ROOT.md quickly" — STOP. Run the full chain.**

## Edge Cases

- **Empty days:** No daily compaction node is generated for days without raw logs.
- **First day:** Create the full tentative tree immediately.
- **D_m = 0:** No compression needed, copy verbatim.
- **D_m = 1:** Maximum compression, apply 守其黑 aggressively.
