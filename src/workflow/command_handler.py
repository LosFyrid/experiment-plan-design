"""命令处理器 - 处理/generate等命令

负责整个生成工作流的编排：
1. 提取需求（保存到文件）
2. 等待用户确认
3. RAG检索（保存到文件）
4. Generator生成（保存到文件）
"""

import time
import json
from typing import Dict, Any, Optional

from workflow.task_manager import (
    get_task_manager,
    TaskStatus,
    GenerationTask,
    LogWriter
)
from chatbot.chatbot import Chatbot
from ace_framework.generator.generator import PlanGenerator
from utils.llm_provider import BaseLLMProvider, extract_json_from_text


class GenerateCommandHandler:
    """处理/generate命令"""

    def __init__(
        self,
        chatbot: Chatbot,
        generator: PlanGenerator,
        llm_provider: BaseLLMProvider
    ):
        self.chatbot = chatbot
        self.generator = generator
        self.llm = llm_provider
        self.task_manager = get_task_manager()

        # 确保任务管理器已启动
        self.task_manager.start(as_daemon=False)

    def handle(self, session_id: str) -> str:
        """处理/generate命令（非阻塞）

        Args:
            session_id: 会话ID

        Returns:
            task_id
        """
        # 提交后台任务
        task_id = self.task_manager.submit_task(
            session_id=session_id,
            handler=self._generate_workflow,
            chatbot=self.chatbot,
            generator=self.generator,
            llm=self.llm
        )

        return task_id

    @staticmethod
    def _generate_workflow(
        task: GenerationTask,
        log: LogWriter,
        chatbot: Chatbot,
        generator: PlanGenerator,
        llm: BaseLLMProvider
    ):
        """生成工作流（在后台线程执行）

        Args:
            task: 任务对象
            log: 日志写入器
            chatbot: Chatbot实例
            generator: Generator实例
            llm: LLM Provider实例
        """
        task_manager = get_task_manager()

        # ================================================================
        # Step 1: 提取需求
        # ================================================================
        task.status = TaskStatus.EXTRACTING
        task_manager._save_task(task)

        log.write("=" * 60)
        log.write("STEP 1: 提取需求")
        log.write("=" * 60)

        # 获取对话历史
        history = chatbot.get_history(task.session_id)

        if len(history) < 2:
            task.status = TaskStatus.FAILED
            task.error = "对话内容不足（至少需要2条消息）"
            task_manager._save_task(task)
            log.write(f"失败: {task.error}")
            return

        log.write(f"对话历史: {len(history)}条消息")

        # 调用LLM提取需求
        try:
            requirements = GenerateCommandHandler._extract_requirements(
                history, llm, log
            )
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"需求提取失败: {str(e)}"
            task_manager._save_task(task)
            log.write(f"失败: {task.error}")
            return

        # 验证必需字段
        if not requirements.get("target_compound") and not requirements.get("objective"):
            task.status = TaskStatus.FAILED
            task.error = "无法提取足够信息（缺少target_compound和objective）"
            task_manager._save_task(task)
            log.write(f"失败: {task.error}")
            return

        # 保存需求到文件
        task.save_requirements(requirements)
        log.write(f"需求已提取并保存: {task.requirements_file}")
        log.write(f"  - objective: {requirements.get('objective', 'N/A')}")
        log.write(f"  - target_compound: {requirements.get('target_compound', 'N/A')}")
        if requirements.get("constraints"):
            log.write(f"  - constraints: {len(requirements['constraints'])}项")

        # ================================================================
        # Step 2: 等待用户确认
        # ================================================================
        task.status = TaskStatus.AWAITING_CONFIRM
        task_manager._save_task(task)

        log.write("")
        log.write("=" * 60)
        log.write("STEP 2: 等待用户确认")
        log.write("=" * 60)
        log.write("任务已暂停，等待用户确认需求")
        log.write(f"用户可查看文件: {task.requirements_file}")
        log.write(f"用户可使用命令: /status, /confirm, /cancel")

        # 轮询等待用户确认
        check_interval = 0.5  # 500ms检查一次
        while True:
            time.sleep(check_interval)

            # 重新加载任务状态（可能被用户修改）
            task = task_manager.get_task(task.task_id)
            if not task:
                log.write("错误: 任务对象丢失")
                return

            # 检查状态变化
            if task.status == TaskStatus.CANCELLED:
                log.write("用户取消任务")
                return

            if task.status != TaskStatus.AWAITING_CONFIRM:
                # 用户已确认（通过/confirm命令）
                log.write("用户已确认需求，继续生成")
                break

        # 重新加载需求（用户可能手动修改了文件）
        requirements = task.load_requirements()
        if not requirements:
            task.status = TaskStatus.FAILED
            task.error = "需求文件不存在或已损坏"
            task_manager._save_task(task)
            log.write(f"失败: {task.error}")
            return

        log.write("需求已确认（可能已被用户修改）")

        # ================================================================
        # Step 3: RAG检索
        # ================================================================
        task.status = TaskStatus.RETRIEVING
        task_manager._save_task(task)

        log.write("")
        log.write("=" * 60)
        log.write("STEP 3: RAG检索模板")
        log.write("=" * 60)

        # 使用Mock RAG检索（端到端测试）
        # TODO: 替换为真实RAG实现
        try:
            from workflow.mock_rag import create_mock_rag_retriever
            mock_rag = create_mock_rag_retriever()
            templates = mock_rag.retrieve(requirements, top_k=3)
            log.write(f"检索到 {len(templates)} 个模板（使用Mock RAG）")
        except Exception as e:
            log.write(f"Mock RAG失败: {e}，使用空模板列表")
            templates = []

        # 保存templates到文件
        task.save_templates(templates)
        log.write(f"检索结果已保存: {task.templates_file}")

        # ================================================================
        # Step 4: 生成方案
        # ================================================================
        task.status = TaskStatus.GENERATING
        task_manager._save_task(task)

        log.write("")
        log.write("=" * 60)
        log.write("STEP 4: 生成实验方案")
        log.write("=" * 60)

        try:
            generation_result = generator.generate(
                requirements=requirements,
                templates=templates
            )

            # 保存方案到文件
            task.save_plan(generation_result.generated_plan)
            task.metadata = generation_result.generation_metadata

            log.write(f"方案已生成并保存: {task.plan_file}")
            log.write(f"方案标题: {generation_result.generated_plan.title}")
            log.write(f"耗时: {task.metadata.get('duration', 0):.2f}s")
            log.write(f"Tokens: {task.metadata.get('total_tokens', 0)}")
            log.write(f"使用bullets: {task.metadata.get('retrieved_bullets_count', 0)}个")

            # 完成
            task.status = TaskStatus.COMPLETED
            task_manager._save_task(task)

            log.write("")
            log.write("=" * 60)
            log.write("任务完成！")
            log.write("=" * 60)

        except Exception as e:
            import traceback
            task.status = TaskStatus.FAILED
            task.error = f"生成失败: {str(e)}"
            task_manager._save_task(task)

            log.write(f"失败: {task.error}")
            log.write(traceback.format_exc())

    @staticmethod
    def _extract_requirements(
        history: list,
        llm: BaseLLMProvider,
        log: LogWriter
    ) -> Dict[str, Any]:
        """从对话历史提取需求

        Args:
            history: 对话历史
            llm: LLM Provider
            log: 日志写入器

        Returns:
            requirements字典

        Raises:
            ValueError: 提取失败
        """
        EXTRACTION_PROMPT = """分析以下对话历史，提取实验需求信息。

# 对话历史
{history}

# 任务
提取以下信息（未提及的字段设为null）：

1. **target_compound**: 目标化合物名称（必需）
2. **objective**: 实验目标描述（必需，建议格式："反应类型+合成+化合物"或简洁描述）
3. **constraints**: 约束条件列表（如"2小时内"、"使用基础设备"、"成本<500元"）
4. **materials**: 材料列表（如果明确提到）
5. **special_requirements**: 特殊要求（如"需要在通风橱操作"）

# 输出格式
只输出JSON，格式：
```json
{{
  "target_compound": "化合物名称",
  "objective": "实验目标描述",
  "constraints": ["约束1", "约束2"],
  "materials": [{{"name": "材料名", "amount": "10g", "purity": "99%"}}],
  "special_requirements": "特殊要求"
}}
```

**重要规则**：
- target_compound和objective至少要有一个
- constraints必须是具体的字符串列表，不要只写"是"/"否"
- 没提到的字段用null
- 只输出JSON，不要其他文字
"""

        # 格式化对话历史
        formatted_history = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
            for msg in history
        ])

        prompt = EXTRACTION_PROMPT.format(history=formatted_history)

        # 调用LLM
        log.write("调用LLM提取需求...")
        response = llm.generate(
            prompt=prompt,
            system_prompt="你是化学实验需求分析专家。请仔细分析对话，提取结构化信息。"
        )

        log.write(f"LLM响应: {len(response.content)}字符")

        # 解析JSON
        try:
            requirements = json.loads(response.content.strip())
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            requirements = extract_json_from_text(response.content)
            if not requirements:
                raise ValueError(f"无法解析LLM响应为JSON: {response.content[:200]}")

        # 清理空值
        requirements = {
            k: v for k, v in requirements.items()
            if v not in [None, [], "", {}]
        }

        log.write(f"提取到 {len(requirements)} 个字段")

        return requirements
