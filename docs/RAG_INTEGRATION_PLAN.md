# Generator 集成真实 RAG 方案设计

## 📋 当前架构分析

### 1. Mock RAG 使用位置

**文件**: `src/workflow/task_worker.py`（第305-312行）

```python
# 使用Mock RAG检索
try:
    from workflow.mock_rag import create_mock_rag_retriever
    mock_rag = create_mock_rag_retriever()
    templates = mock_rag.retrieve(requirements, top_k=3)
    print(f"✅ 检索到 {len(templates)} 个模板（使用Mock RAG）")
except Exception as e:
    print(f"⚠️  Mock RAG失败: {e}，使用空模板列表")
    templates = []
```

### 2. Generator 接口分析

**文件**: `src/ace_framework/generator/generator.py`（第77-83行）

```python
def generate(
    self,
    requirements: Dict[str, Any],
    templates: Optional[List[Dict]] = None,  # RAG检索的模板
    few_shot_examples: Optional[List[Dict]] = None,
    section_filter: Optional[List[str]] = None
) -> GenerationResult:
```

**要求**：
- `templates` 参数是 `List[Dict]`
- 每个 Dict 应包含模板内容

### 3. 数据流

```
User Input (对话历史)
    ↓
MOSES提取需求 (requirements.json)
    ↓
RAG检索模板 (templates.json) ← 【替换点】
    ↓
Generator生成方案 (plan.json)
```

---

## 🎯 集成方案设计

### 方案概述

**核心思路**：在 `task_worker.py` 中替换 Mock RAG 调用为 LargeRAG，确保返回格式兼容。

### 详细设计

#### **1. 创建 RAG 适配器模块**

**新建文件**: `src/workflow/rag_adapter.py`

**目的**：
- 封装 LargeRAG 调用逻辑
- 处理格式转换（LargeRAG输出 → Generator需要的格式）
- 统一错误处理
- 支持配置化（路径、top_k等）

**接口设计**：
```python
class RAGAdapter:
    """RAG检索适配器 - 统一RAG接口"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化

        Args:
            config_path: RAG配置文件路径（可选）
        """
        pass

    def retrieve_templates(
        self,
        requirements: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict]:
        """检索相关模板

        Args:
            requirements: 结构化需求
            top_k: 返回模板数量

        Returns:
            模板列表，每个模板是Dict，包含:
            - title: str
            - content: str (完整文本)
            - metadata: Dict (source, score等)
        """
        pass
```

#### **2. 实现 RAG 适配器**

**核心逻辑**：

```python
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# 添加 src/external/rag 到路径
rag_path = Path(__file__).parent.parent / "external" / "rag"
if str(rag_path) not in sys.path:
    sys.path.insert(0, str(rag_path))

from src.external.rag import LargeRAG


class RAGAdapter:
    def __init__(self, config_path: Optional[str] = None):
        """惰性初始化 - 只在第一次调用时初始化LargeRAG"""
        self.config_path = config_path
        self._rag = None  # 延迟初始化

    def _ensure_initialized(self):
        """确保RAG已初始化"""
        if self._rag is None:
            print("[RAGAdapter] 初始化 LargeRAG...")
            self._rag = LargeRAG(config_path=self.config_path)
            print("[RAGAdapter] ✅ LargeRAG 初始化完成")

    def retrieve_templates(
        self,
        requirements: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict]:
        """检索相关模板"""
        self._ensure_initialized()

        # 1. 构建查询字符串
        query = self._build_query(requirements)
        print(f"[RAGAdapter] 查询: {query}")

        # 2. 调用 LargeRAG
        try:
            docs = self._rag.get_similar_docs(
                query=query,
                top_k=top_k
            )
            print(f"[RAGAdapter] 检索到 {len(docs)} 个相关文档")

        except Exception as e:
            print(f"[RAGAdapter] ❌ 检索失败: {e}")
            return []

        # 3. 格式转换
        templates = self._convert_to_template_format(docs)

        return templates

    def _build_query(self, requirements: Dict[str, Any]) -> str:
        """从requirements构建查询字符串"""
        parts = []

        if "objective" in requirements:
            parts.append(requirements["objective"])

        if "target_compound" in requirements:
            parts.append(f"{requirements['target_compound']}")

        if "constraints" in requirements and requirements["constraints"]:
            parts.append(" ".join(requirements["constraints"]))

        return " ".join(parts)

    def _convert_to_template_format(self, docs: List[Dict]) -> List[Dict]:
        """
        将 LargeRAG 输出转换为 Generator 需要的格式

        LargeRAG输出格式:
        {
            "text": "文档内容",
            "score": 0.85,
            "metadata": {"doc_hash": "xxx", ...}
        }

        Generator需要格式:
        {
            "title": "模板标题",
            "content": "模板内容",
            "source": "来源",
            "score": 0.85
        }
        """
        templates = []

        for i, doc in enumerate(docs, 1):
            template = {
                "title": f"检索文档 {i}",  # 可以从metadata提取
                "content": doc["text"],
                "source": doc.get("metadata", {}).get("doc_hash", "unknown"),
                "score": doc.get("score", 0.0),
                "metadata": doc.get("metadata", {})
            }
            templates.append(template)

        return templates
```

#### **3. 修改 task_worker.py**

**位置**: `src/workflow/task_worker.py` 第283-318行

**修改前**:
```python
# Step 2: RAG检索模板
if task.status in [TaskStatus.AWAITING_CONFIRM, TaskStatus.RETRIEVING]:
    print()
    print("=" * 70)
    print("STEP 2: RAG检索模板")
    print("=" * 70)

    task.status = TaskStatus.RETRIEVING
    task_manager._save_task(task)

    # 加载需求
    requirements = task.load_requirements()
    if not requirements:
        task.status = TaskStatus.FAILED
        task.error = "需求文件不存在或已损坏"
        task_manager._save_task(task)
        print(f"❌ {task.error}")
        sys.exit(1)

    # 使用Mock RAG检索
    try:
        from workflow.mock_rag import create_mock_rag_retriever
        mock_rag = create_mock_rag_retriever()
        templates = mock_rag.retrieve(requirements, top_k=3)
        print(f"✅ 检索到 {len(templates)} 个模板（使用Mock RAG）")
    except Exception as e:
        print(f"⚠️  Mock RAG失败: {e}，使用空模板列表")
        templates = []

    # 保存templates到文件
    task.save_templates(templates)
    print(f"✅ 检索结果已保存: {task.templates_file}")
```

**修改后**:
```python
# Step 2: RAG检索模板
if task.status in [TaskStatus.AWAITING_CONFIRM, TaskStatus.RETRIEVING]:
    print()
    print("=" * 70)
    print("STEP 2: RAG检索模板")
    print("=" * 70)

    task.status = TaskStatus.RETRIEVING
    task_manager._save_task(task)

    # 加载需求
    requirements = task.load_requirements()
    if not requirements:
        task.status = TaskStatus.FAILED
        task.error = "需求文件不存在或已损坏"
        task_manager._save_task(task)
        print(f"❌ {task.error}")
        sys.exit(1)

    # 使用真实 RAG 检索
    try:
        from workflow.rag_adapter import RAGAdapter

        # 初始化 RAG 适配器
        rag_adapter = RAGAdapter()

        # 检索模板（使用配置的 top_k，默认5）
        templates = rag_adapter.retrieve_templates(
            requirements=requirements,
            top_k=5  # 可以从配置读取
        )

        print(f"✅ 检索到 {len(templates)} 个相关文档")

        # 打印前3个结果预览
        for i, t in enumerate(templates[:3], 1):
            print(f"  {i}. 分数: {t.get('score', 0):.3f} | 来源: {t.get('source', 'unknown')[:20]}...")

    except Exception as e:
        import traceback
        print(f"⚠️  RAG检索失败: {e}")
        traceback.print_exc()
        print("⚠️  回退到空模板列表")
        templates = []

    # 保存templates到文件
    task.save_templates(templates)
    print(f"✅ 检索结果已保存: {task.templates_file}")
```

#### **4. 配置管理**

**位置**: `configs/ace_config.yaml` 或新建 `configs/workflow_config.yaml`

```yaml
# RAG配置（用于workflow）
rag:
  enabled: true
  top_k: 5  # 检索模板数量
  min_score: 0.5  # 最低相似度阈值（可选）
  data_source: "test_papers"  # 或 "templates"（未来）

  # LargeRAG 配置文件路径（可选，使用默认则留空）
  config_path: null  # 或 "src/external/rag/config/settings.yaml"
```

**读取配置**（在 rag_adapter.py 中）：
```python
from utils.config_loader import load_config

def get_rag_config():
    """获取RAG配置"""
    config = load_config("configs/workflow_config.yaml")
    return config.get("rag", {})

class RAGAdapter:
    def __init__(self):
        self.config = get_rag_config()
        self.enabled = self.config.get("enabled", True)
        self.default_top_k = self.config.get("top_k", 5)
        # ...
```

---

## 🔍 关键考虑

### 1. **格式兼容性**

**LargeRAG 输出**：
```python
[
    {
        "text": "双相不锈钢的点蚀行为...",
        "score": 0.85,
        "metadata": {"doc_hash": "xxx", "page_idx": 0, ...}
    },
    ...
]
```

**Generator 期望输入**：
```python
[
    {
        "title": "文档标题",
        "content": "完整内容",
        # 其他字段可选
    },
    ...
]
```

**适配器负责转换**：`_convert_to_template_format()`

### 2. **错误处理**

**策略**：
- RAG初始化失败 → 打印警告，返回空列表（继续执行）
- 检索失败 → 打印错误，返回空列表（继续执行）
- Generator可以在没有templates的情况下运行（仅使用playbook）

**原因**：
- RAG是增强功能，不是必需功能
- Playbook本身就包含知识
- 避免单点故障

### 3. **性能优化**

**惰性初始化**：
- LargeRAG 在第一次调用时才初始化
- 避免不必要的索引加载

**缓存**（可选，后期优化）：
- 同一个requirements可能被多次检索
- 可以在session级别缓存检索结果

### 4. **测试策略**

**单元测试** (`tests/workflow/test_rag_adapter.py`):
```python
def test_rag_adapter_format_conversion():
    """测试格式转换"""
    adapter = RAGAdapter()

    # Mock LargeRAG输出
    mock_docs = [
        {"text": "测试内容", "score": 0.9, "metadata": {"doc_hash": "abc123"}}
    ]

    templates = adapter._convert_to_template_format(mock_docs)

    assert len(templates) == 1
    assert "content" in templates[0]
    assert templates[0]["content"] == "测试内容"
```

**集成测试**：
```bash
# 使用真实RAG运行完整workflow
conda activate OntologyConstruction
cd /home/syk/projects/experiment-plan-design
python -m workflow.task_worker test_task_123
```

---

## 📝 实施步骤

### Phase 1: 创建适配器（优先）
1. ✅ 创建 `src/workflow/rag_adapter.py`
2. ✅ 实现基础接口（无配置，硬编码参数）
3. ✅ 测试格式转换逻辑

### Phase 2: 集成到 task_worker（核心）
4. ✅ 修改 `src/workflow/task_worker.py`
5. ✅ 替换 Mock RAG 调用
6. ✅ 添加错误处理和日志

### Phase 3: 配置和优化（增强）
7. ⏳ 添加配置文件支持
8. ⏳ 实现惰性初始化
9. ⏳ 添加性能监控

### Phase 4: 测试和文档（验证）
10. ⏳ 编写单元测试
11. ⏳ 运行端到端测试
12. ⏳ 更新文档

---

## ⚠️ 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| RAG初始化慢 | 首次调用延迟高 | 惰性初始化，只在需要时加载 |
| 检索质量差 | 生成方案质量下降 | 保留空templates兜底，Generator仍可使用playbook |
| 格式不兼容 | Generator解析失败 | 适配器严格转换格式，添加schema验证 |
| OntologyConstruction环境问题 | 导入失败 | 明确文档说明环境要求，添加环境检查 |
| 路径问题 | 找不到RAG模块 | 使用绝对路径，添加sys.path处理 |

---

## 🎯 预期效果

### 功能改进
- ✅ 真实文献数据检索（当前10篇双相不锈钢论文）
- ✅ 语义相似度匹配（vs 关键词匹配）
- ✅ 支持大规模文档库（vs 手工mock数据）

### 性能指标
- **检索时间**: 2-5秒（含向量检索+重排序）
- **准确率**: 取决于文档质量和查询构建
- **首次加载**: ~10秒（索引加载）

### 可扩展性
- ✅ 未来轻松替换数据源（test_papers → templates）
- ✅ 支持配置化调优（top_k, threshold等）
- ✅ 为ACE训练循环做准备（templates作为few-shot）

---

## 📚 相关文件

**需要新建**:
- `src/workflow/rag_adapter.py`
- `tests/workflow/test_rag_adapter.py`
- `configs/workflow_config.yaml`（可选）

**需要修改**:
- `src/workflow/task_worker.py`（第305-312行）

**可以保留**（向后兼容）:
- `src/workflow/mock_rag.py`（作为fallback或测试用）

---

**方案设计完成日期**: 2025-10-26
**设计者**: Claude Code
**状态**: 待审阅
