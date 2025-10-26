# RAG 系统使用总结

## ✅ 已完成的工作

1. **复制并本地化 pdf_chunk_processor.py**
   - 从 MOSES 项目复制
   - 修改路径配置为 RAG 专用
   - 输出格式改为 `content_list_process.json`

2. **处理测试 PDF 文献**
   - 使用 **OntologyConstruction** conda 环境
   - 成功处理 10 篇双相不锈钢文献
   - 生成约 200+ 文本 chunks

3. **配置更新**
   - `config/settings.yaml` 添加数据路径配置
   - 索引路径：`${PROJECT_ROOT}src/external/rag/data/test_papers`

## 📊 处理结果

```
总 PDF 文件: 10
成功处理: 10
失败: 0
提取 DOI: 10/10
```

## 🚀 快速使用

### 1. 构建索引

```bash
conda activate OntologyConstruction
cd /home/syk/projects/experiment-plan-design/src/external/rag

# 使用 examples/1_build_index.py 或直接使用 LargeRAG
python -c "
from src.external.rag import LargeRAG
rag = LargeRAG()
rag.index_from_folders('data/test_papers')
print('索引构建完成！')
"
```

### 2. 检索测试

```python
from src.external.rag import LargeRAG

# 初始化
rag = LargeRAG()

# 检索相似文档
docs = rag.get_similar_docs(
    query="双相不锈钢的点蚀行为",
    top_k=5
)

# 查看结果
for i, doc in enumerate(docs):
    print(f"文档 {i+1}: {doc['text'][:100]}...")
    print(f"分数: {doc['score']}\n")
```

### 3. 集成到 Generator

```python
# src/ace_framework/generator/generator.py
from src.external.rag import LargeRAG

class ExperimentPlanGenerator:
    def __init__(self):
        self.rag = LargeRAG()

    def generate_plan(self, requirements: dict, playbook):
        # 检索相关模板/文献
        query = f"{requirements['target_compound']} 实验"
        templates = self.rag.get_similar_docs(query, top_k=8)

        # 使用模板生成方案
        ...
```

## 📝 重要说明

### 当前状态
- ✅ 使用**文献数据**作为临时测试（10 篇双相不锈钢论文）
- ⏳ 未来将替换为**实验方案模板库**

### 配置变量
- 数据路径在 `config/settings.yaml` 中配置：
  ```yaml
  data:
    templates_dir: "${PROJECT_ROOT}src/external/rag/data/test_papers"
  ```
- 生产环境时修改此路径即可

### 添加新数据

```bash
# 将 PDF 放入 data/test_papers/
cp your_paper.pdf data/test_papers/

# 处理 PDF
conda activate OntologyConstruction
python pdf_chunk_processor.py --overwrite

# 重新构建索引
python -c "from src.external.rag import LargeRAG; LargeRAG().index_from_folders('data/test_papers')"
```

## 📚 文档位置

- **使用指南**: `USAGE_GUIDE.md` - 详细使用说明
- **迁移报告**: `MIGRATION_COMPLETION_REPORT.md` - OpenAI→DashScope 迁移
- **示例代码**: `examples/README.md` - 完整示例

## 🔧 工具

- **pdf_chunk_processor.py**: PDF → JSON 转换工具
  - 基于 Docling
  - 智能分块和过滤
  - DOI 自动提取

## ⚙️ 配置文件

- `config/settings.yaml` - RAG 内部配置（已本地化）
- `configs/rag_config.yaml` - 项目级配置（暂未使用）

---

**最后更新**: 2025-10-26 18:09
**环境要求**: OntologyConstruction conda 环境
