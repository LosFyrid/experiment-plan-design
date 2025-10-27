# Retry 命令扩展方案总结

> 最终版本 - 2025-10-27

## 1. 设计目标

扩展 `/retry` 命令，支持三种任务状态的重试：
- **FAILED** - 修复错误后重试（现有功能）
- **CANCELLED** - 用户取消后恢复执行（新增）
- **COMPLETED** - 用户对结果不满意，重新生成（新增）

---

## 2. 核心原则

### 2.1 接口统一
- 所有状态使用相同的 `/retry` 命令
- 所有状态都支持 `--stage` 和 `--mode` 参数
- COMPLETED 任务需要 `--force` 明确意图（防止误操作）

### 2.2 数据一致性
- **FAILED 任务**：`retry_count +1`（继续计数）
- **CANCELLED 任务**：`retry_count = 0`（重置，因为不是错误）
- **COMPLETED 任务**：`retry_count` 不变（重新生成不视为重试）

### 2.3 Playbook 管理
- feedback 结束的任务重试时，支持保留/回滚 playbook bullets
- `--keep-playbook`（默认）：保留已生成的 bullets
- `--discard-playbook`：丢弃 bullets，回滚 playbook
- **关键设计**：由用户完全控制，无自动回滚行为

---

## 3. 状态支持矩阵

| 状态 | 当前支持 | 新设计 | 默认行为 | 必需参数 | retry_count |
|------|---------|--------|---------|---------|------------|
| **FAILED** | ✅ | ✅ | 从失败点继续 | 无 | +1 |
| **CANCELLED** | ❌ | ✅ | 从取消点继续 | 无 | 重置为0 |
| **COMPLETED** | ❌ | ✅ | 需明确意图 | `--force` | 不变 |
| AWAITING_CONFIRM | ✅ | ✅ | 使用 `/confirm` | - | - |
| PENDING/其他 | ❌ | ❌ | 不支持 | - | - |

---

## 4. 命令语法

### 4.1 基本语法
```bash
/retry <task_id> [options]
```

### 4.2 参数说明

#### 通用参数（所有状态支持）
- `--clean` - 完全重试，清理所有中间文件，从头开始
- `--stage <stage>` - 手动指定从哪个阶段开始
  - 简写：`generate`, `feedback`
  - 详细：`extracting`, `retrieving`, `generating`, `evaluating`, `reflecting`, `curating`
- `--mode <mode>` - 覆盖评估模式（当 `--stage` 为 feedback 相关阶段时有效）
  - 可选值：`auto`, `llm_judge`, `human`

#### 状态特定参数
- `--force` - FAILED: 忽略重试次数限制；COMPLETED: 允许重新生成（必需）
- `--keep-playbook` - 保留已生成的 playbook bullets（默认行为）
- `--discard-playbook` - 丢弃已生成的 playbook bullets，回滚 playbook

### 4.3 典型用法

#### FAILED 任务
```bash
/retry abc123                    # 从失败点继续
/retry abc123 --force            # 强制重试（忽略次数限制）
/retry abc123 --stage generate   # 从指定阶段重试
```

#### CANCELLED 任务
```bash
/retry abc123                              # 从取消点恢复
/retry abc123 --stage feedback --mode auto # 从 feedback 阶段开始
```

#### COMPLETED 任务
```bash
/retry abc123 --force --stage generate                        # 重新生成方案
/retry abc123 --force --stage generate --discard-playbook    # 丢弃 playbook 后重新生成
/retry abc123 --force --stage feedback --mode llm_judge      # 用不同模式重新执行 feedback
```

---

## 5. 关键设计决策

### 5.1 为什么 COMPLETED 任务不计数？
- **语义一致性**：重新生成不是"修复错误"，是"用户不满意想重新生成"
- **灵活性**：用户可以无限次重新生成，尝试不同参数（如不同评估模式）
- **避免混淆**：retry_count 专门用于失败重试，COMPLETED 重新生成是独立操作

### 5.2 为什么不自动回滚 playbook？
- **用户意图不明确**：用户可能只是想用不同评估模式重新执行 feedback，但保留之前的 bullets
- **灵活性优先**：用户可能手动编辑了 playbook，想用新 playbook 重新生成
- **明确控制**：通过 `--discard-playbook` 参数让用户明确表达意图

**典型场景**：
- 场景1：用户用 `auto` 模式执行了 feedback，生成了 3 个 bullets
- 场景2：用户想试试 `llm_judge` 模式，看看效果如何
- 如果自动回滚：场景1 的 bullets 会被删除（用户可能不希望）
- 新设计：默认保留，用户可选择 `--discard-playbook` 重新开始

### 5.3 Playbook 回滚机制
- 读取 `curation.json`，提取此任务添加的 bullet IDs
- 从 `data/playbooks/chemistry_playbook.json` 移除这些 bullets
- 回滚失败不阻塞重试流程（跳过并打印警告）

---

## 6. 实施清单

### 6.1 核心方法（RetryHandler）

**新增方法**（3个状态检查 + 2个准备方法 + 3个 Playbook 管理）：
1. `_can_retry_cancelled(task, force_stage)` - 检查 CANCELLED 任务是否可重试
2. `_can_retry_completed(task, force, force_stage)` - 检查 COMPLETED 任务是否可重试
3. `_prepare_cancelled_retry(task, force_stage, keep_playbook)` - 准备 CANCELLED 任务恢复
4. `_prepare_completed_retry(task, force_stage, keep_playbook)` - 准备 COMPLETED 任务重新生成
5. `_determine_playbook_action(task, resume_stage, keep_playbook)` - 判断 playbook 操作类型
6. `_has_completed_feedback(task)` - 检查任务是否完成了 feedback 流程
7. `_rollback_playbook(task)` - 回滚 playbook（移除此任务的 bullets）

**修改方法**：
8. `can_retry(task, force, force_stage)` - 路由到不同状态检查方法
9. `prepare_retry(task, clean, force_stage, keep_playbook)` - 路由到不同准备方法
10. `execute_retry(task, clean, force, force_stage, keep_playbook)` - 添加 Playbook 操作逻辑

### 6.2 CLI 参数解析（workflow_cli.py）

**新增参数解析**：
- `keep_playbook = True`（默认）
- `if "--discard-playbook" in cmd_parts: keep_playbook = False`

**传递参数**：
- `retry_handler.handle(..., keep_playbook=keep_playbook)`

### 6.3 命令处理器（RetryCommandHandler）

**修改方法签名**：
- `handle(task_id, clean, force, force_stage, override_mode, keep_playbook)`

**传递参数**：
- `retry_handler.execute_retry(..., keep_playbook=keep_playbook)`

### 6.4 数据结构（GenerationTask）

**无需新增字段**，复用现有字段：
- `retry_count` - 计数逻辑按状态区分
- `retry_history` - 扩展格式，记录操作类型和 playbook 操作
  ```python
  {
      "timestamp": "...",
      "operation": "retry" | "resume_cancelled" | "regenerate",
      "previous_status": "failed" | "cancelled" | "completed",
      "retry_count": int,
      "strategy": "partial" | "clean" | "resume_cancelled" | "regenerate",
      "playbook_action": "none" | "rollback"
  }
  ```

---

## 7. 关键实现细节

### 7.1 状态映射（stage_mapping）

CANCELLED 和 COMPLETED 任务共享相同的阶段映射：
- `extracting` → PENDING，清除所有中间文件
- `retrieving` → AWAITING_CONFIRM，保留 requirements.json
- `generating` → RETRIEVING，保留 requirements.json + templates.json
- `evaluating` → COMPLETED，保留到 generation_result.json
- `reflecting` → COMPLETED，保留到 feedback.json
- `curating` → COMPLETED，保留到 reflection.json

### 7.2 Playbook 操作逻辑

```
if _has_completed_feedback(task):
    if keep_playbook:
        return "none"      # 保留（默认）
    else:
        return "rollback"  # 丢弃（用户明确指定）
else:
    return "none"          # 未完成 feedback，无需处理
```

### 7.3 retry_count 更新逻辑

```
if operation == 'resume_cancelled':
    task.retry_count = 0
    print("重试计数已重置为 0")
elif operation == 'retry':
    task.retry_count += 1
    print(f"重试次数: {task.retry_count}/{task.max_retries}")
# COMPLETED 任务（regenerate）：不修改 retry_count，无输出
```

### 7.4 别名映射（简写支持）

```python
stage_aliases = {
    "generate": "generating",
    "feedback": "evaluating"
}
```

---

## 8. 边缘情况处理

### 8.1 子进程冲突
- **检测**：`task_id in scheduler.processes`
- **处理**：自动调用 `terminate_task(task_id)`，等待 1 秒

### 8.2 数据损坏
- **检测**：验证 `files_to_keep` 的 JSON 格式和必需字段
- **处理**：自动移入 `files_to_remove`，提示使用 `--clean`

### 8.3 Playbook 回滚失败
- **场景**：`curation.json` 不存在或损坏
- **处理**：打印警告，跳过回滚，继续重试流程（不阻塞）

### 8.4 反馈流程特殊处理
- **场景**：`--stage evaluating` 且任务状态为 COMPLETED
- **处理**：
  1. 根据 `--discard-playbook` 参数决定是否回滚 playbook
  2. 保持任务状态为 COMPLETED
  3. 调用 `submit_feedback_task()` 启动独立子进程

---

## 9. 测试要点

### 9.1 CANCELLED 任务测试

**基本恢复**：
- 场景：生成阶段取消 → 直接恢复
- 验证：retry_count 重置为 0

**指定阶段**：
- 场景：取消后指定从 feedback 阶段开始
- 验证：正确恢复，支持 --mode 参数

### 9.2 COMPLETED 任务测试

**缺少 --force**：
- 场景：`/retry abc123`（COMPLETED 任务）
- 预期：❌ 错误提示，要求使用 --force

**保留 playbook**：
- 场景：`/retry abc123 --force --stage generate`（默认）
- 验证：playbook 保留，retry_count 不变

**丢弃 playbook**：
- 场景：`/retry abc123 --force --stage generate --discard-playbook`
- 验证：playbook 回滚，bullets 被移除

**Feedback 阶段**：
- 场景1：`/retry abc123 --force --stage feedback --mode llm_judge`（默认）
- 验证：playbook 保留
- 场景2：同上 + `--discard-playbook`
- 验证：playbook 回滚

### 9.3 边缘情况测试

**子进程冲突**：
- 场景：任务正在运行时执行 `/retry`
- 验证：自动终止子进程，等待后继续

**文件损坏**：
- 场景：`requirements.json` 损坏
- 验证：自动检测并删除，提示使用 `--clean`

**Playbook 回滚失败**：
- 场景：`curation.json` 不存在
- 验证：跳过回滚，打印警告，继续重试流程

---

## 10. 向后兼容性

### 10.1 现有任务
- **FAILED 任务**：完全兼容，无行为变化
- **旧版本 CANCELLED 任务**：默认从 `extracting` 开始

### 10.2 配置文件
- 无需修改现有配置

### 10.3 CLI 命令
- 现有命令完全兼容
- 新增参数（`--keep-playbook`, `--discard-playbook`）为可选

---

## 11. 设计亮点

### 核心优势
1. **简化数据结构**：零新增字段，复用现有 `retry_count` 和 `retry_history`
2. **接口统一**：所有状态使用相同命令和参数
3. **用户完全控制**：Playbook 回滚无自动行为，由参数明确控制
4. **语义一致性**：COMPLETED 重新生成不视为重试，不影响计数
5. **灵活性**：支持多次重新生成，尝试不同参数组合

### 适用场景
- **场景1**：用户手动编辑 playbook，想用新 playbook 重新生成 → 保留
- **场景2**：playbook 质量不佳，想回滚后重新来 → 丢弃
- **场景3**：尝试不同评估模式，但保留之前的结果 → 保留

---

## 12. 风险评估

### 低风险
- CANCELLED 任务恢复（逻辑简单）
- COMPLETED 任务重新生成（明确 --force 要求）

### 中风险
- Playbook 回滚（需正确解析 curation.json）

### 缓解措施
- 回滚失败时跳过并打印警告，不阻塞重试流程
- 充分测试 curation.json 解析逻辑
- 提供详细的错误提示

---

## 13. 实施步骤建议

### Phase 1: 核心逻辑（优先级 P0）
1. 修改 `RetryHandler.can_retry()` - 路由到不同状态检查
2. 实现 `_can_retry_cancelled()`
3. 实现 `_can_retry_completed()`
4. 实现 `_prepare_cancelled_retry()`
5. 实现 `_prepare_completed_retry()`

### Phase 2: Playbook 管理（优先级 P0）
6. 实现 `_determine_playbook_action()`
7. 实现 `_has_completed_feedback()`
8. 实现 `_rollback_playbook()`
9. 修改 `execute_retry()` 添加 Playbook 操作逻辑

### Phase 3: CLI 集成（优先级 P0）
10. 修改 `workflow_cli.py` 参数解析
11. 修改 `RetryCommandHandler.handle()` 方法签名
12. 更新 help 文本

### Phase 4: 测试验证（优先级 P1）
13. 单元测试（各状态的 can_retry 和 prepare_retry）
14. 集成测试（完整重试流程）
15. 边缘情况测试（子进程冲突、数据损坏、回滚失败）

### Phase 5: 文档更新（优先级 P1）
16. 更新 `RETRY_USAGE_GUIDE.md`
17. 更新 `RETRY_MECHANISM_DESIGN.md`

---

## 14. 预期效果

### 用户体验改进
- ✅ CANCELLED 任务一键恢复，无需重新开始
- ✅ COMPLETED 任务可重新生成，支持参数调优
- ✅ Playbook 管理灵活，支持保留/回滚
- ✅ 统一接口，学习成本低

### 系统健壮性
- ✅ retry_count 语义清晰，不混淆
- ✅ 完整的 retry_history 审计日志
- ✅ 边缘情况处理完善
- ✅ 向后兼容，无破坏性变更

---

## 15. 审阅 Checklist

在开始实施前，请确认：

- [ ] **状态支持矩阵**：FAILED/CANCELLED/COMPLETED 的行为是否合理？
- [ ] **retry_count 规则**：FAILED(+1), CANCELLED(重置), COMPLETED(不变) 是否正确？
- [ ] **Playbook 策略**：默认保留，需 `--discard-playbook` 明确丢弃，是否合理？
- [ ] **参数设计**：`--stage` 和 `--mode` 对所有状态支持，是否符合需求？
- [ ] **边缘情况**：子进程冲突、数据损坏、回滚失败的处理是否充分？
- [ ] **向后兼容**：现有 FAILED 任务行为是否完全不受影响？
- [ ] **实施清单**：10个方法修改/新增，是否有遗漏？
- [ ] **测试覆盖**：9.1-9.3 的测试场景是否覆盖所有关键路径？

---

**方案版本**：Final v1.0
**创建时间**：2025-10-27
**状态**：待审阅 → 待实施
