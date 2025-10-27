# ACE 反馈训练流程集成总结

## 🎯 实现目标

将ACE框架的反馈训练流程（评估→反思→curate）集成到现有workflow系统中，支持用户对已完成的实验方案进行反馈，从而持续改进playbook。

## ✅ 已完成的功能

### 1. 扩展任务状态（src/workflow/task_manager.py）

**新增4个反馈训练状态**：
```python
class TaskStatus(str, Enum):
    # ... 原有状态 ...

    # 新增：反馈训练状态（ACE循环）
    EVALUATING = "evaluating"               # 评估方案质量
    REFLECTING = "reflecting"               # 反思分析
    CURATING = "curating"                  # 更新playbook
    FEEDBACK_COMPLETED = "feedback_completed"  # 反馈流程完成
```

### 2. 扩展GenerationTask数据结构（src/workflow/task_manager.py）

**新增3个文件属性**：
- `feedback_file` - 评估反馈文件（feedback.json）
- `reflection_file` - 反思结果文件（reflection.json）
- `curation_file` - Playbook更新记录文件（curation.json）

**新增6个方法**：
- `save_feedback()` / `load_feedback()` - 保存/加载评估反馈
- `save_reflection()` / `load_reflection()` - 保存/加载反思结果
- `save_curation()` / `load_curation()` - 保存/加载更新记录

**更新序列化**：
- `to_dict()` 中添加 `has_feedback`、`has_reflection`、`has_curation` 字段

### 3. 实现反馈工作进程（src/workflow/feedback_worker.py）

**核心特性**：
- 独立子进程运行（类似task_worker.py）
- 从`generation_result.json`加载完整数据（plan + trajectory + relevant_bullets）
- 从配置文件读取默认评估模式（`configs/ace_config.yaml`）
- 支持旧任务降级处理（无generation_result.json的情况）

**工作流程**：
```
1. 验证任务状态（必须是COMPLETED）
2. 加载generation_result.json
   - plan: 生成的方案
   - trajectory: 推理轨迹（给Reflector分析）
   - relevant_bullets: 使用的bullets（给Reflector标记）
3. 评估（EVALUATING）
   - 使用auto/llm_judge/human模式
   - 保存feedback.json
4. 反思（REFLECTING）
   - 分析trajectory，提取insights
   - 标记helpful/harmful/neutral bullets
   - 保存reflection.json
5. 更新Playbook（CURATING）
   - 增删改bullets
   - 保存curation.json
6. 完成（FEEDBACK_COMPLETED）
```

**命令行参数**：
```bash
python -m workflow.feedback_worker <task_id>
python -m workflow.feedback_worker <task_id> --mode auto
python -m workflow.feedback_worker <task_id> --mode llm_judge
```

### 4. 扩展TaskScheduler（src/workflow/task_scheduler.py）

**新增方法**：
```python
def submit_feedback_task(
    self,
    task_id: str,
    evaluation_mode: Optional[str] = None
) -> bool:
    """提交反馈训练任务（启动独立子进程）

    Args:
        task_id: 已完成的任务ID
        evaluation_mode: 评估模式（可选，默认从配置读取）

    Returns:
        是否成功启动
    """
```

**功能**：
- 验证任务存在且已完成（TaskStatus.COMPLETED）
- 启动feedback_worker子进程
- 复用日志缓冲区（追加日志）
- 支持指定评估模式或使用配置默认值

### 5. 扩展CLI命令（examples/workflow_cli.py）

#### 新增 `/feedback` 命令
```bash
/feedback <task_id>                  # 使用配置默认模式
/feedback <task_id> --mode auto      # 指定auto模式
/feedback <task_id> --mode llm_judge # 指定llm_judge模式
```

**功能**：
- 显示评估模式说明和配置默认值
- 参数验证和错误提示
- 提交反馈任务到TaskScheduler
- 显示实时状态和日志提示

#### 更新 `/help` 命令
- 添加 `/feedback` 命令说明
- 更新工作流程（添加反馈训练步骤）
- 更新示例对话

#### 更新 `/status` 命令
**新增状态图标**：
- 📊 EVALUATING - 评估方案质量
- 💭 REFLECTING - 反思分析
- 📝 CURATING - 更新playbook
- 🎓 FEEDBACK_COMPLETED - 反馈流程完成

**新增文件显示**：
- ✅ 评估反馈: feedback.json
- ✅ 反思结果: reflection.json
- ✅ 更新记录: curation.json

**新增状态提示**：
- COMPLETED状态：提示可使用`/feedback`进行反馈训练
- FEEDBACK_COMPLETED状态：显示Playbook更新统计和查看结果的命令

## 📊 数据流图

### 完整ACE流程
```
用户对话
    ↓
/generate → task_worker子进程
    ↓
COMPLETED (保存generation_result.json)
    ↓
/feedback → feedback_worker子进程
    ↓
├─ EVALUATING (生成feedback.json)
│   ├─ auto: 规则评估（快速免费）
│   ├─ llm_judge: LLM评估（准确但耗tokens）
│   └─ human: 人工评分（占位符）
├─ REFLECTING (生成reflection.json)
│   ├─ 分析trajectory推理过程
│   ├─ 提取insights
│   └─ 标记helpful/harmful bullets
├─ CURATING (生成curation.json)
│   ├─ 新增bullets
│   ├─ 删除harmful bullets
│   └─ 更新现有bullets
└─ FEEDBACK_COMPLETED
    ↓
下次生成时使用更新后的playbook
```

### 任务目录结构
```
logs/generation_tasks/<task_id>/
├── config.json              # 任务配置
├── task.json                # 任务状态
├── requirements.json        # 提取的需求
├── templates.json           # RAG检索结果
├── plan.json                # 生成的方案（向后兼容）
├── generation_result.json   # 完整生成结果（⭐包含trajectory和bullets）
├── feedback.json            # ⭐新增：评估反馈
├── reflection.json          # ⭐新增：反思结果
├── curation.json            # ⭐新增：Playbook更新记录
└── task.log                 # 完整日志
```

## 🎮 使用示例

### 完整工作流
```bash
# 1. 生成方案
你: 我想合成阿司匹林
助手: 好的，请告诉我更多细节...
你: /generate
[方案生成完成]

# 2. 查看方案
你: /view abc123
[显示格式化方案]

# 3. 反馈训练（使用配置默认模式）
你: /feedback abc123
🚀 启动反馈训练流程（使用配置默认: llm_judge）

# 4. 查看实时日志
你: /logs abc123
[Worker] 使用配置的评估模式: llm_judge
[Worker] 加载完整 GenerationResult:
  - Trajectory 步骤: 8
  - Relevant bullets: 12
STEP 1: 评估方案质量
✅ 评估完成: 0.87
STEP 2: 反思分析
✅ 提取了 5 个 insights
✅ 标记了 12 个 bullets
STEP 3: 更新 Playbook
✅ Playbook已更新: +3 -1 ~2

# 5. 查看最终状态
你: /status abc123
任务状态: 🎓 FEEDBACK_COMPLETED
📊 Playbook 更新:
  新增: 3 bullets
  删除: 1 bullets
  更新: 2 bullets
```

### 指定评估模式
```bash
# 使用auto模式（快速免费）
你: /feedback abc123 --mode auto

# 使用llm_judge模式（准确但消耗tokens）
你: /feedback abc123 --mode llm_judge

# 查看默认模式
你: /feedback
💡 默认模式（configs/ace_config.yaml）: llm_judge
```

## 🔧 配置说明

### configs/ace_config.yaml
```yaml
ace:
  training:
    feedback_source: "llm_judge"  # 默认评估模式
    # "auto": 快速规则评估
    # "llm_judge": LLM评估（消耗tokens）
    # "human": 人工评分（待实现）
```

**重要**：feedback_worker会优先使用命令行指定的模式，如果未指定则从配置读取。

## ✨ 关键设计决策

### 1. 默认模式从配置读取（而非硬编码）
**原因**：灵活性。用户可根据需求在配置文件中设置默认模式，无需修改代码。

**实现**：
```python
from utils.config_loader import get_ace_config

if evaluation_mode is None:
    ace_config = get_ace_config()
    evaluation_mode = ace_config.training.feedback_source
```

### 2. 从generation_result.json加载完整数据
**原因**：
- `trajectory`：Reflector需要分析推理过程，找出错误根源
- `relevant_bullets`：Reflector需要标记哪些bullets有帮助/有害

**实现**：
```python
generation_result_data = task.load_generation_result()

if generation_result_data:
    plan = ExperimentPlan(**generation_result_data["plan"])
    trajectory = [TrajectoryStep(**step) for step in generation_result_data["trajectory"]]
    relevant_bullets = generation_result_data["relevant_bullets"]
else:
    # 旧任务降级处理
    plan = load_from_plan_json()
    trajectory = []
    relevant_bullets = []
```

### 3. 独立子进程架构
**原因**：
- 与生成流程保持一致的架构
- 反馈训练可能耗时较长（LLM调用）
- 隔离print输出，不干扰CLI交互

**实现**：
- `feedback_worker.py` 作为独立模块运行
- `TaskScheduler.submit_feedback_task()` 启动子进程
- 日志通过管道捕获到缓冲区

### 4. 向后兼容旧任务
**原因**：旧任务可能没有`generation_result.json`（功能实现前生成的）

**实现**：
```python
if not generation_result_data:
    # 降级处理：只加载plan，trajectory和bullets为空
    # 反馈功能将受限，但不会失败
```

## 📝 修改的文件清单

1. **src/workflow/task_manager.py**
   - 添加4个新状态
   - 添加3个文件属性
   - 添加6个保存/加载方法
   - 更新to_dict()

2. **src/workflow/feedback_worker.py**
   - 新建文件
   - 实现完整反馈工作流
   - 支持命令行参数

3. **src/workflow/task_scheduler.py**
   - 添加submit_feedback_task()方法

4. **examples/workflow_cli.py**
   - 添加/feedback命令处理
   - 更新/help命令
   - 更新/status命令（图标+文件+提示）

## 🚀 下一步

现在所有功能已实现，可以进行测试：

1. **启动CLI测试**：
```bash
conda activate OntologyConstruction
python examples/workflow_cli.py
```

2. **测试完整流程**：
```bash
# 生成方案
你: 我想合成阿司匹林
你: /generate
你: /confirm

# 反馈训练
你: /feedback <task_id>
你: /logs <task_id>
你: /status <task_id>
```

3. **检查生成的文件**：
```bash
# 查看任务目录
ls -la logs/generation_tasks/<task_id>/

# 查看反馈文件
cat logs/generation_tasks/<task_id>/feedback.json
cat logs/generation_tasks/<task_id>/reflection.json
cat logs/generation_tasks/<task_id>/curation.json
```

## 🎉 总结

**已实现**：
- ✅ 完整的ACE反馈训练流程（评估→反思→curate）
- ✅ 从generation_result.json加载完整数据
- ✅ 从配置文件读取默认评估模式
- ✅ 独立子进程架构
- ✅ CLI命令和帮助文档
- ✅ 向后兼容旧任务

**关键特性**：
- 🚀 后台执行，不阻塞CLI
- 📊 实时日志查看
- 🎯 灵活的评估模式（auto/llm_judge/human）
- 🔄 持续改进playbook
- 📝 完整的数据追踪

系统现在支持完整的ACE循环，用户可以通过反馈训练持续改进playbook，从而提升未来生成方案的质量！
