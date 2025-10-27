# 日志查询指南

本文档说明如何查询和分析系统的两种日志记录。

## 📊 两种日志系统对比

### 1. ACE框架训练循环 (`query_runs.py`)

**用途**: 查询离线训练和playbook进化的ACE循环记录

**日志位置**: `logs/runs/<date>/run_<run_id>/`

**包含文件**:
- `generator.jsonl` - Generator组件日志
- `reflector.jsonl` - Reflector组件日志
- `curator.jsonl` - Curator组件日志
- `performance.json` - 性能统计

**使用场景**:
- 分析ACE框架的学习过程
- 研究playbook进化趋势
- 评估不同组件的性能

### 2. Workflow CLI生成任务 (`inspect_tasks.py`)

**用途**: 查询实际生产环境的方案生成流程和反馈循环

**日志位置**: `logs/generation_tasks/<task_id>/`

**包含文件**:
- `task.json` - 任务状态和元数据
- `requirements.json` - 提取的结构化需求
- `templates.json` - RAG检索的模板
- `plan.json` - 生成的实验方案
- `feedback.json` - **反馈循环评分**
- `curation.json` - **Playbook更新记录**
- `task.log` - 完整执行日志

**使用场景**:
- 监控实时任务进度
- 查看方案生成结果
- **分析反馈循环（重要！）**
- 追踪playbook更新

---

## 🔍 查询Workflow CLI反馈循环

### 基本用法

```bash
# 1. 激活conda环境（必须！）
conda activate OntologyConstruction

# 2. 列出所有任务
python scripts/inspect_tasks.py --list

# 3. 查看任务详情
python scripts/inspect_tasks.py --task <task_id>

# 4. 查看反馈循环（⭐核心功能⭐）
python scripts/inspect_tasks.py --feedback <task_id>

# 5. 查看完整方案
python scripts/inspect_tasks.py --plan <task_id>

# 6. 实时监控任务
python scripts/inspect_tasks.py --watch <task_id>

# 7. 查看执行日志
python scripts/inspect_tasks.py --log <task_id>
```

### 反馈循环数据解读

运行 `--feedback` 命令后会显示：

**🔍 反馈评分** (来自 `feedback.json`):
- **completeness** (完整性): 方案是否包含所有必需部分
- **safety** (安全性): 安全措施是否充分
- **clarity** (清晰度): 描述是否易于理解
- **executability** (可执行性): 实验人员能否实际操作
- **cost_effectiveness** (成本效益): 资源利用是否合理
- **overall_score** (总分): 加权平均分

**📚 Playbook更新** (来自 `curation.json`):
- **更新后的规则总数**: Playbook包含的所有规则数量
- **各section的规则分布**: 每个section（material_selection, procedure_design等）的规则数量
- **规则来源分布**: 按来源统计（seed/reflection/manual）
- **本次变更统计**: 新增/修改/删除的数量
- **详细变更**: 按操作类型分组显示（ADD/UPDATE/REMOVE）
  - 新增规则：显示bullet ID、section、内容和原因
  - 修改规则：显示bullet ID、新内容和修改原因
  - 删除规则：显示bullet ID和删除原因
- **每条最多显示5项**，超过则提示剩余数量

---

## 🎯 常见查询场景

### 场景1: 检查最新任务的反馈循环

```bash
# 步骤1: 列出所有任务（最新的在最上面）
python scripts/inspect_tasks.py --list

# 步骤2: 复制最新任务的ID（例如 d30aea0e）
# 步骤3: 查看反馈循环
python scripts/inspect_tasks.py --feedback d30aea0e
```

**输出示例**:
```
🔍 反馈评分:
  • completeness: 0.85
    实验方案涵盖了目标、材料清单、详细步骤...
  • safety: 0.95
  • clarity: 0.90
  • executability: 0.80
  • cost_effectiveness: 0.75

  📊 总分: 0.83
  🤖 评分来源: llm_judge

📚 Playbook更新:

  📦 更新后的Playbook包含 34 条规则

  📑 各部分规则数量:
    • material_selection: 4
    • procedure_design: 11
    • safety_protocols: 7
    • quality_control: 6
    • troubleshooting: 2
    • common_mistakes: 4

  🏷️  规则来源分布:
    • seed: 18
    • reflection: 16

  📊 本次变更统计:
    ✅ 新增: 2 条
    ✏️  修改: 2 条
    ❌ 删除: 0 条
    📝 总计: 4 项变更

  🔄 详细变更:

    ✅ 新增 (2 条):
       [proc-00009] (procedure_design)
       For each step involving specialized tests, provide detailed...
       原因: Ensures detailed and reproducible test methods

       [err-00004] (common_mistakes)
       Not considering cost-effective alternatives for materials...
       原因: Highlights the importance of evaluating alternatives

    ✏️  修改 (2 条):
       [mat-00004]
       新内容: Clearly specify the exact quantity of materials...
       原因: Replaces vague terms with specific quantities

       [safe-00007]
       新内容: Provide detailed safety instructions for chemicals...
       原因: More specific safety instructions for epoxy resin
```

### 场景2: 监控正在运行的任务

```bash
# 终端1: 实时监控状态变化
python scripts/inspect_tasks.py --watch <task_id>

# 终端2: 实时追踪日志输出
python scripts/inspect_tasks.py --log <task_id>
```

### 场景3: 分析playbook进化

```bash
# 步骤1: 查看多个任务的反馈循环
python scripts/inspect_tasks.py --feedback task1
python scripts/inspect_tasks.py --feedback task2
python scripts/inspect_tasks.py --feedback task3

# 步骤2: 对比各任务添加的新规则
# （查看 "🆕 最近更新的规则" 部分）

# 步骤3: 直接查看完整playbook文件
cat data/playbooks/chemistry_playbook.json | jq '.bullets | length'
```

### 场景4: 恢复中断的任务

```bash
# 列出所有可恢复的任务（AWAITING_CONFIRM状态）
python scripts/inspect_tasks.py --resumable

# 交互式恢复任务
python scripts/inspect_tasks.py --resume

# 或直接指定任务ID恢复
python scripts/inspect_tasks.py --resume <task_id>
```

---

## 🔧 查询ACE框架训练循环

如果你需要查询离线训练的ACE循环（非实时生成任务），使用 `query_runs.py`：

```bash
# 列出所有runs
python scripts/analysis/query_runs.py

# 按日期过滤
python scripts/analysis/query_runs.py --date 20251023

# 查询特定run的详情
python scripts/analysis/query_runs.py --run-id 143052_abc123

# 按组件过滤
python scripts/analysis/query_runs.py --component generator --latest 5
```

**注意**: ACE框架的runs记录的是**完整的三角色训练循环**（Generator → Reflector → Curator），而Workflow CLI记录的是**实际生产环境的方案生成**。

---

## 📁 文件位置速查

### Workflow CLI任务
```
logs/generation_tasks/<task_id>/
├── config.json          # 任务配置（会话ID、对话历史）
├── task.json           # ⭐任务状态（包含元数据）
├── requirements.json   # MOSES提取的需求
├── templates.json      # RAG检索的模板
├── plan.json          # 生成的实验方案
├── feedback.json      # ⭐反馈循环评分
├── curation.json      # ⭐Playbook更新记录
└── task.log           # 完整执行日志
```

### ACE框架训练
```
logs/runs/<date>/run_<run_id>/
├── generator.jsonl    # Generator事件流
├── reflector.jsonl    # Reflector事件流
├── curator.jsonl      # Curator事件流
├── performance.json   # 性能统计
└── metadata.json      # 运行元数据
```

---

## 💡 最佳实践

1. **优先使用 `inspect_tasks.py`** 查询Workflow CLI的反馈循环
2. **定期检查反馈评分** 了解方案质量趋势
3. **追踪playbook更新** 观察系统学习进展
4. **保存关键任务ID** 便于后续分析
5. **使用 `--watch` 和 `--log`** 实时监控长时间运行的任务

---

## ❓ FAQ

**Q: 为什么有两个不同的查询脚本？**

A: 因为有两个不同的日志系统：
- `query_runs.py` - 用于ACE框架的离线训练循环
- `inspect_tasks.py` - 用于Workflow CLI的在线生成任务

**Q: 反馈循环数据存储在哪里？**

A: 在 `logs/generation_tasks/<task_id>/feedback.json` 和 `curation.json` 中

**Q: 如何查看playbook是否被更新？**

A: 运行 `python scripts/inspect_tasks.py --feedback <task_id>`，查看 "📚 Playbook更新" 部分。会显示：
- 变更统计（新增/修改/删除的数量）
- 详细变更（具体哪些规则被添加、修改或删除，以及原因）

**Q: 任务状态 `awaiting_confirm` 是什么意思？**

A: 表示任务已提取需求，正在等待用户确认后继续生成方案。使用 `--resume` 命令恢复任务。

**Q: 什么是 delta_operations（增量操作）？**

A: Delta operations 是ACE框架的核心机制，记录了对playbook的每一次变更：
- **ADD**: 新增规则（包含新bullet的完整内容和原因）
- **UPDATE**: 修改现有规则（包含bullet_id、新内容和修改原因）
- **REMOVE**: 删除规则（包含bullet_id和删除原因）

这种增量更新方式避免了整体重写，防止了context collapse（论文§3.1）。

**Q: 如何判断反馈循环是否正常工作？**

A: 检查以下指标：
1. `feedback.json` 中有评分数据（5个维度 + 总分）
2. `curation.json` 中有 `delta_operations` 记录（不为空）
3. 变更统计显示有新增、修改或删除操作
4. 每个操作都有清晰的原因说明

---

## 📚 相关文档

- [RETRY_USAGE_GUIDE.md](./RETRY_USAGE_GUIDE.md) - 任务重试机制
- [FEEDBACK_MODE_STORAGE.md](./FEEDBACK_MODE_STORAGE.md) - 反馈模式配置
- [SESSION_MANAGEMENT.md](./SESSION_MANAGEMENT.md) - 会话管理
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 整体架构设计
