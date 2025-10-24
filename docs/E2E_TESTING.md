# 端到端测试指南

## 系统状态总结

### ✅ 已完整实现的组件

1. **Chatbot对话系统** - 基于LangGraph + MOSES本体
2. **后台任务管理** - 持久化、工作线程、文件锁
3. **斜杠命令系统** - 10个命令
4. **需求提取** - LLM自动分析
5. **Mock RAG检索** - 关键词匹配 ⭐ NEW
6. **Generator生成** - ACE框架
7. **主动提醒机制** - AWAITING_CONFIRM自动提示
8. **独立检查工具** - 多终端监控

### 🔄 使用Mock数据的组件

- **RAG模板检索** - 使用 `data/mock/dss_templates.json`（8个DSS实验模板）

## 端到端测试流程

### 前提条件

```bash
# 1. 确保环境配置
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置API Key
cp .env.example .env
# 编辑.env，填写DASHSCOPE_API_KEY

# 3. 确保目录存在
mkdir -p data/playbooks logs/generation_tasks

# 4. 确保playbook存在
# 如果没有，运行一次 examples/run_simple_ace.py 创建初始playbook
```

### 完整测试脚本

#### 测试1：基础工作流（DSS热处理实验）

```bash
# 终端1：启动主CLI
python examples/workflow_cli.py

# 以下是交互过程
```

**对话脚本**：
```
👤 你: /help
[查看帮助信息]

👤 你: 我想做DSS 2205的固溶处理实验

🤖 助手: [MOSES查询DSS 2205相关信息...]
        双相不锈钢DSS 2205是一种铁素体-奥氏体双相不锈钢...

👤 你: 温度范围1050-1080度，需要水淬

🤖 助手: 明白了。还需要确认：
        - 试样尺寸和数量？
        - 保温时间要求？
        - 是否需要后续检测？

👤 你: 试样10mm厚，保温10分钟，需要做金相分析

🤖 助手: 好的，信息已收集。你可以使用 /generate 生成详细方案。

👤 你: /generate

🚀 已提交生成任务（后台执行）
   任务ID: abc12345
   使用 /status 查看进度
   日志: logs/generation_tasks/abc12345/task.log

[等待5-10秒，系统提取需求]

======================================================================
⏸️  任务需要确认！
======================================================================
  任务ID: abc12345
  状态: awaiting_confirm

📋 需求已提取，文件路径:
  logs/generation_tasks/abc12345/requirements.json

💡 接下来可以:
  1. 查看需求: cat logs/generation_tasks/abc12345/requirements.json
  2. 修改需求: nano logs/generation_tasks/abc12345/requirements.json
  3. 确认继续: /confirm
  4. 取消任务: /cancel
======================================================================

👤 你: /status

任务状态: ⏸️  AWAITING_CONFIRM
======================================================================
  任务ID: abc12345
  ...

📁 数据文件:
  ✅ 需求: logs/generation_tasks/abc12345/requirements.json

💡 操作提示:
  # 查看需求
  cat logs/generation_tasks/abc12345/requirements.json

  # 确认继续
  /confirm

👤 你: /confirm

✅ 已确认需求，任务继续执行...

[等待10-20秒，系统RAG检索 + Generator生成]

👤 你: /status

任务状态: ✅ COMPLETED
======================================================================
  任务ID: abc12345
  ...

✅ 任务完成!
  耗时: 15.32s
  Tokens: 4253

💡 查看方案:
  cat logs/generation_tasks/abc12345/plan.json
  /view abc12345

👤 你: /view abc12345

======================================================================
  DSS 2205双相不锈钢固溶处理实验方案
======================================================================

## 📋 实验目标
对DSS 2205双相不锈钢进行固溶处理，优化两相组织平衡...

[完整方案输出]

👤 你: 保温时间可以延长到15分钟吗？

🤖 助手: 可以的。对于10mm厚的试样，延长到15分钟更保险...

👤 你: /quit

👋 再见！（任务会继续在后台运行）
```

#### 测试2：多终端监控

```bash
# 终端1：运行主CLI（如上）

# 终端2：独立监控
python scripts/inspect_tasks.py --list

所有任务列表
======================================================================
  ✅ abc12345 (completed)
     会话: cli_session
     时间: 2025-10-24 15:30:00
     目录: logs/generation_tasks/abc12345
     方案: DSS 2205双相不锈钢固溶处理实验方案

# 查看任务详情
python scripts/inspect_tasks.py --task abc12345

# 查看需求
python scripts/inspect_tasks.py --requirements abc12345

📋 需求文件: logs/generation_tasks/abc12345/requirements.json
======================================================================
{
  "target_compound": "DSS 2205",
  "objective": "固溶处理优化两相组织",
  "constraints": [
    "温度1050-1080度",
    "水淬冷却",
    "保温10分钟"
  ],
  "special_requirements": "需要金相分析"
}

# 查看方案
python scripts/inspect_tasks.py --plan abc12345

# 查看日志
python scripts/inspect_tasks.py --log abc12345 --no-follow
```

#### 测试3：需求修改流程

```bash
# 终端1：主CLI
👤 你: 我要测试DSS的腐蚀性能

🤖 助手: 好的，请问具体是哪种腐蚀测试？

👤 你: 点腐蚀测试，ASTM G61标准

👤 你: /generate
[任务提交: def45678]

[等待提醒]
⏸️  任务需要确认！
...

# 终端2：查看并修改需求
cat logs/generation_tasks/def45678/requirements.json

{
  "objective": "DSS点腐蚀测试",
  "constraints": ["ASTM G61标准"],
  ...
}

# 手动添加更多约束
vim logs/generation_tasks/def45678/requirements.json

{
  "objective": "DSS点腐蚀测试",
  "constraints": [
    "ASTM G61标准",
    "6% FeCl3溶液",        # 添加
    "温度范围20-60度",      # 添加
    "平行样品3个"           # 添加
  ],
  ...
}

# 保存后回到终端1
👤 你: /confirm
✅ 已确认需求，任务继续执行...

[系统会使用修改后的需求继续生成]
```

#### 测试4：CLI退出后任务继续

```bash
# 终端1
👤 你: /generate
[任务提交: ghi78901]

[在EXTRACTING状态时按Ctrl+C]
^C
👋 程序被中断，正在退出...
   任务会继续在后台运行

# 终端2：验证任务仍在运行
python scripts/inspect_tasks.py --watch ghi78901

👀 实时监控任务 ghi78901 (Ctrl+C 退出)

[14:35:10] 状态变更: extracting
[14:35:15] 状态变更: awaiting_confirm

# 重新启动CLI
python examples/workflow_cli.py

[TaskManager] Worker已在其他进程运行，跳过启动

👤 你: /status
任务状态: ⏸️  AWAITING_CONFIRM
...

👤 你: /confirm
[继续完成任务]
```

### 验证Mock RAG是否工作

查看任务日志：
```bash
cat logs/generation_tasks/<task_id>/task.log

# 应该看到：
[HH:MM:SS] STEP 3: RAG检索模板
[HH:MM:SS] [MockRAG] 加载了 8 个模板
[HH:MM:SS] [MockRAG] 提取关键词: ['固溶处理', 'dss 2205', ...]
[HH:MM:SS] [MockRAG] 检索到 3 个相关模板:
[HH:MM:SS]   1. DSS 2205双相不锈钢固溶处理工艺
[HH:MM:SS]   2. DSS显微组织金相分析
[HH:MM:SS]   3. DSS热变形实验（Gleeble模拟）
[HH:MM:SS] 检索到 3 个模板（使用Mock RAG）
```

查看检索结果：
```bash
cat logs/generation_tasks/<task_id>/templates.json

# 应该包含3个完整的模板数据
```

## Mock RAG测试用例

### 用例1：固溶处理

**输入需求**：
```json
{
  "objective": "DSS 2205固溶处理",
  "target_compound": "DSS 2205"
}
```

**预期匹配模板**：
- DSS 2205双相不锈钢固溶处理工艺（高分）
- DSS热变形实验（中分）
- DSS显微组织金相分析（低分）

### 用例2：腐蚀测试

**输入需求**：
```json
{
  "objective": "点腐蚀测试",
  "constraints": ["ASTM G61"]
}
```

**预期匹配模板**：
- DSS点腐蚀电位测试（ASTM G61）（高分）
- DSS应力腐蚀开裂测试（中分）
- DSS晶间腐蚀敏感性评价（中分）

### 用例3：金相分析

**输入需求**：
```json
{
  "objective": "金相分析",
  "special_requirements": "相比例测量"
}
```

**预期匹配模板**：
- DSS显微组织金相分析（高分）
- DSS 2205双相不锈钢固溶处理工艺（低分）

## 预期输出文件结构

```
logs/generation_tasks/<task_id>/
├── task.json
│   {
│     "task_id": "abc12345",
│     "status": "completed",
│     "has_requirements": true,
│     "has_templates": true,
│     "has_plan": true,
│     ...
│   }
│
├── requirements.json
│   {
│     "target_compound": "DSS 2205",
│     "objective": "固溶处理优化两相组织",
│     "constraints": [...],
│     ...
│   }
│
├── templates.json
│   [
│     {
│       "title": "DSS 2205双相不锈钢固溶处理工艺",
│       "procedure_summary": "...",
│       "key_points": [...],
│       ...
│     },
│     {...},
│     {...}
│   ]
│
├── plan.json
│   {
│     "title": "DSS 2205双相不锈钢固溶处理实验方案",
│     "objective": "...",
│     "materials": [...],
│     "procedure": [...],
│     "safety_notes": [...],
│     ...
│   }
│
└── task.log
    [14:30:00] Task abc12345 started
    [14:30:01] STEP 1: 提取需求
    ...
    [14:30:25] Task abc12345 finished
```

## 故障排查

### Mock RAG未工作

**症状**：日志显示 "检索到 0 个模板"

**排查**：
```bash
# 1. 检查mock文件是否存在
ls -l data/mock/dss_templates.json

# 2. 检查日志中的错误信息
cat logs/generation_tasks/<task_id>/task.log | grep "Mock RAG"

# 3. 手动测试mock_rag
python
>>> from workflow.mock_rag import create_mock_rag_retriever
>>> rag = create_mock_rag_retriever()
>>> templates = rag.retrieve({"objective": "固溶处理"})
>>> len(templates)
3
```

### Generator使用了空模板

**症状**：生成的方案没有参考模板内容

**原因**：这是正常的！Generator会：
1. 优先使用playbook bullets（ACE框架）
2. 参考templates作为辅助
3. 即使templates为空也能生成

**验证**：查看生成的方案是否合理，是否使用了playbook指导

## 下一步：真实RAG实现

Mock RAG验证通过后，可以实现真实RAG：

1. **选择向量数据库**：Chroma / Faiss / Milvus
2. **实现文档处理**：切分、嵌入、索引
3. **实现检索逻辑**：语义搜索 + 重排序
4. **替换mock_rag**：在command_handler.py中替换导入

参考配置文件：`configs/rag_config.yaml`（已存在）

## 总结

✅ **系统已完全可用**，除了RAG使用Mock数据外，所有组件都是真实实现

✅ **可以端到端测试**，从对话到生成完整流程

✅ **Mock数据充足**，8个DSS实验模板覆盖主要场景

✅ **易于替换**，真实RAG实现后只需修改一行导入即可

**开始测试吧！** 🚀
