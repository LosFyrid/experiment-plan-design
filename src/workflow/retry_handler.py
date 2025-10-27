"""重试处理器 - 智能重试失败的任务

设计原则：
1. 根据失败阶段选择重试策略
2. 验证文件完整性
3. 防止无限重试
4. 处理边缘情况（子进程、文件锁等）
"""

import time
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime

from workflow.task_manager import (
    GenerationTask,
    TaskStatus,
    get_task_manager
)


# 不可重试的错误模式
NON_RETRYABLE_ERRORS = [
    "配置文件不存在",
    "Playbook不存在",
    "API密钥无效",
    "模型不存在",
    "权限不足",
    "config.json",
    "FileNotFoundError"
]


class RetryHandler:
    """重试处理器"""

    def __init__(self, task_manager=None):
        """
        Args:
            task_manager: TaskManager 实例（可选，默认使用单例）
        """
        self.task_manager = task_manager or get_task_manager()

    def can_retry(self, task: GenerationTask, force: bool = False, force_stage: Optional[str] = None) -> tuple[bool, str]:
        """检查任务是否可以重试（支持所有状态）

        Args:
            task: 任务对象
            force: 是否强制重试
            force_stage: 强制指定阶段

        Returns:
            (可重试, 原因)
        """
        # 1. 根据任务状态路由到不同的检查方法
        if task.status == TaskStatus.FAILED:
            return self._can_retry_failed(task, force, force_stage)
        elif task.status == TaskStatus.CANCELLED:
            return self._can_retry_cancelled(task, force_stage)
        elif task.status == TaskStatus.COMPLETED:
            return self._can_retry_completed(task, force, force_stage)
        elif task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            # 中间状态：任务卡住（子进程已退出但状态未更新）
            return self._can_retry_stuck(task, force, force_stage)
        else:
            return False, f"任务状态不支持重试（当前: {task.status.value}）"

    def _can_retry_failed(self, task: GenerationTask, force: bool, force_stage: Optional[str]) -> tuple[bool, str]:
        """检查FAILED任务是否可重试（现有逻辑）"""
        # 1. 检查重试次数
        if not force and task.retry_count >= task.max_retries:
            return False, f"已达到最大重试次数 ({task.retry_count}/{task.max_retries})"

        # 2. 检查错误是否可重试
        if task.error and not force:
            if not self._is_retryable_error(task.error):
                return False, f"此错误不可重试: {task.error}"

        # 3. 检查是否有失败阶段信息
        if not task.failed_stage and not force_stage:
            return False, "缺少失败阶段信息，请使用 --stage 参数指定"

        return True, "可以重试"

    def _can_retry_cancelled(self, task: GenerationTask, force_stage: Optional[str]) -> tuple[bool, str]:
        """检查CANCELLED任务是否可重试（新增）"""
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

    def _can_retry_completed(self, task: GenerationTask, force: bool, force_stage: Optional[str]) -> tuple[bool, str]:
        """检查COMPLETED任务是否可重试（新增）"""
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

    def _can_retry_stuck(self, task: GenerationTask, force: bool, force_stage: Optional[str]) -> tuple[bool, str]:
        """检查卡住的中间状态任务是否可重试（新增）

        场景：子进程已退出但任务状态未更新为 FAILED
        处理：视为隐式失败，允许重试
        """
        # 1. 检查重试次数（除非force）
        if not force and task.retry_count >= task.max_retries:
            return False, f"已达到最大重试次数 ({task.retry_count}/{task.max_retries})"

        # 2. 检测重试阶段
        if force_stage:
            # 用户明确指定阶段
            resume_stage = force_stage
        else:
            # 自动检测：根据当前状态推断
            state_to_stage = {
                TaskStatus.PENDING: "extracting",
                TaskStatus.EXTRACTING: "extracting",
                TaskStatus.RETRIEVING: "retrieving",
                TaskStatus.GENERATING: "generating"
            }
            resume_stage = state_to_stage.get(task.status, "extracting")

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

        return True, f"检测到任务卡住，可以从 {resume_stage} 阶段重试"

    def _is_retryable_error(self, error_msg: str) -> bool:
        """判断错误是否可重试"""
        for pattern in NON_RETRYABLE_ERRORS:
            if pattern in error_msg:
                return False
        return True

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
        elif task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            # 卡住的中间状态：视为FAILED，但自动检测阶段
            if force_stage:
                stage = force_stage
            else:
                # 根据当前状态自动检测阶段
                state_to_stage = {
                    TaskStatus.PENDING: "extracting",
                    TaskStatus.EXTRACTING: "extracting",
                    TaskStatus.RETRIEVING: "retrieving",
                    TaskStatus.GENERATING: "generating"
                }
                stage = state_to_stage.get(task.status, "extracting")
            return self._prepare_partial_retry(task, stage)
        else:  # FAILED
            stage = force_stage or task.failed_stage
            return self._prepare_partial_retry(task, stage)

    def _prepare_clean_retry(self, task: GenerationTask) -> Dict:
        """准备完全重试（所有状态通用）"""
        return {
            "strategy": "clean",
            "resume_from_stage": "extracting",
            "resume_from_status": TaskStatus.PENDING,
            "files_to_keep": ["config.json", "task.json"],  # 只保留配置
            "files_to_remove": [
                "requirements.json",
                "templates.json",
                "plan.json",
                "generation_result.json",
                "feedback.json",
                "reflection.json",
                "curation.json"
            ],
            "playbook_action": "none"  # 完全重试不涉及 playbook 操作
        }

    def _prepare_partial_retry(self, task: GenerationTask, failed_stage: str) -> Dict:
        """准备部分重试（从失败点继续）"""

        # 别名映射：用户友好的名称 → 实际阶段
        stage_aliases = {
            "generate": "generating",  # 用户自然语言：从生成阶段重试
            "feedback": "evaluating",   # 用户自然语言：从反馈阶段重试
        }

        # 如果是别名，转换为实际阶段
        if failed_stage in stage_aliases:
            failed_stage = stage_aliases[failed_stage]

        # 根据失败阶段决定从哪里恢复
        stage_mapping = {
            # 主任务阶段
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

            # Feedback流程阶段
            "evaluating": {
                "resume_from_status": TaskStatus.COMPLETED,
                "files_to_keep": ["requirements.json", "templates.json", "plan.json", "generation_result.json"],
                "files_to_remove": ["feedback.json"]
            },
            "reflecting": {
                "resume_from_status": TaskStatus.COMPLETED,
                "files_to_keep": ["requirements.json", "templates.json", "plan.json", "generation_result.json", "feedback.json"],
                "files_to_remove": ["reflection.json"]
            },
            "curating": {
                "resume_from_status": TaskStatus.COMPLETED,
                "files_to_keep": ["requirements.json", "templates.json", "plan.json", "generation_result.json", "feedback.json", "reflection.json"],
                "files_to_remove": ["curation.json"]
            }
        }

        if failed_stage not in stage_mapping:
            raise ValueError(f"未知的失败阶段: {failed_stage}")

        info = stage_mapping[failed_stage]
        return {
            "strategy": "partial",
            "resume_from_stage": failed_stage,
            "resume_from_status": info["resume_from_status"],
            "files_to_keep": info["files_to_keep"],
            "files_to_remove": info["files_to_remove"],
            "playbook_action": "none"  # FAILED 任务不涉及 playbook 操作
        }

    def _prepare_cancelled_retry(
        self,
        task: GenerationTask,
        force_stage: Optional[str],
        keep_playbook: bool
    ) -> Dict:
        """准备CANCELLED任务的恢复（新增）"""
        # 检测恢复阶段
        resume_stage = force_stage or task.failed_stage or "extracting"

        # 别名映射
        stage_aliases = {"generate": "generating", "feedback": "evaluating"}
        if resume_stage in stage_aliases:
            resume_stage = stage_aliases[resume_stage]

        # 根据恢复阶段决定保留/删除文件（复用 stage_mapping）
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
        files_to_remove = info["files_to_remove"].copy()

        # 🔧 如果保留 playbook，不删除 curation.json
        # 让新的 Curator 覆盖它（新任务分身会生成新的 curation.json）
        if keep_playbook and "curation.json" in files_to_remove:
            files_to_remove.remove("curation.json")

        # 判断 playbook 操作
        playbook_action = self._determine_playbook_action(
            task, resume_stage, keep_playbook
        )

        return {
            "strategy": "resume_cancelled",
            "resume_from_stage": resume_stage,
            "resume_from_status": info["resume_from_status"],
            "files_to_keep": info["files_to_keep"],
            "files_to_remove": files_to_remove,
            "playbook_action": playbook_action
        }

    def _prepare_completed_retry(
        self,
        task: GenerationTask,
        force_stage: Optional[str],
        keep_playbook: bool
    ) -> Dict:
        """准备COMPLETED任务的重新生成（新增）"""
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
        files_to_remove = info["files_to_remove"].copy()

        # 🔧 如果保留 playbook，不删除 curation.json
        # 让新的 Curator 覆盖它（新任务分身会生成新的 curation.json）
        if keep_playbook and "curation.json" in files_to_remove:
            files_to_remove.remove("curation.json")

        # 判断 playbook 操作
        playbook_action = self._determine_playbook_action(
            task, resume_stage, keep_playbook
        )

        return {
            "strategy": "regenerate",
            "resume_from_stage": resume_stage,
            "resume_from_status": info["resume_from_status"],
            "files_to_keep": info["files_to_keep"],
            "files_to_remove": files_to_remove,
            "playbook_action": playbook_action
        }

    def validate_files(self, task: GenerationTask, files_to_keep: List[str]) -> List[str]:
        """验证文件完整性

        Args:
            task: 任务对象
            files_to_keep: 需要保留的文件列表

        Returns:
            损坏的文件列表
        """
        corrupted = []

        for filename in files_to_keep:
            filepath = task.task_dir / filename

            if not filepath.exists():
                corrupted.append(filename)
                continue

            # 验证文件内容
            try:
                if filename == "requirements.json":
                    req = task.load_requirements()
                    if not req or (not req.get("objective") and not req.get("target_compound")):
                        corrupted.append(filename)

                elif filename == "templates.json":
                    import json
                    with open(filepath, 'r') as f:
                        templates = json.load(f)
                    if not isinstance(templates, list):
                        corrupted.append(filename)

                elif filename == "plan.json":
                    import json
                    with open(filepath, 'r') as f:
                        plan = json.load(f)
                    if not plan or not plan.get("title"):
                        corrupted.append(filename)

                elif filename == "generation_result.json":
                    result = task.load_generation_result()
                    if not result or not result.get("plan"):
                        corrupted.append(filename)

                # 其他文件只验证JSON格式
                else:
                    import json
                    with open(filepath, 'r') as f:
                        json.load(f)

            except Exception as e:
                print(f"  ⚠️  文件验证失败: {filename} - {e}")
                corrupted.append(filename)

        return corrupted

    def clean_files(self, task: GenerationTask, files_to_remove: List[str]):
        """清理文件

        Args:
            task: 任务对象
            files_to_remove: 需要删除的文件列表
        """
        for filename in files_to_remove:
            filepath = task.task_dir / filename
            if filepath.exists():
                try:
                    filepath.unlink()
                    print(f"  🗑️  已删除: {filename}")
                except Exception as e:
                    print(f"  ⚠️  删除失败: {filename} - {e}")

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
            # 读取 curation.json，获取此任务的所有操作
            curation_file = task.task_dir / "curation.json"
            if not curation_file.exists():
                print("  ℹ️  未找到 curation.json，跳过 playbook 回滚")
                return True

            import json
            with open(curation_file, 'r', encoding='utf-8') as f:
                curation_result = json.load(f)

            # 提取需要回滚的操作
            added_bullet_ids = []
            updated_bullets = []  # [(bullet_id, old_content), ...]
            removed_bullets = []  # [完整的 bullet 对象, ...]

            for update in curation_result.get("delta_operations", []):
                operation = update.get("operation")

                if operation == "ADD":
                    # ADD 操作：记录需要删除的 bullet ID
                    # 🔧 修复：ADD 操作的 bullet_id 字段是 None，实际 ID 在 new_bullet.id 中
                    new_bullet = update.get("new_bullet")
                    if new_bullet:
                        bullet_id = new_bullet.get("id")
                        if bullet_id:
                            added_bullet_ids.append(bullet_id)

                elif operation == "UPDATE":
                    # UPDATE 操作：记录需要还原的 bullet 和旧内容
                    bullet_id = update.get("bullet_id")
                    old_content = update.get("old_content")
                    if bullet_id and old_content:
                        updated_bullets.append((bullet_id, old_content))

                elif operation == "REMOVE":
                    # REMOVE 操作：记录需要恢复的完整 bullet
                    removed_bullet = update.get("removed_bullet")
                    if removed_bullet:
                        removed_bullets.append(removed_bullet)

            if not added_bullet_ids and not updated_bullets and not removed_bullets:
                print("  ℹ️  此任务未修改 bullets，无需回滚")
                return True

            # 从 playbook 中回滚变更
            playbook_path = Path("data/playbooks/chemistry_playbook.json")

            with open(playbook_path, 'r', encoding='utf-8') as f:
                playbook = json.load(f)

            # 1. 移除 ADD 的 bullets
            original_count = len(playbook.get("bullets", []))
            playbook["bullets"] = [
                b for b in playbook.get("bullets", [])
                if b["id"] not in added_bullet_ids
            ]
            removed_count = original_count - len(playbook["bullets"])

            # 2. 还原 UPDATE 的 bullets
            restored_count = 0
            for bullet_id, old_content in updated_bullets:
                for bullet in playbook.get("bullets", []):
                    if bullet["id"] == bullet_id:
                        bullet["content"] = old_content
                        # 清除 embedding（需要重新计算）
                        if "metadata" in bullet and "embedding" in bullet["metadata"]:
                            bullet["metadata"]["embedding"] = None
                        restored_count += 1
                        break

            # 3. 恢复 REMOVE 的 bullets
            recovered_count = 0
            for removed_bullet in removed_bullets:
                # 检查 bullet 是否已存在（避免重复添加）
                bullet_exists = any(
                    b["id"] == removed_bullet["id"]
                    for b in playbook.get("bullets", [])
                )

                if not bullet_exists:
                    # 恢复被删除的 bullet
                    # 注意：embedding 可能为 None（因为 curation.json 保存时移除了 embedding）
                    # 这是正常的，下次 Curator 运行时会重新计算 embedding
                    playbook["bullets"].append(removed_bullet)
                    recovered_count += 1

            # 保存回滚后的 playbook
            with open(playbook_path, 'w', encoding='utf-8') as f:
                json.dump(playbook, f, ensure_ascii=False, indent=2)

            # 显示回滚结果
            print(f"  ✅ Playbook 已回滚:")
            if removed_count > 0:
                print(f"     - 移除 {removed_count} 个 bullets (ADD): {', '.join(added_bullet_ids)}")
            if restored_count > 0:
                print(f"     - 还原 {restored_count} 个 bullets (UPDATE): {', '.join([bid for bid, _ in updated_bullets])}")
            if recovered_count > 0:
                print(f"     - 恢复 {recovered_count} 个 bullets (REMOVE): {', '.join([b['id'] for b in removed_bullets])}")

            return True

        except Exception as e:
            print(f"  ⚠️  Playbook 回滚失败: {e}")
            import traceback
            traceback.print_exc()
            return False

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
        elif task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            print(f"  💡 检测到任务卡住（子进程已退出），视为失败重试")

        # 显示阶段信息
        if force_stage:
            print(f"  ✅ 指定阶段: {force_stage}")
        elif task.failed_stage:
            print(f"  ✅ 恢复阶段: {task.failed_stage}")
        elif task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            # 卡住状态：显示自动检测的阶段
            state_to_stage = {
                TaskStatus.PENDING: "extracting",
                TaskStatus.EXTRACTING: "extracting",
                TaskStatus.RETRIEVING: "retrieving",
                TaskStatus.GENERATING: "generating"
            }
            detected_stage = state_to_stage.get(task.status, "extracting")
            print(f"  ✅ 自动检测阶段: {detected_stage}")

        # 对 FAILED 和卡住状态显示重试次数
        if task.status == TaskStatus.FAILED or task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            print(f"  ✅ 重试次数: {task.retry_count}/{task.max_retries}")
            if task.error:
                print(f"  ℹ️  错误信息: {task.error[:100]}...")

        prep_info = self.prepare_retry(
            task,
            clean=clean,
            force_stage=force_stage,
            keep_playbook=keep_playbook
        )

        print(f"\n📋 重试策略: {prep_info['strategy']}")
        print(f"  - 从阶段开始: {prep_info['resume_from_stage']}")
        print(f"  - 恢复到状态: {prep_info['resume_from_status'].value}")

        # 3. Playbook 操作（关键新增）
        if prep_info['playbook_action'] == 'rollback':
            print(f"\n🔄 回滚 Playbook...")
            self._rollback_playbook(task)

        # 4. 验证文件
        if prep_info['files_to_keep']:
            print(f"\n🔍 验证文件完整性...")
            corrupted = self.validate_files(task, prep_info['files_to_keep'])

            if corrupted:
                print(f"  ⚠️  发现损坏文件: {', '.join(corrupted)}")
                print(f"  ⚠️  建议使用 --clean 模式完全重试")

                # 将损坏文件加入删除列表
                prep_info['files_to_remove'].extend(corrupted)
                prep_info['files_to_keep'] = [f for f in prep_info['files_to_keep'] if f not in corrupted]

        # 5. 清理文件
        if prep_info['files_to_remove']:
            print(f"\n🗑️  清理文件...")
            self.clean_files(task, prep_info['files_to_remove'])

        # 6. 记录重试历史
        retry_record = {
            "timestamp": datetime.now().isoformat(),
            "operation": self._get_operation_type(task.status),
            "previous_status": task.status.value,
            "retry_count": task.retry_count + 1 if task.status != TaskStatus.CANCELLED else 0,
            "previous_error": task.error if (task.status == TaskStatus.FAILED or task.status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]) else None,
            "previous_stage": task.failed_stage,
            "strategy": prep_info['strategy'],
            "playbook_action": prep_info['playbook_action']
        }
        task.retry_history.append(retry_record)

        # 7. 更新任务状态
        task.status = prep_info['resume_from_status']
        task.error = None  # 清除错误信息
        task.failed_stage = None  # 清除失败阶段

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

        # Feedback流程重置
        if prep_info['resume_from_stage'] in ['evaluating', 'reflecting', 'curating']:
            task.feedback_status = "pending"
            task.feedback_error = None

        # 8. 保存任务
        self.task_manager._save_task(task)

        print(f"\n✅ 重试准备完成")
        print(f"  - 任务状态已更新: {task.status.value}")

        return True

    def _get_operation_type(self, status: TaskStatus) -> str:
        """获取操作类型（用于审计日志）"""
        if status == TaskStatus.FAILED:
            return "retry"
        elif status == TaskStatus.CANCELLED:
            return "resume_cancelled"
        elif status == TaskStatus.COMPLETED:
            return "regenerate"
        elif status in [TaskStatus.PENDING, TaskStatus.EXTRACTING, TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
            # 卡住的中间状态：视为失败重试
            return "retry"
        else:
            return "unknown"
