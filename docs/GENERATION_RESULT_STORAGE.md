# GenerationResult 存储说明

## 概述

从现在开始，系统会保存**完整的 GenerationResult**（包含 trajectory 和 relevant_bullets），而不仅仅是 ExperimentPlan。

## 文件结构

### 任务目录：`logs/generation_tasks/<task_id>/`

```
<task_id>/
├── config.json              # 任务配置（会话ID、对话历史）
├── task.json                # 任务状态（持久化）
├── requirements.json        # 提取的需求
├── templates.json           # RAG检索的模板
├── plan.json                # 生成的方案（ExperimentPlan）
├── generation_result.json   # ⭐ 新增：完整的生成结果
└── task.log                 # 完整日志
```

## generation_result.json 结构

```json
{
  "plan": {
    "title": "实验标题",
    "objective": "实验目标",
    "materials": [...],
    "procedure": [...],
    "safety_notes": [...],
    "expected_outcome": "...",
    "quality_control": [...]
  },
  "trajectory": [
    {
      "step_number": 1,
      "thought": "推理过程",
      "action": "采取的决策",
      "observation": "预期结果"
    }
  ],
  "relevant_bullets": [
    "mat-00001",
    "proc-00003",
    "safe-00005"
  ],
  "metadata": {
    "model": "qwen-max",
    "prompt_tokens": 1500,
    "completion_tokens": 2000,
    "total_tokens": 3500,
    "retrieved_bullets_count": 50,
    "retrieved_bullet_ids": [...],
    "templates_retrieved": [...],
    "duration": 81.22
  },
  "timestamp": "2025-10-27T10:41:22.123456"
}
```

## 用途

### 1. Trajectory（推理轨迹）

**给 Reflector 使用**，分析 Generator 的决策过程：

```python
from workflow.task_manager import get_task_manager

task_manager = get_task_manager()
task = task_manager.get_task("task_id")

# 加载完整结果
result = task.load_generation_result()

# 分析 trajectory
for step in result["trajectory"]:
    print(f"Step {step['step_number']}: {step['thought']}")
    # Reflector 可以分析：
    # - 哪个决策导致了错误？
    # - 推理中缺少了什么考虑？
```

### 2. Relevant Bullets（实际使用的 bullets）

**给 Reflector 标记用**，判断哪些 bullets 有帮助：

```python
# Reflector 分析后标记
bullet_tags = {
    "mat-00001": "helpful",   # 这个 bullet 帮助做出正确决策
    "proc-00003": "harmful",  # 这个 bullet 导致了错误
    "safe-00005": "neutral"   # 没有明显影响
}

# Curator 根据标记更新 playbook
```

### 3. Metadata（统计信息）

**用于性能分析和成本计算**：

- Tokens 消耗
- 生成耗时
- 检索到的 bullets 数量
- 使用的模板信息

## 向后兼容

**旧任务**（功能实现前生成的）：
- ✅ `plan.json` 存在
- ❌ `generation_result.json` 不存在

**新任务**（功能实现后生成的）：
- ✅ `plan.json` 存在（向后兼容）
- ✅ `generation_result.json` 存在（完整数据）

## API 使用

### 保存

```python
from workflow.task_manager import GenerationTask

task = GenerationTask(...)

# 生成方案
generation_result = generator.generate(...)

# 保存完整结果
task.save_generation_result(generation_result)

# 向后兼容：同时保存 plan.json
task.save_plan(generation_result.generated_plan)
```

### 加载

```python
from workflow.task_manager import get_task_manager

task_manager = get_task_manager()
task = task_manager.get_task("task_id")

# 加载完整结果
result = task.load_generation_result()

if result:
    plan = result["plan"]
    trajectory = result["trajectory"]
    bullets = result["relevant_bullets"]
    metadata = result["metadata"]
else:
    # 旧任务，只有 plan.json
    plan = task.load_requirements()
```

## 检查工具

使用脚本查看 generation_result：

```bash
# 查看指定任务
python scripts/inspect_generation_result.py <task_id>

# 查看最新任务
python scripts/inspect_generation_result.py --latest
```

## 实现细节

### 修改的文件

1. **src/workflow/task_manager.py**
   - 添加 `generation_result_file` 属性
   - 添加 `save_generation_result()` 方法
   - 添加 `load_generation_result()` 方法
   - 更新 `to_dict()` 添加 `has_generation_result` 字段

2. **src/workflow/task_worker.py**
   - 在生成后调用 `task.save_generation_result()`
   - 添加调试输出显示 trajectory 和 bullets 信息

3. **scripts/inspect_generation_result.py**
   - 新增检查工具

## 未来改进

1. **Reflector 集成**
   - 从 `generation_result.json` 加载数据
   - 分析 trajectory 和标记 bullets

2. **训练数据集**
   - 收集所有 `generation_result.json`
   - 构建 ACE 训练数据集

3. **可视化**
   - 显示 trajectory 的决策流程图
   - 展示 bullets 的使用统计

## 注意事项

⚠️ **重要**：

1. **LLM 必须输出 trajectory**
   - 检查 Generator 的 `SYSTEM_PROMPT`
   - 确保 JSON 输出包含 `reasoning.trajectory` 字段

2. **文件大小**
   - `generation_result.json` 比 `plan.json` 大（包含额外数据）
   - 长时间运行后注意磁盘空间

3. **隐私**
   - Trajectory 包含 LLM 的推理过程
   - 如果敏感，注意数据保护
