# LargeRAG 使用指南

## 📋 概述

这是一个基于 LlamaIndex 和 DashScope (Qwen) 的生产级 RAG 系统。

**当前状态**：
- ✅ 使用**文献数据**作为临时测试数据（10 篇双相不锈钢相关论文）
- ⏳ 未来将替换为**实验方案模板库**
- ✅ 基于 Docling 的 PDF 处理工具已集成

**核心特性**：
- ✅ DashScope 原生支持（Qwen embeddings + LLM + reranker）
- ✅ 本地文件缓存（无需 Redis，100x 加速）
- ✅ 两阶段检索（向量检索 + 重排序）
- ✅ 配置驱动（YAML 配置文件）
- ✅ 完整的测试和文档

---

## 🚀 快速开始

### 1. 激活 Conda 环境

```bash
conda activate OntologyConstruction
```

### 2. 安装依赖

```bash
cd /home/syk/projects/experiment-plan-design/src/external/rag
pip install -r requirements.txt
```

### 3. 配置环境变量

确保 `.env` 文件包含：

```bash
# 在项目根目录的 .env 文件中
DASHSCOPE_API_KEY=your_api_key_here
PROJECT_ROOT=/home/syk/projects/experiment-plan-design/
```

### 4. 基本使用

```python
from src.external.rag import LargeRAG

# 初始化（会自动加载已有索引）
rag = LargeRAG()

# 第一次使用：构建索引
# 注意：目前 data/literature/ 包含 DES 论文数据，你需要替换为实验方案模板
rag.index_from_folders("src/external/rag/data/templates")

# 检索相似文档（推荐用于 Generator）
docs = rag.get_similar_docs(
    query="阿司匹林合成实验方案",
    top_k=8
)

# 打印检索结果
for i, doc in enumerate(docs):
    print(f"\n=== 文档 {i+1} ===")
    print(f"相似度分数: {doc['score']}")
    print(f"内容: {doc['text'][:200]}...")
    print(f"元数据: {doc['metadata']}")

# 如果需要 LLM 生成回答（可选）
answer = rag.query("如何合成阿司匹林？")
print(answer)
```

---

## 📁 数据准备

### 当前数据结构（需要替换）

```
src/external/rag/data/literature/
├── {hash1}/
│   ├── content_list_process.json  ← 优先使用
│   ├── article.json               ← 备选
│   └── {hash1}.md                 （忽略）
└── {hash2}/
    └── ...
```

### 推荐的实验方案模板结构

有两个选择：

#### 选项 A：保持原有文件夹结构

```
src/external/rag/data/templates/
├── aspirin_synthesis/
│   └── content_list_process.json   # 包含结构化的实验步骤
├── benzoin_synthesis/
│   └── content_list_process.json
└── ...
```

`content_list_process.json` 格式：
```json
{
  "pdf_path": "templates/aspirin_synthesis.pdf",
  "content_list": [
    {
      "page_idx": 1,
      "text_level": 1,
      "text": "## 阿司匹林合成实验方案\n\n### 实验目的\n合成乙酰水杨酸（阿司匹林）...",
      "has_citations": false
    },
    {
      "page_idx": 1,
      "text_level": 2,
      "text": "### 实验原理\n水杨酸与乙酸酐在酸催化下发生酰化反应...",
      "has_citations": true
    }
  ]
}
```

#### 选项 B：使用简化的 article.json

```json
{
  "paper_id": "aspirin_synthesis_v1",
  "title": "阿司匹林合成实验方案",
  "paragraphs": [
    {
      "text": "实验目的：合成乙酰水杨酸...",
      "section": "objective"
    },
    {
      "text": "所需材料：水杨酸 2.0g，乙酸酐 3.0ml...",
      "section": "materials"
    }
  ]
}
```

### 数据迁移步骤

```bash
# 1. 备份原有 DES 文献数据（可选）
mv src/external/rag/data/literature src/external/rag/data/literature_backup

# 2. 创建模板目录
mkdir -p src/external/rag/data/templates

# 3. 将你的实验方案模板放入 templates/ 目录
# （按照上述格式准备 JSON 文件）

# 4. 构建索引
python -c "
from src.external.rag import LargeRAG
rag = LargeRAG()
rag.index_from_folders('src/external/rag/data/templates')
print('索引构建完成！')
"
```

---

## ⚙️ 配置说明

### 配置文件位置

`src/external/rag/config/settings.yaml`

### 关键配置项（已本地化）

```yaml
# 向量存储
vector_store:
  persist_directory: "${PROJECT_ROOT}src/external/rag/data/chroma_db"
  collection_name: "experiment_plan_templates_v1"  # 已更新

# 检索参数（已优化）
retrieval:
  similarity_top_k: 30      # 向量召回候选数（增加）
  rerank_top_n: 8           # 重排序后返回数（适合实验方案）
  similarity_threshold: 0.5 # 过滤低质量文档

# LLM 配置（已优化成本）
llm:
  model: "qwen-plus"        # 改为 qwen-plus（更便宜）
  temperature: 0            # 确定性生成
```

### 配置调优建议

**提高召回率**（可能召回不相关文档）：
```yaml
retrieval:
  similarity_top_k: 50
  rerank_top_n: 10
  similarity_threshold: 0.3
```

**提高精准度**（可能遗漏相关文档）：
```yaml
retrieval:
  similarity_top_k: 20
  rerank_top_n: 5
  similarity_threshold: 0.7
```

---

## 🔌 集成到项目

### 在 ACE Generator 中使用

```python
# src/ace_framework/generator/generator.py

from src.external.rag import LargeRAG

class ExperimentPlanGenerator:
    def __init__(self):
        self.rag = LargeRAG()

    def generate_plan(self, requirements: dict, playbook: Playbook):
        """生成实验方案"""

        # 1. 使用 RAG 检索相关模板
        query = f"合成 {requirements['target_compound']} 的实验方案"
        templates = self.rag.get_similar_docs(query, top_k=8)

        # 2. 构建 prompt（需求 + 模板 + playbook）
        prompt = self._build_prompt(
            requirements=requirements,
            templates=templates,
            playbook=playbook
        )

        # 3. 调用 LLM 生成方案
        plan = self.llm.generate(prompt)

        return plan

    def _build_prompt(self, requirements, templates, playbook):
        template_context = "\n\n".join([
            f"【参考模板 {i+1}】\n{t['text']}"
            for i, t in enumerate(templates)
        ])

        return f"""
## 任务
根据用户需求和参考模板，生成实验方案。

## 用户需求
{requirements}

## 参考模板
{template_context}

## Playbook 指导
{playbook.render()}

## 输出
请生成完整的实验方案...
"""
```

### 在 Task Worker 中使用

```python
# src/workflow/task_worker.py

from src.external.rag import LargeRAG

class GenerationTask:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.rag = LargeRAG()  # 在子进程中初始化

    def step_retrieve_templates(self):
        """RETRIEVING 步骤"""

        # 加载需求
        requirements = self._load_requirements()

        # RAG 检索
        query = f"{requirements['target_compound']} synthesis experiment"
        templates = self.rag.get_similar_docs(query, top_k=8)

        # 保存到文件
        self._save_templates(templates)

        self._update_status("GENERATING")
```

---

## 📊 性能指标

### 索引构建时间

| 文档数量 | 首次构建 | 使用缓存 |
|---------|---------|---------|
| 35 篇论文（~8000 段） | 1-3 分钟 | <10 秒 |
| 100 个模板（预估） | 3-5 分钟 | <15 秒 |

### 查询性能

| 操作 | 耗时 |
|-----|-----|
| `get_similar_docs()` | 2-5 秒 |
| `query()` (含 LLM) | 5-10 秒 |

---

## 🧪 测试

### 运行示例

```bash
cd src/external/rag

# 示例 1：构建索引
python examples/1_build_index.py

# 示例 2：查询和检索
python examples/2_query_and_retrieve.py
```

### 运行测试

```bash
cd src/external/rag
pytest tests/
```

---

## 🔍 常见问题

### Q1: 为什么有两个配置文件？

- **`src/external/rag/config/settings.yaml`**: LargeRAG 内部配置（DashScope 模型、Chroma 参数）
- **`configs/rag_config.yaml`**: 项目级配置（原计划用于本地 embedding）

**推荐**：使用 `src/external/rag/config/settings.yaml`，这是 LargeRAG 实际使用的配置。

### Q2: 如何切换到本地 embedding 模型？

LargeRAG 当前硬编码使用 DashScope embeddings。如果需要本地模型（如 `BAAI/bge-large-zh-v1.5`），需要修改 `core/indexer.py`：

```python
# 原代码（DashScope）
from llama_index.embeddings.dashscope import DashScopeEmbedding

# 修改为（本地）
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-large-zh-v1.5",
    device="cpu"
)
```

### Q3: 数据目录在哪里？

```
src/external/rag/data/
├── templates/        # 你的实验方案模板（需要准备）
├── chroma_db/        # 向量索引（自动生成）
├── cache/            # Embedding 缓存（自动生成）
└── literature/       # DES 论文（原有数据，可删除）
```

### Q4: 如何查看系统统计信息？

```python
from src.external.rag import LargeRAG

rag = LargeRAG()
stats = rag.get_stats()
print(stats)
# 输出：
# {
#   'total_documents': 35,
#   'total_nodes': 8234,
#   'embedding_dimension': 1024,
#   'cache_enabled': True,
#   'vector_store_type': 'chroma'
# }
```

---

## 📚 推荐阅读顺序

1. **本文件** - 使用指南（你正在看）
2. **examples/README.md** - 详细示例和最佳实践
3. **MIGRATION_COMPLETION_REPORT.md** - OpenAI → DashScope 迁移背景
4. **docs/cache_guide.md** - 缓存系统详解（可选）

---

## 🎯 下一步

- [ ] 准备实验方案模板数据（JSON 格式）
- [ ] 替换 `data/literature/` 为 `data/templates/`
- [ ] 运行 `examples/1_build_index.py` 构建索引
- [ ] 在 `src/ace_framework/generator/` 中集成 RAG
- [ ] 编写集成测试

---

## 🆘 问题反馈

如有问题，请检查：

1. **日志文件**: `logs/largerag.log`
2. **配置验证**: 确保 `DASHSCOPE_API_KEY` 正确设置
3. **依赖安装**: `pip list | grep llama-index`

---

**最后更新**: 2025-10-26
