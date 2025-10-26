# LargeRAG 示例脚本

本目录包含 LargeRAG 的完整使用示例，帮助快速了解系统功能和细节。

## 📁 文件列表

| 文件 | 说明 | 运行顺序 |
|------|------|----------|
| `1_build_index.py` | 构建索引示例 | ① 首次运行 |
| `2_query_and_retrieve.py` | 查询和检索示例 | ② 索引构建后 |

---

## 🚀 快速开始

### 前置条件

1. **安装依赖**
   ```bash
   cd src/tools/largerag
   pip install -r requirements.txt
   ```

2. **配置 API Key**

   在项目根目录创建 `.env` 文件：
   ```
   DASHSCOPE_API_KEY=your_api_key_here
   ```

3. **准备文献数据**

   确保文献数据位于：`src/tools/largerag/data/literature/`

---

## 📖 示例说明

### 示例 1: 构建索引 (`1_build_index.py`)

**功能展示：**
- ✓ 初始化 LargeRAG
- ✓ 从文件夹结构加载文献数据
- ✓ 构建向量索引（Embedding + Chroma）
- ✓ 展示索引统计信息
- ✓ 展示文档处理细节（元数据、分块）
- ✓ 说明缓存系统工作原理

**运行方式：**
```bash
cd src/tools/largerag
python examples/1_build_index.py
```

**预期输出：**
- 索引构建进度（文档加载 → 分块 → Embedding → 存储）
- 处理统计（成功率、节点数、耗时）
- 索引元数据采样展示
- 性能评估（是否达标）

**关键信息：**
- 索引构建时间：35篇文献约 1-3 分钟（首次）
- 缓存生效后：<10 秒（重复索引）
- 索引持久化：自动保存到 `data/chroma_db/`

---

### 示例 2: 查询和检索 (`2_query_and_retrieve.py`)

**功能展示：**
- ✓ 加载已有索引
- ✓ `query()` - LLM 生成完整回答
- ✓ `get_similar_docs()` - 检索文档片段（不使用LLM）
- ✓ 展示检索细节（分数、元数据、来源信息）
- ✓ 对比两种查询方式
- ✓ 说明 Reranker 精排机制

**运行方式：**
```bash
cd src/tools/largerag
python examples/2_query_and_retrieve.py
```

**前置条件：**
需要先运行 `1_build_index.py` 构建索引

**预期输出：**
- 两种查询方式的对比演示
- 检索到的文档详细信息（文本、分数、元数据）
- Reranker 工作流程说明
- 性能指标和使用建议

**关键信息：**
- 查询延迟：~5-10 秒（使用 LLM）
- 检索延迟：~2-5 秒（不使用 LLM）
- Reranker：从 20 个候选中精选 5 个最相关文档

---

## 🔍 功能对比

### `query()` vs `get_similar_docs()`

| 特性 | `query()` | `get_similar_docs()` |
|------|-----------|----------------------|
| **使用 LLM** | ✓ 是 | ✗ 否 |
| **返回格式** | 自然语言回答（字符串） | 文档片段列表 |
| **速度** | 较慢 (~5-10秒) | 较快 (~2-5秒) |
| **返回来源信息** | ✗ 否* | ✓ 是（doc_hash, page_idx） |
| **适用场景** | 最终用户查询 | Agent/开发者调试 |

> *注：`query()` 可以配置返回来源，但当前实现只返回文本

---

## 📊 检索流程详解

```
用户查询
    ↓
[1] 向量召回 (Vector Retrieval)
    - Embedding 查询文本
    - 余弦相似度检索
    - 召回 top_k=20 个候选文档
    ↓
[2] Reranker 精排 (Reranking)
    - DashScope gte-rerank 模型
    - 对 20 个候选重新打分
    - 返回 top_n=5 个最相关文档
    ↓
[3] LLM 生成 (仅 query() 使用)
    - 基于检索到的文档
    - Qwen-Max 生成回答
    ↓
返回结果
```

---

## ⚙️ 配置参数

关键配置位于 `config/settings.yaml`：

```yaml
# 检索参数
retrieval:
  similarity_top_k: 20        # 向量召回数量
  rerank_top_n: 5             # Reranker 返回数量
  similarity_threshold: 0.7   # 相似度阈值

# Reranker 配置
reranker:
  enabled: true               # 是否启用 Reranker
  model: gte-rerank           # Reranker 模型

# LLM 配置
llm:
  model: qwen-max             # Qwen3-235B
  temperature: 0.1            # 生成温度
  max_tokens: 2000            # 最大生成长度
```

---

## 💡 使用建议

### 选择查询方式

- **需要自然语言回答** → 使用 `query()`
- **需要原始文档片段** → 使用 `get_similar_docs()`
- **需要来源信息（doc_hash, page_idx）** → 使用 `get_similar_docs()`

### 性能优化

- 调整 `similarity_top_k` 平衡精度和速度
- 调整 `rerank_top_n` 控制返回文档数量
- 禁用 Reranker 显著提速（精度下降）

### Agent 集成

- Agent 应调用 `get_similar_docs()` 获取文档
- Agent 自己整合多个工具的结果
- Agent 根据 `doc_hash` 和 `page_idx` 追溯原文献

### 调试技巧

- 查看 `get_similar_docs()` 的 `score` 判断检索质量
- 检查 `metadata.doc_hash` 确认来源文献
- 对比不同查询的 `score` 分布调整检索参数

---

## 🐛 常见问题

### Q1: 运行示例报错 "Index not found"

**原因：** 未构建索引

**解决：**
```bash
python examples/1_build_index.py  # 先构建索引
python examples/2_query_and_retrieve.py  # 再运行查询
```

---

### Q2: 索引构建很慢

**原因：** 首次运行需要计算所有文档的 Embedding

**解决：**
- 首次运行慢是正常的（35篇约 1-3 分钟）
- 启用缓存后，重复运行会非常快（<10秒）
- 缓存位置：`src/tools/largerag/data/cache/`

---

### Q3: 查询延迟太高

**可能原因：**
1. Reranker 精排耗时（~2-3秒）
2. LLM 生成耗时（~3-5秒）
3. 网络延迟

**优化建议：**
- 禁用 Reranker：`config/settings.yaml` 中设置 `reranker.enabled: false`
- 使用更快的 LLM 模型（但回答质量可能下降）
- 使用 `get_similar_docs()` 跳过 LLM 生成

---

### Q4: 如何清空索引重新构建？

**方法1：删除 Chroma 数据库**
```bash
rm -rf src/tools/largerag/data/chroma_db
```

**方法2：删除缓存（可选）**
```bash
rm -rf src/tools/largerag/data/cache
```

然后重新运行 `1_build_index.py`

---

## 📚 更多资源

- **配置说明**: `config/settings.yaml`
- **缓存机制**: `docs/cache_guide.md`
- **API 文档**: `largerag.py` (LargeRAG 类注释)
- **测试用例**: `tests/test_integration.py`

---

## 🔗 相关文件

```
src/tools/largerag/
├── examples/                   ← 你在这里
│   ├── 1_build_index.py
│   ├── 2_query_and_retrieve.py
│   └── README.md
├── config/
│   └── settings.yaml           ← 配置文件
├── docs/
│   └── cache_guide.md          ← 缓存说明
├── data/
│   ├── literature/             ← 文献数据
│   ├── chroma_db/              ← 向量索引（自动生成）
│   └── cache/                  ← 缓存文件（自动生成）
└── largerag.py                 ← 主接口类
```

---

**祝使用愉快！如有问题请参考主项目文档 `CLAUDE.md`。**
