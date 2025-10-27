# 反馈循环显示改进说明

## 📝 改进内容

将 `--feedback` 命令的Playbook更新显示从**模糊的"最近5条"**改进为**清晰的变更记录**。

---

## 🔄 对比：改进前 vs 改进后

### ❌ 改进前

```
📚 Playbook更新:
  更新后的Playbook包含 34 条规则

  📑 各部分规则数量:
    • material_selection: 4
    • procedure_design: 11
    • safety_protocols: 7
    ...

  🆕 最近更新的规则 (最多5条):
    [proc-00007] (reflection) For any analytical or testing methods...
    [qc-00006] (reflection) For critical tests, provide detailed...
    [qc-00005] (reflection) For experiments where microstructure...
    [safe-00007] (reflection) When using chemicals like epoxy...
    [mat-00004] (reflection) Clearly specify the exact quantity...
```

**问题**：
- ✅ 有总规则数和section分布（保留）
- ❌ **看不出这次任务具体做了什么变更**
- ❌ "最近5条"是按时间排序，不是按变更类型
- ❌ 无法区分新增、修改还是删除
- ❌ 没有变更原因说明
- ❌ 缺少规则来源统计

---

### ✅ 改进后

```
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

**优势**：
- ✅ **保留了所有统计信息**（总数、section分布、来源分布）
- ✅ **新增了本次变更统计**（新增/修改/删除的数量）
- ✅ **新增了详细变更记录**（按操作类型分组）
- ✅ 显示每个变更的具体原因
- ✅ 能追踪哪些规则被添加、修改或删除
- ✅ 符合ACE框架的delta updates机制
- ✅ 既有宏观统计，又有微观细节

---

## 🎯 技术实现

### 数据来源

改进基于 `curation.json` 中已有的 `delta_operations` 字段：

```json
{
  "bullets_added": 2,
  "bullets_updated": 2,
  "bullets_removed": 0,
  "delta_operations": [
    {
      "operation": "ADD",
      "new_bullet": {
        "id": "proc-00009",
        "section": "procedure_design",
        "content": "For each step involving..."
      },
      "reason": "Ensures detailed and reproducible test methods"
    },
    {
      "operation": "UPDATE",
      "bullet_id": "mat-00004",
      "new_bullet": {
        "content": "Clearly specify the exact quantity..."
      },
      "reason": "Replaces vague terms with specific quantities"
    }
  ]
}
```

### 实现位置

`scripts/inspect_tasks.py` 中的 `show_feedback()` 函数

### 关键代码逻辑

```python
# 获取统计信息
bullets_added = curation.get('bullets_added', 0)
bullets_updated = curation.get('bullets_updated', 0)
bullets_removed = curation.get('bullets_removed', 0)

# 按操作类型分组
delta_operations = curation.get('delta_operations', [])
adds = [op for op in delta_operations if op.get('operation') == 'ADD']
updates = [op for op in delta_operations if op.get('operation') == 'UPDATE']
removes = [op for op in delta_operations if op.get('operation') == 'REMOVE']

# 分别显示每种类型的变更（最多5条）
```

---

## 📋 使用方法

```bash
# 激活conda环境
conda activate OntologyConstruction

# 查看任务的反馈循环和变更记录
python scripts/inspect_tasks.py --feedback <task_id>
```

**示例**：
```bash
# 列出所有任务
python scripts/inspect_tasks.py --list

# 查看最新任务的反馈（假设ID是d30aea0e）
python scripts/inspect_tasks.py --feedback d30aea0e
```

---

## 🔗 相关概念

### Delta Operations（增量操作）

ACE框架的核心机制，来自论文 §3.1：

- **目的**: 防止context collapse（上下文崩溃）
- **方法**: 使用小批量增量更新，而非整体重写
- **操作类型**:
  - `ADD`: 添加新规则
  - `UPDATE`: 修改现有规则
  - `REMOVE`: 删除过时规则

### Curator组件

负责维护和更新playbook的ACE组件：

1. 接收Reflector的insights
2. 生成delta operations
3. 应用增量更新
4. 进行语义去重（cosine similarity > 0.85）
5. 保存完整的更新记录

---

## 🎓 为什么这样改进？

### 用户需求

> "但是我也要这部分：
> - 更新后的规则总数
> - 各section的规则分布
> - 规则来源标记
>
> 我只是让你把最近的五条改为被修改的，请将上述三条内容加回来"

### 核心问题

1. **模糊性**: "最近5条"按时间排序，无法反映本次任务的实际变更
2. **不完整**: 可能错过重要的修改或删除操作
3. **缺乏上下文**: 没有变更原因，难以理解为什么要这样改
4. **统计信息不足**: 缺少规则来源分布

### 解决方案

**保留原有统计 + 增强变更显示**：

1. **保留宏观统计**:
   - ✅ 更新后的规则总数（了解playbook规模）
   - ✅ 各section的规则分布（了解覆盖范围）
   - ✅ 规则来源分布（了解seed vs reflection占比）

2. **增强微观变更**:
   - ✅ 本次变更统计（新增/修改/删除数量）
   - ✅ 详细变更记录（按操作类型分组，附带原因）

3. **数据来源**:
   - 使用 `delta_operations` 字段（ACE框架内置）
   - 按操作类型（ADD/UPDATE/REMOVE）分组
   - 显示每个变更的完整上下文

---

## 📊 实际效果

### 测试任务 d30aea0e

- 新增1条安全规则（紧急响应程序）
- 原因明确：针对反馈评分中safety的改进建议

### 测试任务 5328e7d2

- 新增2条（procedure_design + common_mistakes）
- 修改2条（material_selection + safety_protocols）
- 每条变更都关联到具体的insight

---

## 🚀 后续可能的改进

1. **变更对比**: 对于UPDATE操作，显示修改前后的diff
2. **统计图表**: 可视化展示playbook的进化趋势
3. **变更历史**: 追踪某个bullet的完整修改历史
4. **影响分析**: 分析某个变更对后续生成任务的影响

---

## 📚 相关文档

- [QUERY_LOGS_GUIDE.md](./QUERY_LOGS_GUIDE.md) - 完整的日志查询指南
- [ARCHITECTURE.md](../ARCHITECTURE.md) - ACE框架架构
- 论文 §3.1 - Incremental Delta Updates
- 论文 §3.2 - Grow-and-Refine Mechanism
