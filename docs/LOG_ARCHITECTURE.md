# ACE框架日志架构设计

## 设计原则

1. **统一运行ID** - 每次ACE循环分配唯一ID，关联所有相关日志
2. **双重索引** - 支持按组件查看 + 按运行查看
3. **时间分区** - 按日期组织，便于清理和归档
4. **格式统一** - 所有日志使用JSONL（每行一个JSON对象）
5. **易于查询** - 结构化字段，支持grep/jq等工具
6. **增量写入** - 支持追加写入，不阻塞运行
7. **自包含** - 每条日志记录包含必要的上下文信息

---

## 目录结构

```
logs/
├── README.md                          # 日志系统说明文档
├── .gitignore                         # 忽略日志文件（过大）
│
├── runs/                              # 【核心】按运行组织（最常用）
│   ├── runs_index.jsonl               # 运行索引（元数据）
│   ├── 2025-01-23/                    # 按日期分区
│   │   ├── run_143015_aBc123/         # run_id = {时间}_{随机后缀}
│   │   │   ├── metadata.json          # 运行元数据
│   │   │   ├── generator.jsonl        # Generator事件日志
│   │   │   ├── reflector.jsonl        # Reflector事件日志
│   │   │   ├── curator.jsonl          # Curator事件日志
│   │   │   ├── performance.json       # 性能统计
│   │   │   └── summary.json           # 运行摘要
│   │   ├── run_150422_Xy9Def/
│   │   │   └── ...
│   │   └── ...
│   ├── 2025-01-24/
│   │   └── ...
│   └── ...
│
├── components/                        # 【备选】按组件聚合（全局分析用）
│   ├── generator.jsonl                # 所有Generator事件
│   ├── reflector.jsonl                # 所有Reflector事件
│   └── curator.jsonl                  # 所有Curator事件
│
├── llm_calls/                         # 【A4】LLM调用记录
│   ├── 2025-01-23/
│   │   ├── 143015_aBc123_generator.json
│   │   ├── 143045_aBc123_reflector_round1.json
│   │   ├── 143052_aBc123_reflector_round2.json
│   │   ├── 143120_aBc123_curator.json
│   │   └── ...
│   └── ...
│
├── prompts/                           # 【A5相关】提示词保存（可选，如果单独需要）
│   ├── 2025-01-23/
│   │   ├── 143015_aBc123_generator.txt
│   │   ├── 143045_aBc123_reflector_initial.txt
│   │   └── ...
│   └── ...
│
├── playbook_versions/                 # 【A2】Playbook版本历史
│   ├── versions_index.jsonl           # 版本索引
│   ├── playbook_20250123_143200_v001.json
│   ├── meta_20250123_143200_v001.json # 版本元数据
│   ├── playbook_20250123_150500_v002.json
│   ├── meta_20250123_150500_v002.json
│   └── ...
│
├── performance/                       # 【A3】性能数据（可选聚合）
│   ├── daily_summary.jsonl            # 每日性能摘要
│   └── 2025-01-23_performance.json    # 单日详细数据
│
├── errors/                            # 错误日志（未来B2）
│   ├── errors.jsonl                   # 所有错误记录
│   └── 2025-01-23/
│       └── error_143015_aBc123.json   # 错误现场快照
│
└── archive/                           # 归档目录（30天前的日志）
    ├── 2024-12-20.tar.gz
    └── ...
```

---

## 核心设计决策

### 1. 运行ID (run_id) 设计

```python
run_id = f"{timestamp}_{random_suffix}"
# 示例: "143015_aBc123"
#       ^^^^^^  ^^^^^^
#       HHMMSS  6字符随机（避免冲突）
```

**优势**:
- 人类可读的时间信息
- 随机后缀避免并发冲突
- 可作为目录名和文件名前缀

### 2. 日志格式标准

#### 基础格式（所有日志共享）

```json
{
  "timestamp": "2025-01-23T14:30:15.123456Z",  // ISO 8601，带微秒
  "run_id": "143015_aBc123",                   // 关联到具体运行
  "component": "generator",                     // generator/reflector/curator
  "event_type": "bullet_retrieval",            // 事件类型
  "level": "info",                             // info/warning/error
  "data": { /* 事件特定数据 */ }
}
```

#### Generator事件类型

```python
event_types = [
    "bullet_retrieval",      # Bullet检索完成
    "prompt_constructed",    # Prompt构建完成
    "llm_call_started",      # LLM调用开始
    "llm_call_completed",    # LLM调用完成
    "output_parsed",         # 输出解析完成
    "plan_generated",        # 方案生成完成
]
```

#### Reflector事件类型

```python
event_types = [
    "reflection_started",         # 开始reflection
    "initial_reflection_done",    # 初始reflection完成
    "refinement_round_started",   # 某轮refinement开始
    "refinement_round_completed", # 某轮refinement完成
    "bullet_tagging_done",        # Bullet tagging完成
    "insights_extracted",         # Insights提取完成
]
```

#### Curator事件类型

```python
event_types = [
    "curation_started",           # 开始curation
    "delta_operations_generated", # Delta operations生成
    "operation_applied",          # 单个operation应用
    "deduplication_started",      # 去重开始
    "deduplication_completed",    # 去重完成
    "pruning_started",            # Pruning开始
    "pruning_completed",          # Pruning完成
    "playbook_updated",           # Playbook更新完成
]
```

### 3. 文件格式选择

| 文件类型 | 格式 | 原因 |
|---------|------|------|
| 事件日志 | JSONL | 追加写入，逐行解析，支持流式处理 |
| 元数据 | JSON | 结构固定，一次性读写 |
| 索引文件 | JSONL | 追加写入，快速查找 |
| Playbook版本 | JSON | 结构化数据，完整保存 |
| LLM调用记录 | JSON | 包含大文本，单独文件 |
| 性能统计 | JSON | 聚合数据，一次性读写 |

### 4. 索引机制

#### runs_index.jsonl
```json
{"run_id": "143015_aBc123", "timestamp": "2025-01-23T14:30:15Z", "date": "2025-01-23", "status": "completed", "components": ["generator", "reflector", "curator"], "duration": 125.3, "playbook_version": "v001"}
{"run_id": "150422_Xy9Def", "timestamp": "2025-01-23T15:04:22Z", "date": "2025-01-23", "status": "completed", "components": ["generator", "reflector", "curator"], "duration": 118.7, "playbook_version": "v002"}
```

**用途**:
- 快速查找特定运行
- 统计总运行次数
- 过滤失败的运行
- 查看运行趋势

#### versions_index.jsonl
```json
{"version": "v001", "timestamp": "2025-01-23T14:32:00Z", "run_id": "143015_aBc123", "size": 21, "reason": "After ACE cycle", "changes": {"added": 3, "updated": 0, "removed": 0}}
{"version": "v002", "timestamp": "2025-01-23T15:05:00Z", "run_id": "150422_Xy9Def", "size": 22, "reason": "After ACE cycle", "changes": {"added": 1, "updated": 1, "removed": 0}}
```

---

## 详细日志内容设计

### A1: 结构化日志

#### Generator日志示例

```jsonl
{"timestamp": "2025-01-23T14:30:15.123Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "bullet_retrieval", "level": "info", "data": {"query": "Synthesize aspirin from salicylic acid", "bullets_retrieved": 7, "top_k": 50, "min_similarity": 0.3, "top_similarities": [0.87, 0.82, 0.79, 0.75, 0.72, 0.68, 0.65], "sections": {"material_selection": 3, "procedure_design": 4}}}
{"timestamp": "2025-01-23T14:30:16.234Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "prompt_constructed", "level": "info", "data": {"prompt_length": 2543, "num_bullets": 7, "num_templates": 0, "num_examples": 0}}
{"timestamp": "2025-01-23T14:30:16.345Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "llm_call_started", "level": "info", "data": {"model": "qwen-max", "config": {"temperature": 0.7, "max_tokens": 4000}}}
{"timestamp": "2025-01-23T14:30:41.567Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "llm_call_completed", "level": "info", "data": {"duration": 25.2, "tokens": {"input": 2543, "output": 1203}, "llm_call_id": "143015_aBc123_generator"}}
{"timestamp": "2025-01-23T14:30:41.678Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "output_parsed", "level": "info", "data": {"success": true, "plan_title": "Synthesis of Aspirin from Salicylic Acid", "materials_count": 5, "procedure_steps": 8}}
{"timestamp": "2025-01-23T14:30:41.789Z", "run_id": "143015_aBc123", "component": "generator", "event_type": "plan_generated", "level": "info", "data": {"total_duration": 26.7, "bullets_used": ["mat-00001", "mat-00005", "proc-00003", "proc-00007", "safe-00002", "qc-00004", "qc-00008"]}}
```

#### Reflector日志示例

```jsonl
{"timestamp": "2025-01-23T14:30:45.123Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "reflection_started", "level": "info", "data": {"plan_title": "Synthesis of Aspirin from Salicylic Acid", "feedback_score": 0.81, "max_refinement_rounds": 5}}
{"timestamp": "2025-01-23T14:31:00.456Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "initial_reflection_done", "level": "info", "data": {"duration": 15.3, "insights_count": 5, "priority_distribution": {"high": 1, "medium": 3, "low": 1}}}
{"timestamp": "2025-01-23T14:31:00.567Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "refinement_round_started", "level": "info", "data": {"round": 2}}
{"timestamp": "2025-01-23T14:31:16.789Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "refinement_round_completed", "level": "info", "data": {"round": 2, "duration": 16.2, "insights_count": 4, "quality_improved": true}}
{"timestamp": "2025-01-23T14:31:17.890Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "refinement_round_started", "level": "info", "data": {"round": 3}}
...
{"timestamp": "2025-01-23T14:32:15.123Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "bullet_tagging_done", "level": "info", "data": {"tags": {"mat-00001": "helpful", "mat-00005": "helpful", "proc-00003": "neutral", "proc-00007": "helpful", "safe-00002": "helpful", "qc-00004": "neutral", "qc-00008": "helpful"}, "helpful": 5, "harmful": 0, "neutral": 2}}
{"timestamp": "2025-01-23T14:32:15.234Z", "run_id": "143015_aBc123", "component": "reflector", "event_type": "insights_extracted", "level": "info", "data": {"total_duration": 90.1, "final_insights_count": 3, "refinement_rounds_completed": 5}}
```

#### Curator日志示例

```jsonl
{"timestamp": "2025-01-23T14:32:20.123Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "curation_started", "level": "info", "data": {"insights_count": 3, "current_playbook_size": 21}}
{"timestamp": "2025-01-23T14:32:35.456Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "delta_operations_generated", "level": "info", "data": {"duration": 15.3, "operations": {"ADD": 2, "UPDATE": 1, "REMOVE": 0}}}
{"timestamp": "2025-01-23T14:32:35.567Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "operation_applied", "level": "info", "data": {"operation": "ADD", "bullet_id": "qc-00015", "section": "quality_control", "reason": "Insight: best_practice - Add TLC monitoring", "duplicate_check": {"is_duplicate": false, "closest_similarity": 0.72}}}
{"timestamp": "2025-01-23T14:32:35.678Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "operation_applied", "level": "info", "data": {"operation": "ADD", "bullet_id": "safe-00011", "section": "safety_protocols", "reason": "Insight: safety_issue - Add acetic anhydride handling", "duplicate_check": {"is_duplicate": false, "closest_similarity": 0.65}}}
{"timestamp": "2025-01-23T14:32:35.789Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "operation_applied", "level": "info", "data": {"operation": "UPDATE", "bullet_id": "proc-00007", "reason": "Insight: best_practice - Clarify recrystallization procedure", "content_changed": true}}
{"timestamp": "2025-01-23T14:32:36.890Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "deduplication_started", "level": "info", "data": {"threshold": 0.85, "candidates_count": 23}}
{"timestamp": "2025-01-23T14:32:38.123Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "deduplication_completed", "level": "info", "data": {"duration": 1.2, "duplicates_found": 0, "merges": []}}
{"timestamp": "2025-01-23T14:32:38.234Z", "run_id": "143015_aBc123", "component": "curator", "event_type": "playbook_updated", "level": "info", "data": {"total_duration": 18.1, "size_before": 21, "size_after": 23, "changes": {"added": 2, "updated": 1, "removed": 0}, "new_version": "v002"}}
```

### A2: Playbook版本

#### 版本文件命名
```
playbook_{date}_{time}_v{version}.json
meta_{date}_{time}_v{version}.json
```

#### meta文件内容
```json
{
  "version": "v002",
  "timestamp": "2025-01-23T14:32:38Z",
  "run_id": "143015_aBc123",
  "playbook_path": "data/playbooks/chemistry_playbook.json",
  "reason": "After ACE cycle",
  "trigger": "curator_update",
  "changes": {
    "added": 2,
    "updated": 1,
    "removed": 0,
    "added_bullets": ["qc-00015", "safe-00011"],
    "updated_bullets": ["proc-00007"],
    "removed_bullets": []
  },
  "size": {
    "before": 21,
    "after": 23
  },
  "section_distribution": {
    "material_selection": 4,
    "procedure_design": 6,
    "safety_protocols": 5,
    "quality_control": 4,
    "troubleshooting": 2,
    "common_mistakes": 2
  },
  "avg_helpfulness_score": 0.72,
  "generation_metadata": {
    "feedback_score": 0.81,
    "insights_count": 3,
    "reflector_rounds": 5
  }
}
```

### A3: 性能监控

#### runs/{date}/{run_id}/performance.json
```json
{
  "run_id": "143015_aBc123",
  "timestamp": "2025-01-23T14:30:15Z",
  "total_duration": 134.9,
  "breakdown": {
    "generator": {
      "total": 26.7,
      "bullet_retrieval": 1.1,
      "prompt_construction": 0.1,
      "llm_call": 25.2,
      "output_parsing": 0.3
    },
    "reflector": {
      "total": 90.1,
      "initial_reflection": 15.3,
      "refinement_rounds": [16.2, 15.8, 15.4, 14.9, 14.5],
      "bullet_tagging": 1.0,
      "overhead": 1.0
    },
    "curator": {
      "total": 18.1,
      "delta_generation": 15.3,
      "operations_apply": 0.3,
      "deduplication": 1.2,
      "playbook_save": 1.3
    }
  },
  "llm_stats": {
    "total_calls": 7,
    "calls_breakdown": {
      "generator": 1,
      "reflector": 5,
      "curator": 1
    },
    "tokens": {
      "total_input": 15320,
      "total_output": 8450,
      "total": 23770
    },
    "avg_call_duration": 18.4
  }
}
```

### A4: LLM调用记录

#### 文件命名
```
{time}_{run_id}_{component}_{detail}.json
```

#### 内容格式
```json
{
  "llm_call_id": "143015_aBc123_generator",
  "run_id": "143015_aBc123",
  "timestamp": "2025-01-23T14:30:16.345Z",
  "component": "generator",
  "stage": "generation",
  "model": {
    "provider": "qwen",
    "name": "qwen-max",
    "config": {
      "temperature": 0.7,
      "max_tokens": 4000,
      "top_p": 0.95
    }
  },
  "request": {
    "system_prompt": "You are an expert chemistry experiment planner...",
    "user_prompt": "# Experiment Requirements\n\nTarget Compound: Aspirin...",
    "prompt_length": 2543
  },
  "response": {
    "content": "{\"title\": \"Synthesis of Aspirin from Salicylic Acid\", ...}",
    "length": 1203
  },
  "tokens": {
    "input": 2543,
    "output": 1203,
    "total": 3746
  },
  "timing": {
    "started_at": "2025-01-23T14:30:16.345Z",
    "completed_at": "2025-01-23T14:30:41.567Z",
    "duration": 25.222
  },
  "status": "success"
}
```

---

## 查询和使用示例

### 1. 查看特定运行的所有日志

```bash
# 列出某天的所有运行
ls logs/runs/2025-01-23/

# 查看特定运行的摘要
cat logs/runs/2025-01-23/run_143015_aBc123/summary.json | jq

# 查看Generator日志
cat logs/runs/2025-01-23/run_143015_aBc123/generator.jsonl | jq

# 过滤特定事件
cat logs/runs/2025-01-23/run_143015_aBc123/generator.jsonl | jq 'select(.event_type == "bullet_retrieval")'
```

### 2. 查询所有运行的统计

```bash
# 查看所有运行
cat logs/runs/runs_index.jsonl | jq

# 统计成功率
cat logs/runs/runs_index.jsonl | jq 'select(.status == "completed")' | wc -l

# 平均运行时间
cat logs/runs/runs_index.jsonl | jq -r '.duration' | awk '{s+=$1; c++} END {print s/c}'
```

### 3. 追踪Playbook演化

```bash
# 查看所有版本
cat logs/playbook_versions/versions_index.jsonl | jq

# 对比两个版本
python scripts/diff_playbook_versions.py \
  logs/playbook_versions/playbook_20250123_143200_v001.json \
  logs/playbook_versions/playbook_20250123_150500_v002.json
```

### 4. 分析LLM调用

```bash
# 查看某天的所有LLM调用
ls logs/llm_calls/2025-01-23/

# 统计token消耗
cat logs/llm_calls/2025-01-23/*.json | jq -r '.tokens.total' | awk '{s+=$1} END {print s}'

# 找出最慢的调用
cat logs/llm_calls/2025-01-23/*.json | jq -r '[.llm_call_id, .timing.duration] | @tsv' | sort -k2 -n -r | head -5
```

### 5. 性能分析

```bash
# 查看某次运行的性能数据
cat logs/runs/2025-01-23/run_143015_aBc123/performance.json | jq '.breakdown'

# 找出瓶颈
cat logs/runs/2025-01-23/run_143015_aBc123/performance.json | jq '.breakdown | to_entries | sort_by(.value.total) | reverse'
```

---

## 日志轮转和清理策略

### 自动清理规则（可选实现）

```python
# 保留策略
retention_policy = {
    "runs/": 30,              # 30天
    "llm_calls/": 30,         # 30天
    "playbook_versions/": -1, # 永久保留
    "components/": 90,        # 90天（全局日志）
    "errors/": 90,            # 90天
}

# 归档策略
archive_policy = {
    "enabled": True,
    "threshold_days": 30,
    "archive_dir": "logs/archive/",
    "compression": "gzip"
}
```

### 目录大小估算

```
假设每天运行50次ACE循环:

- runs/: ~50个目录/天 × 500KB/目录 = 25MB/天 = 750MB/月
- llm_calls/: ~350个文件/天 × 50KB/文件 = 17.5MB/天 = 525MB/月
- playbook_versions/: ~50个版本/天 × 20KB/版本 = 1MB/天 = 30MB/月
- components/: ~1MB/天 = 30MB/月

总计: ~44MB/天 ≈ 1.3GB/月

启用30天轮转后，磁盘占用稳定在 ~1.3GB
```

---

## 工具支持

### 必需工具

1. **logs_manager.py** - 日志管理器
   - 创建run_id
   - 创建日志目录结构
   - 更新索引文件
   - 自动清理和归档

2. **query_logs.py** - 日志查询工具
   - 按run_id查询
   - 按组件查询
   - 按时间范围查询
   - 按事件类型查询

3. **diff_playbook_versions.py** - 版本对比工具
   - 对比两个版本的差异
   - 生成可读的diff报告

4. **analyze_performance.py** - 性能分析工具
   - 聚合多次运行的性能数据
   - 识别瓶颈
   - 生成性能报告

---

## 实现优先级

### Phase 1: 核心基础（必需）
- [x] 设计日志架构
- [ ] 实现logs_manager.py
- [ ] 实现StructuredLogger类
- [ ] 集成到Generator/Reflector/Curator
- [ ] 实现PlaybookVersionTracker类
- [ ] 实现PerformanceMonitor类
- [ ] 实现LLMCallTracker类

### Phase 2: 查询工具（重要）
- [ ] 实现query_logs.py
- [ ] 实现diff_playbook_versions.py
- [ ] 实现analyze_performance.py

### Phase 3: 优化（可选）
- [ ] 日志轮转和清理
- [ ] 日志压缩
- [ ] 索引优化

---

## 总结

**关键设计决策**:
1. ✅ **运行ID作为核心关联** - 一次运行的所有日志通过run_id关联
2. ✅ **双重组织** - 既支持按运行查看（常用），也支持按组件查看（全局分析）
3. ✅ **时间分区** - 按日期组织，便于清理和归档
4. ✅ **JSONL格式** - 流式追加，逐行解析，易于查询
5. ✅ **自包含日志** - 每条日志包含timestamp、run_id、component等上下文
6. ✅ **索引文件** - 快速定位和统计

**优势**:
- 📁 结构清晰，易于导航
- 🔍 支持多种查询方式
- 📊 便于统计和分析
- 🔗 完整的关联追踪
- 🗜️ 支持清理和归档

这个架构能够支撑所有4个观测性工具（A1-A4），且可扩展到未来的B类、C类功能。
