# HEARTBEAT.md — 每日主动检查

> 每天主动检查 2-4 次，不等指令，主动发现问题

## 每次心跳检查项

### Hipocampus Memory Maintenance
- [ ] 运行 `hipocampus compact`（如有新 raw 日志）
- [ ] 检查 SCRATCHPAD.md 完成项，归档
- [ ] 检查 WORKING.md 超 7 天任务

### 记忆浓缩维护 (三神算子)
- [ ] 检查 MEMORY.md 大小，超 50 行则浓缩
- [ ] 检查 D_m（记忆折叠度），>0.5 触发 M^m
- [ ] 执行守其黑：保持 α=0.3

### 主动检查（每日 2-4 次）
- [ ] .learnings/ 有新错误需要回顾吗？
- [ ] 有长时间未完成的任务吗？
- [ ] MEMORY.md 中有过期信息需要清理吗？
- [ ] 有安全事件需要记录吗？

### 版本检查（每周一次）
- [ ] hipocampus 有更新吗？
- [ ] openclaw 有更新吗？
- [ ] 其他技能有更新吗？

---

## 📅 每日定时任务

### 早上 9:00 — 论文日报生成

**任务内容：**
1. 运行 `skills/daily-paper-research/scripts/daily_push.py`
2. 生成当日论文日报
3. 推送给用户

**触发方式：**
心跳检查时，如果当前时间在 9:00-10:00 之间，且今日日报未生成，则自动运行

**检查条件：**
- 当前时间：9:00-10:00
- 今日日报文件不存在：`skills/daily-paper-research/data/daily/YYYY-MM-DD/report.md`

**执行脚本：**
```bash
python skills/daily-paper-research/scripts/daily_push.py
```
