# Chatbot CLI 辅助工具完整调研报告

**生成时间**: 2025-10-28
**调研范围**: `scripts/` 目录下所有脚本
**分类标准**: 按功能分为CLI辅助工具、ACE分析工具、测试工具、调试工具

---

## 目录

1. [CLI辅助工具（核心）](#1-cli辅助工具核心)
2. [ACE框架分析工具](#2-ace框架分析工具)
3. [测试工具](#3-测试工具)
4. [调试工具](#4-调试工具)
5. [其他辅助脚本](#5-其他辅助脚本)
6. [使用建议](#6-使用建议)

---

## 1. CLI辅助工具（核心）

这些工具是 **chatbot CLI** (`examples/workflow_cli.py`) 的重要辅助脚本，用于在新终端中独立运行，帮助用户管理任务、查看日志和操作playbook。

### 1.1 `inspect_tasks.py` - **核心任务管理工具** ⭐

**用途**: 独立任务检查和管理工具，可在新终端中运行，实现对后台任务的全方位管理。

**核心功能**:

#### A. 任务管理功能
```bash
# 列出所有任务
python scripts/inspect_tasks.py --list

# 查看任务详情
python scripts/inspect_tasks.py --task <task_id>

# 实时监控任务
python scripts/inspect_tasks.py --watch <task_id>

# 查看任务日志（实时追踪）
python scripts/inspect_tasks.py --log <task_id>

# 查看提取的需求
python scripts/inspect_tasks.py --requirements <task_id>

# 查看生成的方案
python scripts/inspect_tasks.py --plan <task_id>

# 查看反馈循环数据（评分 + Playbook更新）
python scripts/inspect_tasks.py --feedback <task_id>
```

#### B. 任务恢复功能
```bash
# 列出可恢复的任务（AWAITING_CONFIRM状态）
python scripts/inspect_tasks.py --resumable

# 交互式恢复任务
python scripts/inspect_tasks.py --resume

# 恢复指定任务
python scripts/inspect_tasks.py --resume <task_id>
```

#### C. Playbook管理功能
```bash
# 统计当前playbook信息
python scripts/inspect_tasks.py --playbook-stats

# 显示完整playbook内容
python scripts/inspect_tasks.py --playbook-stats --full

# 列出所有playbook快照
python scripts/inspect_tasks.py --list-snapshots

# 统计指定快照信息
python scripts/inspect_tasks.py --snapshot v001

# 显示快照完整内容
python scripts/inspect_tasks.py --snapshot v001 --full
```

**技术特点**:
- 使用 `TaskManager` API 访问任务状态
- 支持实时监控（`tail -f` 效果）
- 提供详细的playbook变更统计（新增/修改/删除）
- 展示反馈评分和策展更新
- 完全独立于CLI主进程运行

**典型使用场景**:
1. **后台任务监控**: CLI运行 `/generate` 后，在新终端用 `--watch` 实时监控
2. **任务恢复**: CLI断开后，使用 `--resumable` 查看待恢复任务
3. **Playbook版本管理**: 查看不同版本的playbook快照，分析学习进度

---

### 1.2 `inspect_generation_result.py` - **生成结果检查工具**

**用途**: 检查 `generation_result.json` 的内容，验证Generator输出的完整性。

**功能**:
```bash
# 检查指定任务的生成结果
python scripts/inspect_generation_result.py <task_id>

# 检查最新已完成任务的结果
python scripts/inspect_generation_result.py --latest
```

**输出信息**:
- Plan信息（标题、材料数、步骤数）
- Trajectory信息（推理步骤数、前3步预览）
- Relevant bullets（使用的playbook bullet IDs）
- Metadata（模型、tokens、耗时、检索的bullets数量）

**使用场景**:
- 验证Generator是否正确生成trajectory
- 检查playbook bullets的使用情况
- 分析生成质量和性能

---

### 1.3 `test_session_helpers.py` - **会话管理辅助函数测试**

**用途**: 快速测试会话ID生成函数（不需要LLM调用）。

**测试内容**:
1. 自定义名称会话ID
2. 自动生成会话ID（格式：`YYYYMMDD_HHMM_<uuid>`）
3. 唯一性检查

**使用场景**:
- 验证会话ID生成逻辑
- 确保会话ID格式正确

---

### 1.4 `test_cli_workflow.py` - **CLI工作流自动化测试**

**用途**: 模拟用户交互，自动化测试CLI工作流。

**测试步骤**:
1. CLI启动干净（无debug输出）
2. 聊天功能正常
3. `/generate` 启动子进程
4. `/logs` 显示业务日志
5. 退出

**使用场景**:
- CI/CD集成测试
- 验证CLI重构后的功能完整性

---

## 2. ACE框架分析工具

这些工具用于分析ACE框架（Generator-Reflector-Curator）的运行数据，帮助开发者优化性能和追踪playbook演化。

### 2.1 `scripts/analysis/query_runs.py` - **查询运行记录**

**用途**: 查询和过滤ACE框架的运行记录。

**功能**:
```bash
# 列出所有runs
python scripts/analysis/query_runs.py

# 查询特定日期的runs
python scripts/analysis/query_runs.py --date 20251022

# 查询特定run的详细信息
python scripts/analysis/query_runs.py --run-id 143052_abc123

# 查询特定组件的runs
python scripts/analysis/query_runs.py --component generator

# 显示最近5次运行
python scripts/analysis/query_runs.py --latest 5

# 显示详细JSON输出
python scripts/analysis/query_runs.py --details
```

**输出信息**:
- Run ID
- 日期
- 包含的组件（Generator/Reflector/Curator）
- 总耗时
- LLM调用次数

---

### 2.2 `scripts/analysis/analyze_performance.py` - **性能分析工具**

**用途**: 分析ACE框架的性能指标。

**功能**:
```bash
# 分析特定run的性能
python scripts/analysis/analyze_performance.py --run-id 143052_abc123

# 分析特定日期的所有runs
python scripts/analysis/analyze_performance.py --date 20251022

# 比较多个runs的性能
python scripts/analysis/analyze_performance.py --date 20251022 --compare

# 识别性能瓶颈（默认top 5）
python scripts/analysis/analyze_performance.py --bottlenecks

# 分析LLM调用效率
python scripts/analysis/analyze_performance.py --llm-efficiency
```

**分析维度**:
- **时间分解**: 各组件和操作的耗时统计
- **LLM统计**: 调用次数、token使用、平均耗时
- **瓶颈识别**: 最耗时的操作（跨多个runs聚合）
- **效率分析**: tokens/秒、平均调用时长

---

### 2.3 `scripts/analysis/view_ace_learning.py` - **ACE学习内容观测**

**用途**: 深度观测ACE学习内容，展示playbook变更和学到的知识。

**功能**:
```bash
# 查看ACE学习内容
python scripts/analysis/view_ace_learning.py --run-id 203038_ID1FWJ

# 显示完整bullet内容
python scripts/analysis/view_ace_learning.py --run-id 203038_ID1FWJ --show-content

# 查看LLM prompts
python scripts/analysis/view_ace_learning.py --run-id 203038_ID1FWJ --show-prompts

# 只看特定组件的prompts
python scripts/analysis/view_ace_learning.py --run-id 203038_ID1FWJ --show-prompts --component curator
```

**展示内容**:
- Reflector发现的insights
- Curator对playbook的更新（新增/修改/删除）
- Playbook更新前后对比
- LLM prompts和responses（可选）

---

### 2.4 `scripts/analysis/analyze_playbook_evolution.py` - **Playbook进化分析**

**用途**: 追踪Playbook随时间的演化。

**功能**:
```bash
# 列出所有playbook版本
python scripts/analysis/analyze_playbook_evolution.py --list-versions

# 比较两个版本
python scripts/analysis/analyze_playbook_evolution.py --compare v1 v2

# 显示增长统计
python scripts/analysis/analyze_playbook_evolution.py --growth-stats

# 追踪特定bullet的演化
python scripts/analysis/analyze_playbook_evolution.py --track-bullet mat-00001
```

**分析维度**:
- **版本列表**: 所有playbook快照及其元数据
- **版本比较**: 识别新增、删除、修改的bullets
- **增长统计**: playbook规模变化、分区分布、质量指标
- **Bullet追踪**: 单个bullet在各版本中的变化历史

---

### 2.5 `scripts/analysis/query_llm_calls.py` - **查询LLM调用**（未读取，从README推断）

**用途**: 查询和分析所有LLM API调用。

**功能**（推断）:
```bash
# 列出所有LLM调用
python scripts/analysis/query_llm_calls.py

# 查询特定日期的LLM调用
python scripts/analysis/query_llm_calls.py --date 20251022

# 导出特定调用的prompts到文件
python scripts/analysis/query_llm_calls.py --export-prompt 143052_abc123_generator --output prompt.txt

# 分析token使用情况
python scripts/analysis/query_llm_calls.py --analyze-tokens
```

---

## 3. 测试工具

这些工具用于测试系统各个组件的功能。

### 3.1 `scripts/test/test_chatbot_basic.py` - **Chatbot基本功能测试**

**用途**: 测试Chatbot的基本功能（不调用MOSES）。

**测试内容**:
1. 配置加载
2. Chatbot初始化
3. 简单对话（不调用MOSES工具）

**使用场景**:
- 快速验证Chatbot配置正确性
- 测试LLM连接

---

### 3.2 `scripts/test/test_moses_llm.py` - **MOSES LLM配置测试**

**用途**: 验证MOSES的Qwen模型调用。

**测试步骤**:
1. 检查API密钥配置
2. 加载MOSES配置
3. 初始化LLM
4. 测试简单LLM调用
5. 测试结构化输出（ToolPlan schema）

**使用场景**:
- 排查MOSES集成问题
- 验证Qwen模型配置

---

### 3.3 `scripts/test_session_management.py` - **会话管理功能测试**

**用途**: 测试会话管理的内存模式和SQLite模式。

**测试场景**:
1. 内存模式 - 基本功能
2. SQLite模式 - 持久化和恢复

**使试内容**:
- 多会话管理
- 历史获取
- 会话列表
- 持久化恢复

---

### 3.4 其他测试脚本（未详细读取）

**文件列表**:
- `test_thinking_stream.py` - 测试思考流
- `test_background_init.py` - 测试后台初始化
- `verify_bullet_tags_fix.py` - 验证bullet tags修复
- `verify_schema_fix.py` - 验证schema修复
- `quick_verify_schema.py` - 快速验证schema
- `test_toolplanner_fix.py` - 测试toolplanner修复
- `test_sqlite_*.py` - SQLite相关测试

---

## 4. 调试工具

这些工具用于调试特定的bug和问题。

### 4.1 `scripts/debug/check_bullet_tags_issue.py` - **调试bullet tags问题**

**用途**: 分析bullet tags格式错误问题。

**分析内容**:
1. Generator返回的bullets_used
2. Reflector收到的参数
3. Reflector返回的bullet_tags
4. Curator实际更新的bullets

**发现的问题**:
- LLM把insight的type字段值误用为bullet_tags的key
- Prompt中没有明确强调bullet_tags必须使用bullet ID作为key

**修复建议**:
1. 在Reflector prompt中更明确地要求使用bullet ID
2. 在prompt中列出所有bullet IDs的列表
3. 在Reflector解析时检测错误格式

---

### 4.2 `scripts/debug_session_b4d838.py` - **调试特定会话**

**用途**: 调试会话 `20251027_1156_b4d838` 的对话历史。

**功能**:
- 读取会话历史
- 格式化展示每条消息

---

### 4.3 其他调试脚本（未详细读取）

**文件列表**:
- `debug_toolplan.py` - 调试toolplan
- `diagnose_qwen_structured_output.py` - 诊断Qwen结构化输出
- `diagnose_moses_toolplan_issue.py` - 诊断MOSES toolplan问题
- `debug_metadata.py` - 调试元数据

---

## 5. 其他辅助脚本

这些脚本用于特定的功能验证和测试。

**文件列表**:
- `test_datetime_serialization.py` - 测试datetime序列化
- `test_retry_mechanism.py` - 测试重试机制
- `test_curation_embedding_fix.py` - 测试策展嵌入修复
- `test_embedding_cache.py` - 测试嵌入缓存
- `test_add_operation_fix.py` - 测试ADD操作修复

---

## 6. 使用建议

### 6.1 Chatbot CLI用户的核心工具

如果你是 **Chatbot CLI 的用户**，以下是最重要的辅助工具：

#### ⭐ 必备工具

1. **`inspect_tasks.py`** - 任务管理的瑞士军刀
   ```bash
   # 在新终端监控后台任务
   python scripts/inspect_tasks.py --watch <task_id>

   # 查看可恢复的任务
   python scripts/inspect_tasks.py --resumable

   # 查看playbook统计
   python scripts/inspect_tasks.py --playbook-stats
   ```

2. **`inspect_generation_result.py`** - 验证生成质量
   ```bash
   # 检查最新生成的方案
   python scripts/inspect_generation_result.py --latest
   ```

#### 💡 推荐使用场景

**场景1: 启动生成后在新终端监控**
```bash
# Terminal 1 - CLI
用户: /generate
系统: 🚀 已启动任务 abc123

# Terminal 2 - 监控
python scripts/inspect_tasks.py --watch abc123
# 或实时查看日志
python scripts/inspect_tasks.py --log abc123
```

**场景2: CLI断开后恢复任务**
```bash
# 查看可恢复的任务
python scripts/inspect_tasks.py --resumable

# 恢复任务
python scripts/inspect_tasks.py --resume abc123
```

**场景3: 分析Playbook学习效果**
```bash
# 统计当前playbook
python scripts/inspect_tasks.py --playbook-stats

# 列出所有快照
python scripts/inspect_tasks.py --list-snapshots

# 比较两个版本
python scripts/inspect_tasks.py --snapshot v001
python scripts/inspect_tasks.py --snapshot v002
```

---

### 6.2 开发者的分析工具

如果你是 **系统开发者**，以下工具用于性能优化和bug排查：

#### ACE框架分析
```bash
# 查看最近的runs
python scripts/analysis/query_runs.py --latest 10

# 分析性能瓶颈
python scripts/analysis/analyze_performance.py --bottlenecks --top 10

# 查看ACE学习内容
python scripts/analysis/view_ace_learning.py --run-id <run_id> --show-prompts

# 分析playbook增长趋势
python scripts/analysis/analyze_playbook_evolution.py --growth-stats
```

#### 测试和调试
```bash
# 测试Chatbot基本功能
python scripts/test/test_chatbot_basic.py

# 测试MOSES LLM配置
python scripts/test/test_moses_llm.py

# 自动化测试CLI工作流
python scripts/test_cli_workflow.py
```

---

### 6.3 脚本分类总结

| 分类 | 用户类型 | 核心脚本 | 用途 |
|------|---------|---------|------|
| **CLI辅助** | CLI用户 | `inspect_tasks.py` | 任务管理、playbook查看 |
| | | `inspect_generation_result.py` | 验证生成质量 |
| **ACE分析** | 开发者 | `query_runs.py` | 查询运行记录 |
| | | `analyze_performance.py` | 性能分析 |
| | | `view_ace_learning.py` | 查看学习内容 |
| | | `analyze_playbook_evolution.py` | Playbook进化 |
| **测试工具** | 开发者 | `test_chatbot_basic.py` | Chatbot功能测试 |
| | | `test_moses_llm.py` | MOSES配置测试 |
| | | `test_cli_workflow.py` | CLI工作流测试 |
| **调试工具** | 开发者 | `check_bullet_tags_issue.py` | 调试bullet tags |
| | | `debug_session_*.py` | 调试特定会话 |

---

### 6.4 与CLI的集成方式

当前架构中，这些脚本与 `workflow_cli.py` 的关系：

```
┌─────────────────────────────────────────────────────────┐
│  用户终端1: workflow_cli.py                              │
│  - 聊天交互                                              │
│  - /generate 启动任务                                    │
│  - /logs 查看实时日志                                    │
└─────────────────────────────────────────────────────────┘
                    │
                    │ 启动子进程
                    ↓
┌─────────────────────────────────────────────────────────┐
│  后台子进程: task_worker.py                             │
│  - 独立运行，不阻塞CLI                                   │
│  - 状态写入文件系统                                      │
└─────────────────────────────────────────────────────────┘
                    │
                    │ 文件系统共享状态
                    ↓
┌─────────────────────────────────────────────────────────┐
│  用户终端2: inspect_tasks.py (独立运行)                 │
│  - 读取任务状态                                          │
│  - 实时监控日志                                          │
│  - 管理playbook                                          │
└─────────────────────────────────────────────────────────┘
```

**关键设计**:
- ✅ **独立性**: 所有辅助脚本都可独立运行，不依赖CLI进程
- ✅ **文件系统通信**: 通过 `logs/generation_tasks/` 共享状态
- ✅ **非侵入性**: 不修改CLI代码，纯观测和管理

---

## 7. 改进建议

### 7.1 CLI集成建议

**建议1: 在CLI中添加快捷命令**
```python
# 在workflow_cli.py中添加
@cmd_decorator
def cmd_inspect(self, arg):
    """在新窗口打开任务检查器"""
    if arg == "tasks":
        os.system(f"gnome-terminal -- python scripts/inspect_tasks.py --list")
    elif arg.startswith("task "):
        task_id = arg.split()[1]
        os.system(f"gnome-terminal -- python scripts/inspect_tasks.py --watch {task_id}")
```

**建议2: 添加帮助提示**
```python
# 在/generate完成后提示
print("\n💡 提示: 在新终端中运行以下命令监控任务:")
print(f"   python scripts/inspect_tasks.py --watch {task_id}")
```

---

### 7.2 文档改进建议

**建议**: 在 `README.md` 中添加 "辅助工具" 章节，引用此报告。

---

## 8. 总结

### 核心发现

1. **`inspect_tasks.py` 是核心**: 这是chatbot CLI用户最重要的辅助工具，提供任务管理、日志查看、playbook统计等全方位功能。

2. **Analysis目录工具完善**: ACE框架的分析工具非常系统化，覆盖runs查询、性能分析、学习内容观测、playbook进化等各个维度。

3. **测试覆盖全面**: 提供了从基本功能到集成工作流的完整测试脚本。

4. **架构解耦优秀**: 所有辅助脚本都独立于CLI进程，通过文件系统通信，设计简洁可靠。

### 推荐使用优先级

**CLI用户**:
1. ⭐⭐⭐ `inspect_tasks.py` (任务管理)
2. ⭐⭐ `inspect_generation_result.py` (验证质量)

**系统开发者**:
1. ⭐⭐⭐ `analyze_performance.py` (性能优化)
2. ⭐⭐⭐ `view_ace_learning.py` (学习观测)
3. ⭐⭐ `analyze_playbook_evolution.py` (进化分析)
4. ⭐⭐ `test_chatbot_basic.py` (快速测试)

---

**报告结束**
