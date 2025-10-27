# Retry 命令扩展设计（简化版）

## 1. 设计目标

扩展 `/retry` 命令，支持三种任务状态的重试：

1. **FAILED** - 当前已支持，修复错误后重试
2. **CANCELLED** - **新增**：用户取消后改主意，恢复执行
3. **COMPLETED** - **新增**：用户对结果不满意，重新生成

## 2. 核心原则

### 2.1 接口统一
- 所有状态使用相同的 `/retry` 命令
- 所有状态都支持 `--stage` 和 `--mode` 参数
- COMPLETED 任务需要 `--force` 明确意图

### 2.2 数据一致性
- CANCELLED 任务：重置 `retry_count = 0`（因为不是错误）
- COMPLETED 任务：`retry_count` 不变（不计数）
- 所有重试操作都记录到 `retry_history`

### 2.3 Playbook 管理
- **关键新增**：feedback 结束的任务重试时，需要控制 playbook bullets 的保留/丢弃
- 新参数：`--keep-playbook`（保留已生成的 bullets）/ `--discard-playbook`（丢弃，回滚）

---

## 3. 状态支持矩阵

| 状态 | 当前支持 | 新设计 | 默认行为 | 必需参数 | retry_count |
|------|---------|--------|---------|---------|------------|
| FAILED | ✅ | ✅ | 从失败点继续 | 无 | +1 |
| CANCELLED | ❌ | ✅ | 从取消点继续 | 无 | 重置为0 |
| COMPLETED | ❌ | ✅ | 需明确意图 | `--force` | 不变 |
| AWAITING_CONFIRM | ✅ (通过 `/confirm`) | ✅ | 使用 `/confirm` | - | - |
| PENDING/其他 | ❌ | ❌ | 不支持 | - | - |

---

## 4. 命令语法设计

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
- `--force` - **FAILED**: 忽略重试次数限制；**COMPLETED**: 允许重新生成（必需）
- `--keep-playbook` - 保留已生成的 playbook bullets（默认行为）
- `--discard-playbook` - 丢弃已生成的 playbook bullets，回滚 playbook（需明确指定）

### 4.3 使用示例

#### FAILED 任务（现有行为）
```bash
# 从失败点继续
/retry abc123

# 完全重试
/retry abc123 --clean

# 强制重试（忽略次数限制）
/retry abc123 --force

# 从生成阶段重试
/retry abc123 --stage generate
```

#### CANCELLED 任务（新增）
```bash
# 从取消点恢复（自动检测）
/retry abc123

# 从头开始（清理所有数据）
/retry abc123 --clean

# 从特定阶段开始
/retry abc123 --stage generating

# 从 feedback 阶段开始，指定评估模式
/retry abc123 --stage feedback --mode llm_judge
```

#### COMPLETED 任务（新增）
```bash
# ❌ 错误：缺少 --force
/retry abc123
# 输出：❌ 任务已完成，请使用 --force 明确重新生成意图

# ✅ 正确：从生成阶段重新生成
/retry abc123 --force --stage generate

# 从头开始重新生成
/retry abc123 --force --clean

# 重新执行反馈流程（使用不同评估模式）
/retry abc123 --force --stage feedback --mode llm_judge
```

#### Feedback 结束的任务（特殊场景）
```bash
# 场景：任务已完成 feedback 流程，playbook 已更新

# 保留 playbook bullets，重新生成方案（默认行为）
/retry abc123 --force --stage generate
/retry abc123 --force --stage generate --keep-playbook  # 显式指定

# 丢弃 playbook bullets，回滚后重新生成
/retry abc123 --force --stage generate --discard-playbook

# 重新执行 feedback 流程（保留之前的 bullets，默认）
/retry abc123 --force --stage feedback --mode auto

# 重新执行 feedback 流程（丢弃之前的 bullets）
/retry abc123 --force --stage feedback --mode auto --discard-playbook
```

---

## 5. 实现设计

### 5.1 修改 `RetryHandler.can_retry()`

```python
def can_retry(
    self,
    task: GenerationTask,
    force: bool = False,
    force_stage: Optional[str] = None
) -> tuple[bool, str]:
    """检查任务是否可以重试（支持所有状态）

    Args:
        task: 任务对象
        force: 是否强制重试
        force_stage: 强制指定阶段

    Returns:
        (可重试, 原因)
    """
    # 1. 检查任务状态
    if task.status == TaskStatus.FAILED:
        return self._can_retry_failed(task, force, force_stage)

    elif task.status == TaskStatus.CANCELLED:
        return self._can_retry_cancelled(task, force_stage)

    elif task.status == TaskStatus.COMPLETED:
        return self._can_retry_completed(task, force, force_stage)

    else:
        return False, f"任务状态不支持重试（当前: {task.status.value}）"
```

### 5.2 状态检查方法

#### A. FAILED 任务（现有逻辑，稍作调整）
```python
def _can_retry_failed(
    self,
    task: GenerationTask,
    force: bool,
    force_stage: Optional[str]
) -> tuple[bool, str]:
    """检查FAILED任务是否可重试"""

    # 检查重试次数
    if not force and task.retry_count >= task.max_retries:
        return False, f"已达到最大重试次数 ({task.retry_count}/{task.max_retries})"

    # 检查错误是否可重试
    if task.error and not force:
        if not self._is_retryable_error(task.error):
            return False, f"此错误不可重试: {task.error}"

    # 检查是否有失败阶段信息
    if not task.failed_stage and not force_stage:
        return False, "缺少失败阶段信息，请使用 --stage 参数指定"

    return True, "可以重试"
```

#### B. CANCELLED 任务（新增）
```python
def _can_retry_cancelled(
    self,
    task: GenerationTask,
    force_stage: Optional[str]
) -> tuple[bool, str]:
    """检查CANCELLED任务是否可重试"""

    # CANCELLED 任务特点：
    # 1. 用户主动取消，不是系统错误
    # 2. 应该能直接恢复执行
    # 3. 不受重试次数限制（会重置为0）

    # 检测恢复阶段（优先使用 force_stage）
    resume_stage = force_stage or task.failed_stage or "extracting"

    # 别名映射
    stage_aliases = {
        "generate": "generating",
        "feedback": "evaluating",
    }
    if resume_stage in stage_aliases:
        resume_stage = stage_aliases[resume_stage]

    # 验证阶段有效性
    valid_stages = [
        "extracting", "retrieving", "generating",
        "evaluating", "reflecting", "curating"
    ]
    if resume_stage not in valid_stages:
        return False, f"未知的阶段: {resume_stage}"

    return True, f"可以从 {resume_stage} 阶段恢复"
```

#### C. COMPLETED 任务（新增）
```python
def _can_retry_completed(
    self,
    task: GenerationTask,
    force: bool,
    force_stage: Optional[str]
) -> tuple[bool, str]:
    """检查COMPLETED任务是否可重试"""

    # COMPLETED 任务重试 = 重新生成
    # 安全性考虑：必须明确用户意图

    if not force:
        return False, (
            "任务已完成，请使用 --force 明确重新生成意图\n"
            "  示例: /retry <task_id> --force --stage generate"
        )

    # 如果没有指定阶段，默认从 generating 开始（保留需求和模板）
    resume_stage = force_stage or "generating"

    # 别名映射
    stage_aliases = {
        "generate": "generating",
        "feedback": "evaluating",
    }
    if resume_stage in stage_aliases:
        resume_stage = stage_aliases[resume_stage]

    # 警告：完全重试会丢失所有数据
    if resume_stage == "extracting":
        print("  ⚠️  注意: 将清除所有中间数据（需求、模板、方案）")

    return True, f"将从 {resume_stage} 阶段重新生成"
```

### 5.3 修改 `RetryHandler.prepare_retry()`

```python
def prepare_retry(
    self,
    task: GenerationTask,
    clean: bool = False,
    force_stage: Optional[str] = None,
    keep_playbook: bool = True
) -> Dict:
    """准备重试任务（支持所有状态）

    Args:
        task: 任务对象
        clean: 是否完全清理
        force_stage: 强制指定阶段
        keep_playbook: 是否保留 playbook bullets（仅对 feedback 结束的任务有效）

    Returns:
        准备信息字典
    """
    if clean:
        # 完全重试：适用于所有状态
        return self._prepare_clean_retry(task)

    # 部分重试：根据状态选择策略
    if task.status == TaskStatus.CANCELLED:
        return self._prepare_cancelled_retry(task, force_stage, keep_playbook)
    elif task.status == TaskStatus.COMPLETED:
        return self._prepare_completed_retry(task, force_stage, keep_playbook)
    else:  # FAILED
        stage = force_stage or task.failed_stage
        return self._prepare_partial_retry(task, stage)
```

### 5.4 准备方法

#### A. 完全重试（通用）
```python
def _prepare_clean_retry(self, task: GenerationTask) -> Dict:
    """准备完全重试（所有状态通用）"""
    return {
        "strategy": "clean",
        "resume_from_stage": "extracting",
        "resume_from_status": TaskStatus.PENDING,
        "files_to_keep": ["config.json", "task.json"],
        "files_to_remove": [
            "requirements.json", "templates.json",
            "plan.json", "generation_result.json",
            "feedback.json", "reflection.json", "curation.json"
        ],
        "playbook_action": "none"  # 完全重试不涉及 playbook 操作
    }
```

#### B. CANCELLED 任务准备（新增）
```python
def _prepare_cancelled_retry(
    self,
    task: GenerationTask,
    force_stage: Optional[str],
    keep_playbook: bool
) -> Dict:
    """准备CANCELLED任务的恢复"""

    # 检测恢复阶段
    resume_stage = force_stage or task.failed_stage or "extracting"

    # 别名映射
    stage_aliases = {"generate": "generating", "feedback": "evaluating"}
    if resume_stage in stage_aliases:
        resume_stage = stage_aliases[resume_stage]

    # 根据恢复阶段决定保留/删除文件
    stage_mapping = {
        "extracting": {
            "resume_from_status": TaskStatus.PENDING,
            "files_to_keep": [],
            "files_to_remove": ["requirements.json"]
        },
        "retrieving": {
            "resume_from_status": TaskStatus.AWAITING_CONFIRM,
            "files_to_keep": ["requirements.json"],
            "files_to_remove": ["templates.json"]
        },
        "generating": {
            "resume_from_status": TaskStatus.RETRIEVING,
            "files_to_keep": ["requirements.json", "templates.json"],
            "files_to_remove": ["plan.json", "generation_result.json"]
        },
        # Feedback 阶段
        "evaluating": {
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json"
            ],
            "files_to_remove": ["feedback.json"]
        },
        "reflecting": {
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json", "feedback.json"
            ],
            "files_to_remove": ["reflection.json"]
        },
        "curating": {
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json",
                "feedback.json", "reflection.json"
            ],
            "files_to_remove": ["curation.json"]
        }
    }

    if resume_stage not in stage_mapping:
        raise ValueError(f"未知的阶段: {resume_stage}")

    info = stage_mapping[resume_stage]

    # 判断 playbook 操作
    playbook_action = self._determine_playbook_action(
        task, resume_stage, keep_playbook
    )

    return {
        "strategy": "resume_cancelled",
        "resume_from_stage": resume_stage,
        "resume_from_status": info["resume_from_status"],
        "files_to_keep": info["files_to_keep"],
        "files_to_remove": info["files_to_remove"],
        "playbook_action": playbook_action  # "none" | "rollback"
    }
```

#### C. COMPLETED 任务准备（新增）
```python
def _prepare_completed_retry(
    self,
    task: GenerationTask,
    force_stage: Optional[str],
    keep_playbook: bool
) -> Dict:
    """准备COMPLETED任务的重新生成"""

    # 默认从 generating 阶段开始（保留需求和模板）
    resume_stage = force_stage or "generating"

    # 别名映射
    stage_aliases = {"generate": "generating", "feedback": "evaluating"}
    if resume_stage in stage_aliases:
        resume_stage = stage_aliases[resume_stage]

    # 重新生成策略
    stage_mapping = {
        "extracting": {
            # 从头开始（清除所有中间数据）
            "resume_from_status": TaskStatus.PENDING,
            "files_to_keep": ["config.json", "task.json"],
            "files_to_remove": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json",
                "feedback.json", "reflection.json", "curation.json"
            ]
        },
        "generating": {
            # 保留需求和模板，重新生成方案
            "resume_from_status": TaskStatus.RETRIEVING,
            "files_to_keep": ["requirements.json", "templates.json"],
            "files_to_remove": [
                "plan.json", "generation_result.json",
                "feedback.json", "reflection.json", "curation.json"
            ]
        },
        "evaluating": {
            # 重新执行反馈流程
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json"
            ],
            "files_to_remove": [
                "feedback.json", "reflection.json", "curation.json"
            ]
        },
        "reflecting": {
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json", "feedback.json"
            ],
            "files_to_remove": ["reflection.json", "curation.json"]
        },
        "curating": {
            "resume_from_status": TaskStatus.COMPLETED,
            "files_to_keep": [
                "requirements.json", "templates.json",
                "plan.json", "generation_result.json",
                "feedback.json", "reflection.json"
            ],
            "files_to_remove": ["curation.json"]
        }
    }

    if resume_stage not in stage_mapping:
        raise ValueError(f"未知的阶段: {resume_stage}")

    info = stage_mapping[resume_stage]

    # 判断 playbook 操作
    playbook_action = self._determine_playbook_action(
        task, resume_stage, keep_playbook
    )

    return {
        "strategy": "regenerate",
        "resume_from_stage": resume_stage,
        "resume_from_status": info["resume_from_status"],
        "files_to_keep": info["files_to_keep"],
        "files_to_remove": info["files_to_remove"],
        "playbook_action": playbook_action
    }
```

### 5.5 Playbook 管理（关键新增）

```python
def _determine_playbook_action(
    self,
    task: GenerationTask,
    resume_stage: str,
    keep_playbook: bool
) -> str:
    """判断 playbook 操作类型

    Args:
        task: 任务对象
        resume_stage: 恢复阶段
        keep_playbook: 用户指定是否保留

    Returns:
        "none" - 不涉及 playbook 操作
        "rollback" - 回滚 playbook（丢弃 bullets）
    """
    # 1. 检查任务是否完成了 feedback 流程
    if not self._has_completed_feedback(task):
        return "none"  # 未完成 feedback，无需处理

    # 2. 所有阶段都由用户参数决定（不自动回滚）
    # 用户可能想用不同的评估模式重新执行 feedback，但保留之前的 playbook bullets
    if keep_playbook:
        return "none"  # 保留 bullets（默认）
    else:
        return "rollback"  # 丢弃 bullets（用户明确指定 --discard-playbook）


def _has_completed_feedback(self, task: GenerationTask) -> bool:
    """检查任务是否完成了 feedback 流程

    Returns:
        True - 已完成 feedback，playbook 可能已更新
        False - 未完成 feedback
    """
    # 方法1: 检查 curation.json 是否存在
    curation_file = task.task_dir / "curation.json"
    if curation_file.exists():
        return True

    # 方法2: 检查任务元数据（如果有 feedback_status）
    if hasattr(task, 'feedback_status') and task.feedback_status == "completed":
        return True

    return False


def _rollback_playbook(self, task: GenerationTask) -> bool:
    """回滚 playbook（丢弃此任务生成的 bullets）

    Args:
        task: 任务对象

    Returns:
        是否成功回滚
    """
    try:
        # 读取 curation.json，获取此任务生成的 bullet IDs
        curation_file = task.task_dir / "curation.json"
        if not curation_file.exists():
            print("  ℹ️  未找到 curation.json，跳过 playbook 回滚")
            return True

        import json
        with open(curation_file, 'r', encoding='utf-8') as f:
            curation_result = json.load(f)

        # 提取新增的 bullet IDs
        added_bullet_ids = []
        for update in curation_result.get("updates", []):
            if update.get("operation") == "ADD":
                added_bullet_ids.append(update.get("bullet_id"))

        if not added_bullet_ids:
            print("  ℹ️  此任务未添加 bullets，无需回滚")
            return True

        # 从 playbook 中移除这些 bullets
        from pathlib import Path
        playbook_path = Path("data/playbooks/chemistry_playbook.json")

        with open(playbook_path, 'r', encoding='utf-8') as f:
            playbook = json.load(f)

        original_count = len(playbook.get("bullets", []))
        playbook["bullets"] = [
            b for b in playbook.get("bullets", [])
            if b["id"] not in added_bullet_ids
        ]
        removed_count = original_count - len(playbook["bullets"])

        # 保存回滚后的 playbook
        with open(playbook_path, 'w', encoding='utf-8') as f:
            json.dump(playbook, f, ensure_ascii=False, indent=2)

        print(f"  ✅ Playbook 已回滚: 移除 {removed_count} 个 bullets")
        print(f"     移除的 IDs: {', '.join(added_bullet_ids)}")
        return True

    except Exception as e:
        print(f"  ⚠️  Playbook 回滚失败: {e}")
        return False
```

### 5.6 修改 `RetryHandler.execute_retry()`

```python
def execute_retry(
    self,
    task: GenerationTask,
    clean: bool = False,
    force: bool = False,
    force_stage: Optional[str] = None,
    keep_playbook: bool = True
) -> bool:
    """执行重试（支持所有状态）

    Args:
        task: 任务对象
        clean: 是否完全清理
        force: 是否强制重试
        force_stage: 强制指定阶段
        keep_playbook: 是否保留 playbook bullets

    Returns:
        是否成功准备重试
    """
    # 1. 检查是否可重试
    can_retry, reason = self.can_retry(task, force=force, force_stage=force_stage)
    if not can_retry:
        print(f"❌ 无法重试: {reason}")
        return False

    # 2. 准备重试
    print(f"\n🔄 准备重试任务 {task.task_id}")
    print(f"  ✅ 任务状态: {task.status.value}")

    # 根据状态显示不同信息
    if task.status == TaskStatus.CANCELLED:
        print(f"  💡 恢复已取消的任务")
    elif task.status == TaskStatus.COMPLETED:
        print(f"  💡 重新生成方案")

    # 显示阶段信息
    if force_stage:
        print(f"  ✅ 指定阶段: {force_stage}")
    elif task.failed_stage:
        print(f"  ✅ 恢复阶段: {task.failed_stage}")

    # 3. 准备重试策略
    prep_info = self.prepare_retry(
        task,
        clean=clean,
        force_stage=force_stage,
        keep_playbook=keep_playbook
    )

    print(f"\n📋 重试策略: {prep_info['strategy']}")
    print(f"  - 从阶段开始: {prep_info['resume_from_stage']}")
    print(f"  - 恢复到状态: {prep_info['resume_from_status'].value}")

    # 4. Playbook 操作（关键新增）
    if prep_info['playbook_action'] == 'rollback':
        print(f"\n🔄 回滚 Playbook...")
        self._rollback_playbook(task)

    # 5. 验证文件
    if prep_info['files_to_keep']:
        print(f"\n🔍 验证文件完整性...")
        corrupted = self.validate_files(task, prep_info['files_to_keep'])

        if corrupted:
            print(f"  ⚠️  发现损坏文件: {', '.join(corrupted)}")
            print(f"  ⚠️  建议使用 --clean 模式完全重试")
            prep_info['files_to_remove'].extend(corrupted)
            prep_info['files_to_keep'] = [
                f for f in prep_info['files_to_keep'] if f not in corrupted
            ]

    # 6. 清理文件
    if prep_info['files_to_remove']:
        print(f"\n🗑️  清理文件...")
        self.clean_files(task, prep_info['files_to_remove'])

    # 7. 记录重试历史
    retry_record = {
        "timestamp": datetime.now().isoformat(),
        "operation": self._get_operation_type(task.status),
        "previous_status": task.status.value,
        "retry_count": task.retry_count + 1 if task.status != TaskStatus.CANCELLED else 0,
        "previous_error": task.error if task.status == TaskStatus.FAILED else None,
        "previous_stage": task.failed_stage,
        "strategy": prep_info['strategy'],
        "playbook_action": prep_info['playbook_action']
    }
    task.retry_history.append(retry_record)

    # 8. 更新任务状态
    task.status = prep_info['resume_from_status']
    task.error = None
    task.failed_stage = None

    # 更新重试计数
    if retry_record['operation'] == 'resume_cancelled':
        # CANCELLED 任务：重置重试计数
        task.retry_count = 0
        print(f"  ℹ️  重试计数已重置为 0")
    elif retry_record['operation'] == 'retry':
        # FAILED 任务：递增重试计数
        task.retry_count += 1
        print(f"  ℹ️  重试次数: {task.retry_count}/{task.max_retries}")
    # COMPLETED 任务（regenerate）：不修改 retry_count

    # Feedback 流程重置
    if prep_info['resume_from_stage'] in ['evaluating', 'reflecting', 'curating']:
        task.feedback_status = "pending"
        task.feedback_error = None

    # 9. 保存任务
    self.task_manager._save_task(task)

    print(f"\n✅ 重试准备完成")
    return True


def _get_operation_type(self, status: TaskStatus) -> str:
    """获取操作类型（用于审计日志）"""
    if status == TaskStatus.FAILED:
        return "retry"
    elif status == TaskStatus.CANCELLED:
        return "resume_cancelled"
    elif status == TaskStatus.COMPLETED:
        return "regenerate"
    else:
        return "unknown"
```

### 5.7 CLI 参数解析

```python
# examples/workflow_cli.py

elif cmd == "/retry":
    if len(cmd_parts) < 2:
        print("\n用法: /retry <task_id> [options]\n")
        print("选项:")
        print("  --clean             完全重试（清理所有文件，从头开始）")
        print("  --force             强制重试（FAILED: 忽略次数限制; COMPLETED: 允许重新生成）")
        print("  --stage <s>         手动指定从哪个阶段重试")
        print("                      简写: generate, feedback")
        print("                      详细: extracting, generating, evaluating, reflecting, curating")
        print("  --mode <m>          覆盖评估模式（当 --stage 为 feedback 相关阶段时有效）")
        print("                      可选值: auto, llm_judge, human")
        print("  --keep-playbook     保留已生成的 playbook bullets（默认行为）")
        print("  --discard-playbook  丢弃已生成的 playbook bullets，回滚 playbook\n")
        print("示例:")
        print("  /retry abc123 --force --stage generate")
        print("  /retry abc123 --force --stage feedback --mode llm_judge")
        print("  /retry abc123 --force --stage generate --discard-playbook\n")
        continue

    task_id = cmd_parts[1]

    # 解析参数
    clean = "--clean" in cmd_parts
    force = "--force" in cmd_parts
    force_stage = None
    override_mode = None
    keep_playbook = True  # 默认保留

    # 解析 --stage
    if "--stage" in cmd_parts:
        try:
            stage_idx = cmd_parts.index("--stage")
            force_stage = cmd_parts[stage_idx + 1]
        except IndexError:
            print("⚠️  --stage 参数缺少值\n")
            continue

    # 解析 --mode
    if "--mode" in cmd_parts:
        try:
            mode_idx = cmd_parts.index("--mode")
            override_mode = cmd_parts[mode_idx + 1]
            if override_mode not in ["auto", "llm_judge", "human"]:
                print(f"⚠️  不支持的评估模式: {override_mode}")
                print("   请使用: auto, llm_judge, 或 human\n")
                continue
        except IndexError:
            print("⚠️  --mode 参数缺少值\n")
            continue

    # 解析 --discard-playbook
    if "--discard-playbook" in cmd_parts:
        keep_playbook = False

    # 使用 RetryCommandHandler
    from workflow.command_handler import RetryCommandHandler
    retry_handler = RetryCommandHandler(scheduler)

    success = retry_handler.handle(
        task_id=task_id,
        clean=clean,
        force=force,
        force_stage=force_stage,
        override_mode=override_mode,
        keep_playbook=keep_playbook
    )

    print()
    continue
```

### 5.8 修改 `RetryCommandHandler.handle()`

```python
# src/workflow/command_handler.py

def handle(
    self,
    task_id: str,
    clean: bool = False,
    force: bool = False,
    force_stage: Optional[str] = None,
    override_mode: Optional[str] = None,
    keep_playbook: bool = True
) -> bool:
    """处理重试命令（支持所有状态）

    Args:
        task_id: 任务ID
        clean: 是否完全清理
        force: 是否强制重试
        force_stage: 强制指定阶段
        override_mode: 覆盖评估模式
        keep_playbook: 是否保留 playbook bullets

    Returns:
        是否成功
    """
    # 1. 加载任务
    task = self.task_manager.get_task(task_id)
    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return False

    # 2. 检查并终止残留子进程
    if task_id in self.task_scheduler.processes:
        print(f"⚠️  检测到残留子进程，正在终止...")
        self.task_scheduler.terminate_task(task_id)
        time.sleep(1)

    # 3. 执行重试准备
    success = self.retry_handler.execute_retry(
        task=task,
        clean=clean,
        force=force,
        force_stage=force_stage,
        keep_playbook=keep_playbook
    )

    if not success:
        return False

    # 4. 重新加载任务（状态已更新）
    task = self.task_manager.get_task(task_id)

    # 5. 根据策略启动子进程
    if force_stage in ['evaluating', 'reflecting', 'curating']:
        # Feedback 流程：使用独立子进程
        success = self.task_scheduler.submit_feedback_task(
            task_id=task_id,
            evaluation_mode=override_mode
        )
    else:
        # 主流程：恢复任务
        success = self.task_scheduler.resume_task(task_id)

    if success:
        print(f"\n✅ 子进程已启动，使用 /logs {task_id} 查看进度")
    else:
        print(f"\n❌ 子进程启动失败")

    return success
```

---

## 6. 数据结构（无新增字段）

### 6.1 GenerationTask（复用现有字段）

```python
class GenerationTask(BaseModel):
    # 现有字段
    task_id: str
    session_id: str
    status: TaskStatus
    retry_count: int = 0
    max_retries: int = 3
    failed_stage: Optional[str] = None
    error: Optional[str] = None

    # 现有 retry_history（扩展格式）
    retry_history: List[Dict] = []
    # 新格式：
    # {
    #     "timestamp": "...",
    #     "operation": "retry" | "resume_cancelled" | "regenerate",
    #     "previous_status": "failed" | "cancelled" | "completed",
    #     "retry_count": int,
    #     "strategy": "partial" | "clean" | "resume_cancelled" | "regenerate",
    #     "playbook_action": "none" | "rollback"
    # }

    # 现有 feedback 相关字段
    feedback_status: Optional[str] = None
    feedback_error: Optional[str] = None
```

**关键变化**：
- ❌ 不新增 `regenerate_count`（简化设计）
- ✅ `retry_count` 计数规则：
  - FAILED: +1
  - CANCELLED: 重置为0
  - COMPLETED: 不变（不计数）
- ✅ `retry_history` 扩展字段（记录操作类型和 playbook 操作）

---

## 7. 用户交互流程

### 7.1 CANCELLED 任务恢复

```
用户: /retry abc123

系统:
🔄 准备重试任务 abc123
  ✅ 任务状态: cancelled
  💡 恢复已取消的任务
  ✅ 恢复阶段: generating

📋 重试策略: resume_cancelled
  - 从阶段开始: generating
  - 恢复到状态: retrieving

🔍 验证文件完整性...
  ✅ requirements.json (有效)
  ✅ templates.json (有效)

✅ 重试准备完成
  - 任务状态已更新: retrieving
  - 重试计数已重置为 0

✅ 子进程已启动，使用 /logs abc123 查看进度
```

### 7.2 COMPLETED 任务重新生成

#### 错误示例（缺少 --force）
```
用户: /retry abc123

系统:
❌ 无法重试: 任务已完成，请使用 --force 明确重新生成意图
  示例: /retry abc123 --force --stage generate
```

#### 正确示例（保留 playbook）
```
用户: /retry abc123 --force --stage generate

系统:
🔄 准备重试任务 abc123
  ✅ 任务状态: completed
  💡 重新生成方案
  ✅ 指定阶段: generate

📋 重试策略: regenerate
  - 从阶段开始: generating
  - 恢复到状态: retrieving

🔍 验证文件完整性...
  ✅ requirements.json (有效)
  ✅ templates.json (有效)

🗑️  清理文件...
  🗑️  已删除: plan.json
  🗑️  已删除: generation_result.json
  🗑️  已删除: feedback.json

✅ 重试准备完成
  - 任务状态已更新: retrieving

✅ 子进程已启动，使用 /logs abc123 查看进度
```

#### 正确示例（丢弃 playbook）
```
用户: /retry abc123 --force --stage generate --discard-playbook

系统:
🔄 准备重试任务 abc123
  ✅ 任务状态: completed
  💡 重新生成方案
  ✅ 指定阶段: generate

📋 重试策略: regenerate
  - 从阶段开始: generating
  - 恢复到状态: retrieving

🔄 回滚 Playbook...
  ✅ Playbook 已回滚: 移除 3 个 bullets
     移除的 IDs: mat-00042, proc-00028, safe-00019

🔍 验证文件完整性...
  ✅ requirements.json (有效)
  ✅ templates.json (有效)

🗑️  清理文件...
  🗑️  已删除: plan.json
  🗑️  已删除: generation_result.json
  🗑️  已删除: feedback.json
  🗑️  已删除: reflection.json
  🗑️  已删除: curation.json

✅ 重试准备完成
  - 任务状态已更新: retrieving

✅ 子进程已启动，使用 /logs abc123 查看进度
```

### 7.3 Feedback 阶段重新执行

#### 场景1: 保留 playbook（默认）
```
用户: /retry abc123 --force --stage feedback --mode llm_judge

系统:
🔄 准备重试任务 abc123
  ✅ 任务状态: completed
  💡 重新生成方案
  ✅ 指定阶段: feedback

📋 重试策略: regenerate
  - 从阶段开始: evaluating
  - 恢复到状态: completed

🗑️  清理文件...
  🗑️  已删除: feedback.json
  🗑️  已删除: reflection.json
  🗑️  已删除: curation.json

✅ 重试准备完成
  - 任务状态已更新: completed

✅ 子进程已启动（feedback 模式: llm_judge），使用 /logs abc123 查看进度
```

#### 场景2: 丢弃 playbook
```
用户: /retry abc123 --force --stage feedback --mode llm_judge --discard-playbook

系统:
🔄 准备重试任务 abc123
  ✅ 任务状态: completed
  💡 重新生成方案
  ✅ 指定阶段: feedback

📋 重试策略: regenerate
  - 从阶段开始: evaluating
  - 恢复到状态: completed

🔄 回滚 Playbook...
  ✅ Playbook 已回滚: 移除 3 个 bullets
     移除的 IDs: mat-00042, proc-00028, safe-00019

🗑️  清理文件...
  🗑️  已删除: feedback.json
  🗑️  已删除: reflection.json
  🗑️  已删除: curation.json

✅ 重试准备完成
  - 任务状态已更新: completed

✅ 子进程已启动（feedback 模式: llm_judge），使用 /logs abc123 查看进度
```

---

## 8. 边缘情况处理

### 8.1 子进程冲突
- **检测**：`task_id in scheduler.processes`
- **处理**：自动调用 `terminate_task()`，等待 1 秒

### 8.2 数据损坏
- **检测**：验证 `files_to_keep` 的 JSON 格式和必需字段
- **处理**：自动移入 `files_to_remove`，提示使用 `--clean`

### 8.3 Playbook 回滚失败
- **场景**：`curation.json` 不存在或损坏
- **处理**：跳过回滚，打印警告，继续重试流程

### 8.4 反馈流程特殊处理
- **场景**：`--stage evaluating` 且任务状态为 COMPLETED
- **处理**：
  1. 根据 `--discard-playbook` 参数决定是否回滚 playbook
  2. 保持任务状态为 COMPLETED
  3. 调用 `submit_feedback_task()` 启动独立子进程

---

## 9. 测试场景

### 9.1 CANCELLED 任务测试

```bash
# 场景1: 生成阶段取消，直接恢复
/cancel abc123
/retry abc123

# 场景2: 指定从 feedback 阶段开始
/cancel abc123
/retry abc123 --stage feedback --mode auto
```

### 9.2 COMPLETED 任务测试

```bash
# 场景1: 缺少 --force（错误）
/retry abc123

# 场景2: 保留 playbook，重新生成方案（默认）
/retry abc123 --force --stage generate

# 场景3: 丢弃 playbook，重新生成方案
/retry abc123 --force --stage generate --discard-playbook

# 场景4: 重新执行 feedback
/retry abc123 --force --stage feedback --mode llm_judge
```

### 9.3 边缘情况测试

```bash
# 场景1: 子进程冲突
/retry abc123 --force  # 任务正在运行，自动终止

# 场景2: 文件损坏
echo "invalid" > logs/generation_tasks/abc123/requirements.json
/retry abc123  # 自动检测并删除

# 场景3: Playbook 回滚失败
rm logs/generation_tasks/abc123/curation.json
/retry abc123 --force --stage generate --discard-playbook
# 输出: ℹ️  未找到 curation.json，跳过 playbook 回滚
```

---

## 10. 实施优先级

### P0（必须实现）
1. ✅ `RetryHandler.can_retry()` 支持 CANCELLED/COMPLETED
2. ✅ `_can_retry_cancelled()` 方法
3. ✅ `_can_retry_completed()` 方法
4. ✅ `_prepare_cancelled_retry()` 方法
5. ✅ `_prepare_completed_retry()` 方法
6. ✅ Playbook 管理方法（`_determine_playbook_action`, `_rollback_playbook`）
7. ✅ CLI 参数解析支持 `--keep-playbook` / `--discard-playbook`
8. ✅ `RetryCommandHandler.handle()` 支持 `keep_playbook` 参数

### P1（强烈建议）
9. ✅ `retry_history` 扩展字段（记录操作类型、playbook 操作）
10. ✅ 边缘情况处理（子进程冲突、数据损坏、playbook 回滚失败）
11. ✅ 用户提示优化（CANCELLED/COMPLETED 不同提示，playbook 操作提示）

---

## 11. 向后兼容性

### 11.1 现有任务
- **FAILED 任务**：完全兼容，无行为变化
- **旧版本 CANCELLED 任务**：默认从 `extracting` 开始

### 11.2 配置文件
- 无需修改现有配置

### 11.3 CLI 命令
- 现有命令完全兼容
- 新增参数（`--keep-playbook`, `--discard-playbook`）为可选

---

## 12. 文档更新

### 需要更新的文档
1. **RETRY_USAGE_GUIDE.md** - 添加新状态的使用示例
2. **RETRY_MECHANISM_DESIGN.md** - 同步技术设计
3. **workflow_cli.py 帮助信息** - 更新 `/retry` 的 help 文本

---

## 13. 总结

### 核心改进
1. **CANCELLED 任务**：一键恢复，重置重试计数
2. **COMPLETED 任务**：需 `--force` 明确意图，不修改重试计数
3. **Playbook 管理**：支持保留/回滚 bullets，用户完全控制
4. **统一接口**：所有状态支持 `--stage` 和 `--mode` 参数

### 设计亮点
- ✅ 简化数据结构（不新增字段）
- ✅ 安全性：COMPLETED 重试需要 `--force`
- ✅ 灵活性：Playbook 回滚由用户完全控制（无自动行为）
- ✅ 一致性：COMPLETED 任务重新生成不影响重试计数
- ✅ 可追溯：完整历史记录（包括 playbook 操作）

### 风险评估
- **低风险**：CANCELLED 任务恢复（逻辑简单）
- **中风险**：Playbook 回滚（需正确解析 curation.json）
- **缓解措施**：回滚失败时跳过并打印警告，不阻塞重试流程
