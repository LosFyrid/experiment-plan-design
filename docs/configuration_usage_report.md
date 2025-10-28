# 配置文件使用情况分析报告

> 本报告详细记录项目中所有配置文件及其配置项的使用情况
> 生成时间: 2025-10-28
> 项目: Experiment Plan Design System (ACE Framework)

---

## 概述

本项目使用多层配置系统，包括：

- **YAML配置文件**: 用于应用级配置（ACE、RAG、Chatbot、Playbook）
- **环境变量**: 用于敏感信息和路径配置
- **Python配置加载器**: 使用Pydantic进行类型安全的配置管理

### 配置文件清单

| 配置文件 | 路径 | 用途 |
|---------|------|------|
| ace_config.yaml | configs/ | ACE框架核心配置 |
| rag_config.yaml | configs/ | RAG模板库配置 |
| chatbot_config.yaml | configs/ | 聊天机器人配置 |
| playbook_sections.yaml | configs/ | Playbook分区管理配置 |
| settings.yaml (MOSES) | src/external/MOSES/config/ | MOSES本体系统配置 |
| settings.yaml (RAG) | src/external/rag/config/ | LargeRAG详细配置 |
| .env | 项目根目录 | 环境变量和API密钥 |

---

## configs/ace_config.yaml

ACE（Agentic Context Engineering）框架的核心配置文件。

### Model Configuration

- **provider** (String, 默认: "qwen")
  - 用途: LLM提供商选择
  - 使用位置: `src/utils/llm_provider.py:309-317`
  - 说明: 统一使用Qwen以避免知识迁移偏差（ACE论文§4.2）

- **model_name** (String, 默认: "qwen-max")
  - 用途: 指定LLM模型名称
  - 使用位置: `src/utils/llm_provider.py:309-317`, `examples/ace_cycle_example.py:40-56`
  - 说明: ACE三角色（Generator、Reflector、Curator）必须使用相同模型

- **temperature** (Float, 默认: 0.7)
  - 用途: 控制生成随机性
  - 使用位置: `src/utils/llm_provider.py:309-317`
  - 说明: 0.7提供平衡的创造性

- **max_tokens** (Integer, 默认: 4096)
  - 用途: 限制最大响应长度
  - 使用位置: `src/utils/llm_provider.py:309-317`
  - 说明: 足够长以支持完整实验方案生成

### Embedding Configuration

- **model** (String, 默认: "text-embedding-v4")
  - 用途: Qwen Embedding API模型
  - 使用位置: `src/utils/embedding_utils.py:20-30`
  - 说明: 用于Curator的语义去重功能

- **batch_size** (Integer, 默认: 10)
  - 用途: 批量编码文本数量
  - 使用位置: `src/utils/embedding_utils.py`
  - 说明: Qwen API限制最多10个文本/批次

### Generator Configuration

- **max_playbook_bullets** (Integer, 默认: 50)
  - 用途: 检索相关playbook bullets的top-k数量
  - 使用位置: `src/ace_framework/generator/generator.py:131, 353`
  - 说明: 控制生成时使用的上下文知识量

- **include_examples** (Boolean, 默认: true)
  - 用途: 是否在prompt中包含示例
  - 使用位置: 配置定义，未直接使用
  - 说明: 预留参数，用于few-shot学习

- **enable_few_shot** (Boolean, 默认: true)
  - 用途: 启用few-shot学习
  - 使用位置: `src/ace_framework/generator/generator.py:144`
  - 说明: 条件性地在prompt中包含少样本示例

- **few_shot_count** (Integer, 默认: 3)
  - 用途: few-shot示例数量
  - 使用位置: 配置定义，用于future实现
  - 说明: 控制示例数量以平衡context长度

- **output_format** (String, 默认: "structured")
  - 用途: 输出格式选择（"structured" | "markdown"）
  - 使用位置: 配置定义，预留用于格式化
  - 说明: 支持结构化JSON或Markdown格式输出

### Reflector Configuration

- **max_refinement_rounds** (Integer, 默认: 5)
  - 用途: 迭代改进的最大轮数
  - 使用位置: `src/ace_framework/reflector/reflector.py:110, 157`
  - 说明: ACE论文§3中的核心机制，防止过度迭代

- **enable_iterative** (Boolean, 默认: true)
  - 用途: 启用迭代式反思
  - 使用位置: `src/ace_framework/reflector/reflector.py:154`
  - 说明: 控制是否执行多轮refinement

- **reflection_mode** (String, 默认: "detailed")
  - 用途: 反思详细程度（"detailed" | "concise"）
  - 使用位置: 配置定义，预留用于prompt构建
  - 说明: 控制insight提取的粒度

- **bullet_tagging** (Boolean, 默认: true)
  - 用途: 启用bullet标记功能
  - 使用位置: 隐式使用于reflection过程
  - 说明: 标记bullets为helpful/harmful/neutral

### Curator Configuration

- **update_mode** (String, 默认: "incremental")
  - 用途: 更新模式选择（"incremental" | "lazy"）
  - 使用位置: 配置定义，影响去重时机
  - 说明: ACE论文§3.2的Grow-and-Refine机制

- **deduplication_threshold** (Float, 默认: 0.85)
  - 用途: 余弦相似度阈值
  - 使用位置: `src/ace_framework/curator/curator.py:601, 629, 661`
  - 说明: 语义去重的相似度门槛，防止重复bullets

- **max_playbook_size** (Integer, 默认: 200)
  - 用途: Playbook最大bullet数量
  - 使用位置: `src/ace_framework/curator/curator.py:186, 290, 712`
  - 说明: 超出后触发pruning机制

- **enable_grow_and_refine** (Boolean, 默认: true)
  - 用途: 启用增长和精炼机制
  - 使用位置: `src/ace_framework/curator/curator.py:178`
  - 说明: 控制是否执行去重操作

- **prune_harmful_bullets** (Boolean, 默认: true)
  - 用途: 删除有害的bullets
  - 使用位置: `src/ace_framework/curator/curator.py:187`
  - 说明: 自动移除harmful_count > helpful_count的bullets

### Playbook Configuration

- **default_path** (String, 默认: "data/playbooks/chemistry_playbook.json")
  - 用途: Playbook文件路径
  - 使用位置: `examples/ace_cycle_example.py:60`
  - 说明: 存储演化的playbook知识库

- **sections_config** (String, 默认: "configs/playbook_sections.yaml")
  - 用途: 分区配置文件路径
  - 使用位置: 引用playbook_sections.yaml
  - 说明: 管理playbook的section结构

### Training Configuration

- **num_epochs** (Integer, 默认: 5)
  - 用途: 离线训练轮数
  - 使用位置: 配置定义，训练功能待实现
  - 说明: 用于offline adaptation

- **batch_size** (Integer, 默认: 1)
  - 用途: 训练批次大小
  - 使用位置: 配置定义
  - 说明: ACE论文使用batch_size=1

- **feedback_source** (String, 默认: "llm_judge")
  - 用途: 反馈来源选择（"llm_judge" | "human" | "auto"）
  - 使用位置: `src/workflow/feedback_worker.py:120`, `examples/run_simple_ace.py:231`
  - 说明: 控制评估模式

- **enable_offline_warmup** (Boolean, 默认: false)
  - 用途: 启用离线预热
  - 使用位置: 配置定义，功能待开发
  - 说明: 准备就绪时设为true

### Evaluation Configuration

- **enable_auto_check** (Boolean, 默认: true)
  - 用途: 启用自动检查
  - 使用位置: `src/evaluation/evaluator.py`（隐式）
  - 说明: 规则基础的完整性检查

- **enable_llm_judge** (Boolean, 默认: true)
  - 用途: 启用LLM评判
  - 使用位置: `src/evaluation/evaluator.py`（隐式）
  - 说明: 基于LLM的质量评估

- **evaluation_criteria** (List[String])
  - 用途: 评估标准列表
  - 默认值: ["completeness", "safety", "clarity", "executability", "cost_effectiveness"]
  - 使用位置: `src/evaluation/evaluator.py`
  - 说明: 定义评估维度

---

## configs/rag_config.yaml

RAG模板库的高层配置文件。

### Vector Store Configuration

- **type** (String, 默认: "chroma")
  - 用途: 向量数据库类型
  - 使用位置: `src/utils/config_loader.py:132-136`
  - 说明: 支持chroma、faiss、qdrant（当前仅chroma实现）

- **persist_directory** (String, 默认: "data/chroma_db")
  - 用途: Chroma数据库持久化目录
  - 使用位置: `src/external/rag/core/indexer.py:89-91`
  - 说明: 存储向量索引的本地路径

- **collection_name** (String, 默认: "experiment_templates")
  - 用途: Chroma集合名称
  - 使用位置: `src/external/rag/core/indexer.py:197-200, 220-222`
  - 说明: 命名空间，用于组织多个RAG集合

### Embeddings Configuration

- **model_name** (String, 默认: "BAAI/bge-large-zh-v1.5")
  - 用途: 中文embedding模型
  - 使用位置: `src/utils/config_loader.py:139-143`
  - 说明: 本地模型，适用于中文文本

- **model_kwargs.device** (String, 默认: "cpu")
  - 用途: 设备选择（"cpu" | "cuda"）
  - 使用位置: 配置定义
  - 说明: GPU加速需要CUDA环境

- **encode_kwargs.normalize_embeddings** (Boolean, 默认: true)
  - 用途: 归一化embeddings
  - 使用位置: 配置定义
  - 说明: 用于余弦相似度计算

- **encode_kwargs.batch_size** (Integer, 默认: 32)
  - 用途: 编码批次大小
  - 使用位置: 配置定义
  - 说明: 控制并行编码数量

### Retrieval Configuration

- **top_k** (Integer, 默认: 5)
  - 用途: 检索模板数量
  - 使用位置: `src/workflow/rag_adapter.py:77-81`
  - 说明: 可在调用时动态覆盖

- **similarity_threshold** (Float, 默认: 0.7)
  - 用途: 最小相似度分数
  - 使用位置: `src/external/rag/core/query_engine.py:59-66`
  - 说明: 过滤低质量结果

- **enable_reranking** (Boolean, 默认: false)
  - 用途: 启用二阶段检索
  - 使用位置: `src/external/rag/core/query_engine.py`
  - 说明: 速度vs准确度权衡

- **reranker_model** (String, 默认: null)
  - 用途: Reranker模型名称
  - 使用位置: `src/external/rag/core/query_engine.py`
  - 说明: 仅当enable_reranking=true时使用

### Document Processing Configuration

- **chunk_size** (Integer, 默认: 512)
  - 用途: 文档分块大小（tokens）
  - 使用位置: `src/external/rag/core/indexer.py:113-124`
  - 说明: 512 tokens ≈ 1000-1500字符

- **chunk_overlap** (Integer, 默认: 50)
  - 用途: 分块重叠大小
  - 使用位置: `src/external/rag/core/indexer.py:113-124`
  - 说明: 保持上下文连续性

- **enable_metadata_extraction** (Boolean, 默认: true)
  - 用途: 启用元数据提取
  - 使用位置: 配置定义
  - 说明: 提取文档元信息

- **supported_formats** (List[String])
  - 用途: 支持的文件格式
  - 默认值: ["json", "markdown", "txt"]
  - 使用位置: `src/external/rag/core/document_processor.py:27-78`
  - 说明: 文档加载器支持的格式

### Template Schema Configuration

- **required_fields** (List[String])
  - 用途: 必需字段列表
  - 默认值: ["title", "objective", "materials", "procedure"]
  - 使用位置: `src/workflow/rag_adapter.py:164-216`
  - 说明: 模板验证使用

- **optional_fields** (List[String])
  - 用途: 可选字段列表
  - 默认值: ["safety_notes", "expected_yield", "quality_control", "references"]
  - 使用位置: 配置定义
  - 说明: 模板可包含的额外信息

### Indexing Configuration

- **auto_index_on_startup** (Boolean, 默认: false)
  - 用途: 启动时自动索引
  - 使用位置: `src/external/rag/largerag.py:54-60`
  - 说明: 当前禁用以提高性能

- **template_directory** (String, 默认: "data/templates")
  - 用途: 模板文件目录
  - 使用位置: `src/external/rag/examples/1_build_index.py:62-103`
  - 说明: 索引时的数据源

- **index_metadata** (List[String])
  - 用途: 索引元数据字段
  - 默认值: ["domain", "difficulty", "safety_level"]
  - 使用位置: `src/external/rag/core/document_processor.py:114-122`
  - 说明: 提取和存储的元数据

---

## configs/chatbot_config.yaml

MOSES聊天机器人配置。

### LLM Configuration

- **provider** (String, 默认: "qwen")
  - 用途: LLM提供商
  - 使用位置: 配置定义（预留，当前仅qwen实现）
  - 说明: 未来支持多提供商切换

- **model_name** (String, 默认: "qwen-plus")
  - 用途: LLM模型名称
  - 使用位置: `src/chatbot/chatbot.py:105`
  - 说明: qwen-plus支持thinking功能

- **temperature** (Float, 默认: 0.7)
  - 用途: 控制响应创造性
  - 使用位置: `src/chatbot/chatbot.py:95`
  - 说明: 通过model_kwargs传递给ChatTongyi

- **max_tokens** (Integer, 默认: 4096)
  - 用途: 最大响应长度
  - 使用位置: `src/chatbot/chatbot.py:96`
  - 说明: 支持长对话响应

- **enable_thinking** (Boolean, 默认: true)
  - 用途: 启用qwen-plus推理过程
  - 使用位置: `src/chatbot/chatbot.py:100-102`
  - 说明: 类似o1的思维链功能

### MOSES Configuration

- **max_workers** (Integer, 默认: 4)
  - 用途: 并发工作线程数
  - 使用位置: `src/chatbot/tools.py:73`
  - 说明: QueryManager的并发查询数量

- **query_timeout** (Integer, 默认: 600)
  - 用途: 查询超时时间（秒）
  - 使用位置: `src/chatbot/tools.py:166`
  - 说明: 10分钟超时，适合复杂查询

### Memory Configuration

- **type** (String, 默认: "sqlite")
  - 用途: 记忆类型（"in_memory" | "sqlite"）
  - 使用位置: `src/chatbot/chatbot.py:119-136`
  - 说明:
    - "in_memory": 开发调试用，会话结束后丢失
    - "sqlite": 生产环境，持久化存储

- **sqlite_path** (String, 默认: "data/chatbot_memory.db")
  - 用途: SQLite数据库文件路径
  - 使用位置: `src/chatbot/chatbot.py:127-134`
  - 说明: 用于SqliteSaver的持久化会话管理

### Display Configuration

- **show_thinking** (Boolean, 默认: true)
  - 用途: 显示thinking过程
  - 使用位置: `src/chatbot/chatbot.py:191-198`
  - 说明: 从additional_kwargs提取reasoning_content

### System Prompt

- **system_prompt** (Multi-line String)
  - 用途: ReAct agent的系统提示词
  - 使用位置: `src/chatbot/chatbot.py:69-79`
  - 说明: 定义agent行为和能力，作为state_modifier传递

---

## configs/playbook_sections.yaml

Playbook分区结构管理配置。

### Core Sections

预定义的核心sections，稳定且不可删除。

#### material_selection

- **id_prefix**: "mat"
  - 用途: bullet ID生成前缀
  - 使用位置: `src/ace_framework/playbook/playbook_manager.py:生成ID如mat-00001`
  - 说明: 材料选择指导原则

- **description**: "选择实验材料、试剂、溶剂的指导原则"
  - 用途: section说明
  - 使用位置: `src/utils/section_manager.py:format_sections_for_prompt()`
  - 说明: 用于LLM prompt构建

- **examples**: List[String]
  - 用途: 示例bullets
  - 使用位置: prompt构建
  - 说明: 帮助LLM理解section范围

#### procedure_design

- **id_prefix**: "proc"
- **description**: "实验流程设计、操作步骤优化"
- **examples**: ["反应温度和时间控制策略", ...]

#### safety_protocols

- **id_prefix**: "safe"
- **description**: "安全操作规范、应急处理措施"
- **examples**: ["个人防护装备要求", ...]

#### quality_control

- **id_prefix**: "qc"
- **description**: "质量检测方法、标准和验收准则"
- **examples**: ["产物纯度检测方法", ...]

#### troubleshooting

- **id_prefix**: "ts"
- **description**: "常见问题诊断和解决方案"
- **examples**: ["反应不发生的排查步骤", ...]

#### common_mistakes

- **id_prefix**: "err"
- **description**: "需要避免的错误和注意事项"
- **examples**: ["常见操作失误和预防", ...]

### Custom Sections

动态添加的sections（初始为空）。

- **结构**: 每个custom section包含
  - `id_prefix`: 2-4字符前缀
  - `description`: 可读描述
  - `created_at`: 创建时间戳
  - `created_by`: "curator"
  - `creation_reason`: 添加理由
  - `examples`: 示例bullets列表

- **使用位置**: `src/utils/section_manager.py:add_custom_section()`
- **同步机制**:
  - 添加到playbook_sections.yaml的custom_sections
  - 同步到playbook.json的sections列表（`src/ace_framework/curator/curator.py:375-384`）

### Settings

#### allow_new_sections

- **类型**: Boolean
- **默认值**: true
- **用途**: 主开关，控制Curator是否可提议新sections
- **使用位置**: `src/utils/section_manager.py:is_new_section_allowed()`
- **说明**: 运行时可覆盖

#### new_section_guidelines

- **类型**: Multi-line String
- **用途**: Curator提议新section时的引导原则
- **使用位置**: `src/ace_framework/curator/prompts.py:86-110`
- **说明**: 插入到curation prompt中，定义严格的提议条件

---

## src/external/MOSES/config/settings.yaml

MOSES本体系统配置。

### Ontology Configuration

- **directory_path** (String, 默认: "data/ontology/")
  - 用途: 本体文件目录（相对于MOSES根目录）
  - 使用位置: `src/external/MOSES/config/settings.py:58-70, 145-155`
  - 说明: owlready2加载本体的路径

- **ontology_file_name** (String, 默认: "chem_ontology.owl")
  - 用途: 本体文件名
  - 使用位置: `src/external/MOSES/autology_constructor/idea/query_team/ontology_tools.py:308`
  - 说明: OWL格式的化学本体

- **base_iri** (String, 默认: "http://www.test.org/chem_ontologies/")
  - 用途: 本体IRI基准
  - 使用位置: `src/external/MOSES/autology_constructor/preprocess.py:5, 10`
  - 说明: OWL本体的命名空间

- **java_exe** (String, 默认: "")
  - 用途: Java可执行文件路径
  - 使用位置: owlready2内部
  - 说明: 留空让owlready2自动检测

### Entity Retrieval Configuration

- **top_k** (Integer, 默认: 5)
  - 用途: 返回候选实体数量
  - 使用位置: `src/external/MOSES/autology_constructor/idea/query_team/entity_matcher.py:311-467`
  - 说明: RankedRetriever的返回结果数

- **bm25_weight** (Float, 默认: 0.5)
  - 用途: BM25算法权重
  - 使用位置: `src/external/MOSES/autology_constructor/idea/query_team/entity_matcher.py`
  - 说明: 混合评分：`mixed_score = bm25_weight * bm25_score + jaccard_weight * jaccard_score`

- **jaccard_weight** (Float, 默认: 0.5)
  - 用途: Jaccard相似度权重
  - 使用位置: `src/external/MOSES/autology_constructor/idea/query_team/entity_matcher.py`
  - 说明: 字符级trigram匹配

- **trigram_size** (Integer, 默认: 3)
  - 用途: n-gram大小
  - 使用位置: entity_matcher.py
  - 说明: 用于字符级相似度计算

- **min_score_threshold** (Float, 默认: 0.1)
  - 用途: 最小分数阈值
  - 使用位置: entity_matcher.py
  - 说明: 过滤低分候选

### LLM Configuration

- **model** (String, 默认: "qwen3-max")
  - 用途: LLM模型名称
  - 使用位置: `src/external/MOSES/autology_constructor/idea/common/llm_provider.py:14-66`
  - 说明: 自动检测Qwen模型并使用OpenAI兼容接口

- **streaming** (Boolean, 默认: false)
  - 用途: 启用流式输出
  - 使用位置: llm_provider.py
  - 说明: 当前禁用

- **temperature** (Integer, 默认: 0)
  - 用途: 控制生成确定性
  - 使用位置: llm_provider.py
  - 说明: 0表示确定性生成，适合本体提取

- **max_tokens** (Integer, 默认: 5000)
  - 用途: 最大token数
  - 使用位置: llm_provider.py
  - 说明: 查询用5000，本体提取用20000

### Extractor Examples Configuration

- **individual_directory_path** (String)
  - 用途: 概念示例目录
  - 使用位置: 配置已加载但未主动使用
  - 说明: 预留用于future功能

- **concept_file_path** (String)
  - 用途: 概念文件路径
  - 使用位置: 配置已加载但未主动使用
  - 说明: 使用`{{individual_directory_path}}`引用

### Dataset Construction Configuration

- **folder_path** (String, 默认: "${PROJECT_ROOT}data")
  - 用途: 数据集根目录
  - 使用位置: `src/external/MOSES/autology_constructor/dataset_construction.py:24-132`
  - 说明: 支持环境变量展开

- **raw_data_folder_path** (String)
  - 用途: 原始文本数据目录
  - 使用位置: dataset_construction.py
  - 说明: 使用`{{folder_path}}`引用

- **devset_file_path** (String)
  - 用途: 开发集文件路径
  - 使用位置: `dataset_construction.py:118-120`
  - 说明: load_saved_datasets()使用

- **trainset_file_path** (String)
  - 用途: 训练集文件路径
  - 使用位置: dataset_construction.py
  - 说明: save_datasets()使用

---

## src/external/rag/config/settings.yaml

LargeRAG详细实现配置。

### Data Configuration

- **templates_dir** (String, 默认: "${PROJECT_ROOT}src/external/rag/data/test_papers")
  - 用途: 索引数据源路径
  - 使用位置: 配置定义
  - 说明: 临时使用文献数据，未来替换为实验方案模板

### Embedding Configuration

- **provider** (String, 默认: "dashscope")
  - 用途: Embedding提供商
  - 使用位置: `src/external/rag/core/indexer.py:79-86`
  - 说明: 固定值，使用Qwen API

- **model** (String, 默认: "text-embedding-v3")
  - 用途: Qwen embedding模型
  - 使用位置: indexer.py初始化RetryableDashScopeEmbedding
  - 说明: API模式，无需本地模型

- **text_type** (String, 默认: "document")
  - 用途: 文本类型（"document" | "query"）
  - 使用位置: indexer.py
  - 说明: 影响embedding优化方向

- **batch_size** (Integer, 默认: 10)
  - 用途: 批处理大小
  - 使用位置: indexer.py
  - 说明: 减小以避免API限流

- **dimension** (Integer, 默认: 1024)
  - 用途: 向量维度
  - 使用位置: 配置定义
  - 说明: text-embedding-v3的固定维度

### Vector Store Configuration

- **type** (String, 默认: "chroma")
  - 用途: 向量数据库类型
  - 使用位置: indexer.py
  - 说明: 固定值，不可修改

- **persist_directory** (String, 默认: "${PROJECT_ROOT}src/external/rag/data/chroma_db")
  - 用途: Chroma持久化目录
  - 使用位置: `indexer.py:89-91`
  - 说明: ChromaDB本地存储路径

- **collection_name** (String, 默认: "experiment_plan_templates_v1")
  - 用途: Collection名称
  - 使用位置: `indexer.py:197-200`
  - 说明: 命名空间隔离

- **distance_metric** (String, 默认: "cosine")
  - 用途: 距离度量（"cosine" | "l2" | "ip"）
  - 使用位置: indexer.py元数据
  - 说明: HNSW空间配置

### Document Processing Configuration

- **splitter_type** (String, 默认: "token")
  - 用途: 分块策略（"token" | "semantic" | "sentence"）
  - 使用位置: `indexer.py:99-125`
  - 说明: 控制文档切分方式

- **chunk_size** (Integer, 默认: 512)
  - 用途: 分块大小（token，仅token模式）
  - 使用位置: `indexer.py:113-124`
  - 说明: 512 tokens适合实验方案

- **chunk_overlap** (Integer, 默认: 50)
  - 用途: 重叠大小
  - 使用位置: indexer.py
  - 说明: 保持上下文连续性

- **separator** (String, 默认: "\n\n")
  - 用途: 分块分隔符（仅token模式）
  - 使用位置: indexer.py
  - 说明: 段落级别分割

- **semantic_breakpoint_threshold** (Float, 默认: 0.5)
  - 用途: 语义断点阈值（semantic模式）
  - 使用位置: `indexer.py:104-108`
  - 说明: 0-1范围

- **semantic_buffer_size** (Integer, 默认: 1)
  - 用途: 缓冲区大小（semantic模式）
  - 使用位置: indexer.py
  - 说明: SemanticSplitterNodeParser参数

### Retrieval Configuration

- **similarity_top_k** (Integer, 默认: 30)
  - 用途: 向量检索召回数量
  - 使用位置: `src/external/rag/core/query_engine.py:59-66`
  - 说明: 增加候选池，为reranker准备

- **rerank_top_n** (Integer, 默认: 8)
  - 用途: Reranker最终返回数量
  - 使用位置: query_engine.py
  - 说明: 实验计划需要更多模板

- **similarity_threshold** (Float, 默认: 0.5)
  - 用途: 相似度阈值
  - 使用位置: `query_engine.py:59-66`
  - 说明: 过滤低质量文档（推荐0.6-0.8）

### Reranker Configuration

- **provider** (String, 默认: "dashscope")
  - 用途: Reranker提供商
  - 使用位置: query_engine.py
  - 说明: 固定值

- **model** (String, 默认: "gte-rerank-v2")
  - 用途: Qwen reranker模型
  - 使用位置: query_engine.py
  - 说明: 二阶段精排

- **enabled** (Boolean, 默认: true)
  - 用途: 是否启用reranker
  - 使用位置: query_engine.py
  - 说明: 速度vs准确度权衡

### LLM Configuration

- **provider** (String, 默认: "dashscope")
  - 用途: LLM提供商
  - 使用位置: query_engine.py
  - 说明: 固定值

- **model** (String, 默认: "qwen-plus")
  - 用途: LLM模型
  - 使用位置: query_engine.py
  - 说明: qwen-plus（成本优化）或qwen-max

- **temperature** (Integer, 默认: 0)
  - 用途: 生成温度
  - 使用位置: query_engine.py
  - 说明: 确定性生成

- **max_tokens** (Integer, 默认: 2000)
  - 用途: 最大token数
  - 使用位置: query_engine.py
  - 说明: 适合摘要生成

### Cache Configuration

- **enabled** (Boolean, 默认: true)
  - 用途: 是否启用缓存
  - 使用位置: indexer.py
  - 说明: 加速重复查询

- **type** (String, 默认: "local")
  - 用途: 缓存类型（"local" | "redis"）
  - 使用位置: indexer.py
  - 说明: local推荐，无需额外服务

- **local_cache_dir** (String, 默认: "${PROJECT_ROOT}src/external/rag/data/cache")
  - 用途: 本地缓存目录
  - 使用位置: indexer.py
  - 说明: 文件系统缓存

- **redis_host** (String, 默认: "localhost")
  - 用途: Redis主机（可选）
  - 使用位置: 配置定义
  - 说明: 需要redis-server服务

- **redis_port** (Integer, 默认: 6379)
  - 用途: Redis端口
  - 使用位置: 配置定义
  - 说明: 默认Redis端口

- **collection_name** (String, 默认: "largerag_embedding_cache")
  - 用途: 缓存集合名称
  - 使用位置: indexer.py
  - 说明: 命名空间隔离

- **ttl** (Integer, 默认: 86400)
  - 用途: 缓存过期时间（秒，仅Redis）
  - 使用位置: 配置定义
  - 说明: 24小时

### Logging Configuration

- **level** (String, 默认: "INFO")
  - 用途: 日志级别
  - 使用位置: 配置定义
  - 说明: DEBUG, INFO, WARNING, ERROR

- **file_path** (String, 默认: "${PROJECT_ROOT}logs/largerag.log")
  - 用途: 日志文件路径
  - 使用位置: 配置定义
  - 说明: LargeRAG专用日志

- **format** (String)
  - 用途: 日志格式
  - 使用位置: 配置定义
  - 说明: Python logging格式字符串

---

## .env

环境变量配置文件（敏感信息和路径）。

### API Keys

- **DASHSCOPE_API_KEY** (String, 必需)
  - 用途: Qwen LLM和Embedding API认证
  - 使用位置:
    - `src/utils/llm_provider.py:110`
    - `src/utils/qwen_embedding.py:50`
    - `src/external/rag/config/settings.py:198`
  - 说明: **必须设置**，否则系统无法运行

- **QWEN_BASE_URL** (String, 可选)
  - 用途: Qwen OpenAI兼容接口Base URL
  - 默认值: `https://dashscope.aliyuncs.com/compatible-mode/v1`（中国区）
  - 使用位置: `src/external/MOSES/autology_constructor/idea/common/llm_provider.py:35-38`
  - 备选值: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`（国际区）

- **OPENAI_API_KEY** (String, 可选)
  - 用途: OpenAI API认证（备用）
  - 使用位置: `src/utils/llm_provider.py:195`
  - 说明: 仅当使用OpenAI模型时需要

### Path Configuration

- **PROJECT_ROOT** (String, 关键)
  - 用途: 项目根目录绝对路径
  - 使用位置:
    - `src/utils/config_loader.py:215-222`
    - `src/external/MOSES/config/settings.py:53-54`
    - `src/external/rag/config/settings.py:156-163`
  - 说明: 所有相对路径的基准，自动检测`.git`目录

- **MOSES_ROOT** (String, 派生)
  - 用途: MOSES根目录
  - 默认值: `${PROJECT_ROOT}/src/external/MOSES`
  - 使用位置: MOSES内部本体加载
  - 说明: 依赖PROJECT_ROOT

- **CHROMA_PERSIST_DIR** (String, 派生)
  - 用途: Chroma向量数据库目录
  - 默认值: `${PROJECT_ROOT}/data/chroma_db`
  - 使用位置: ChromaDB初始化
  - 说明: 依赖PROJECT_ROOT

### Logging Configuration

- **LOG_LEVEL** (String, 可选)
  - 用途: 日志级别
  - 默认值: `INFO`
  - 使用位置: `src/utils/config_loader.py:189`
  - 说明: 配置已加载但未系统性使用

- **LOG_FILE** (String, 可选)
  - 用途: 主日志文件路径
  - 默认值: `${PROJECT_ROOT}/logs/app.log`
  - 使用位置: 配置定义
  - 说明: 实际使用LogsManager的结构化日志系统

### Model Configuration

- **DEFAULT_LLM_PROVIDER** (String, 关键)
  - 用途: 默认LLM提供商
  - 默认值: `qwen`
  - 使用位置: `src/utils/llm_provider.py:310-317`
  - 说明: 路由到QwenProvider或OpenAIProvider

- **DEFAULT_LLM_MODEL** (String, 关键)
  - 用途: ACE使用的默认模型
  - 默认值: `qwen-max`
  - 使用位置: `src/utils/llm_provider.py:286`
  - 说明: ACE三角色必须使用相同模型

- **MOSES_LLM_MODEL** (String, 可选)
  - 用途: MOSES专用模型
  - 默认值: `qwen-plus`
  - 使用位置: 配置定义，未主动加载
  - 说明: MOSES使用settings.yaml配置

- **DEFAULT_EMBEDDING_MODEL** (String, 可选)
  - 用途: 默认embedding模型
  - 默认值: `BAAI/bge-large-zh-v1.5`
  - 使用位置: 配置定义，未主动使用
  - 说明: RAG使用hardcoded配置

- **DEFAULT_PLAYBOOK_PATH** (String, 可选)
  - 用途: Playbook文件路径
  - 默认值: `${PROJECT_ROOT}/data/playbooks/chemistry_playbook.json`
  - 使用位置: 配置定义，代码中直接构造路径
  - 说明: 未直接使用，路径相对PROJECT_ROOT解析

### Development Settings

- **DEBUG** (Boolean, 可选)
  - 用途: 启用调试模式
  - 默认值: `False`
  - 使用位置: 配置定义，未集成到中心化系统
  - 说明: Debug输出散布在代码中

- **ENABLE_CACHE** (Boolean, 可选)
  - 用途: 启用缓存
  - 默认值: `True`
  - 使用位置: 配置定义，未系统性使用
  - 说明: RAG有缓存功能但不受此控制

- **CACHE_DIR** (String, 可选)
  - 用途: 缓存目录
  - 默认值: `${PROJECT_ROOT}/.cache`
  - 使用位置: 配置定义，未主动使用
  - 说明: RAG使用独立缓存目录配置

---

## 配置加载机制

### src/utils/config_loader.py

使用Pydantic进行类型安全的配置管理。

#### 主要类

- **ModelConfig**: LLM模型配置
- **GeneratorConfig**: Generator配置
- **ReflectorConfig**: Reflector配置
- **CuratorConfig**: Curator配置
- **PlaybookConfig**: Playbook配置
- **TrainingConfig**: 训练配置
- **EvaluationConfig**: 评估配置
- **ACEConfig**: 完整ACE配置
- **VectorStoreConfig**: 向量存储配置
- **EmbeddingsConfig**: Embeddings配置
- **RetrievalConfig**: 检索配置
- **DocumentProcessingConfig**: 文档处理配置
- **RAGConfig**: 完整RAG配置
- **EnvironmentSettings**: 环境变量配置

#### 加载函数

- **get_config_loader()**: 获取全局单例
- **get_ace_config()**: 便捷函数获取ACE配置
- **get_rag_config()**: 便捷函数获取RAG配置
- **get_env_settings()**: 便捷函数获取环境配置

#### 使用模式

```python
from src.utils.config_loader import get_ace_config, get_rag_config

# 加载ACE配置
ace_config = get_ace_config()
provider = ace_config.model.provider
model_name = ace_config.model.model_name

# 加载RAG配置
rag_config = get_rag_config()
top_k = rag_config.retrieval.top_k
```

---

## 配置优先级

1. **命令行参数** - 最高优先级（覆盖所有）
2. **环境变量** - 覆盖YAML默认值
3. **YAML配置文件** - 项目级配置
4. **代码默认值** - 最低优先级（fallback）

---

## 关键发现

### 1. 环境变量状态

**必须设置**:
- `DASHSCOPE_API_KEY`
- `PROJECT_ROOT`（可自动检测）
- `DEFAULT_LLM_PROVIDER`（默认qwen）
- `DEFAULT_LLM_MODEL`（默认qwen-max）

**可选但推荐**:
- `QWEN_BASE_URL`（国际部署）
- `LOG_LEVEL`（调试）

**已定义但未主动使用**:
- `MOSES_LLM_MODEL`
- `DEFAULT_EMBEDDING_MODEL`
- `DEFAULT_PLAYBOOK_PATH`
- `DEBUG`
- `ENABLE_CACHE`
- `CACHE_DIR`

### 2. 配置文件协同

- **ACE + RAG**: 通过RAGAdapter集成
- **ACE + Playbook Sections**: Curator使用SectionManager
- **Chatbot + MOSES**: MOSESToolWrapper集成
- **RAG双配置**: 高层configs/rag_config.yaml + 底层src/external/rag/config/settings.yaml

### 3. 配置验证

- **Pydantic**: 类型验证和默认值
- **字段验证**: pattern匹配（如provider必须是qwen|openai|anthropic）
- **范围验证**: ge/le限制（如temperature在0.0-2.0）
- **必需字段**: Field(...) 标记

### 4. 配置热点

**最常使用的参数**:
- `ace_config.model.*` - LLM provider和examples
- `ace_config.generator.max_playbook_bullets` - bullet检索
- `ace_config.curator.deduplication_threshold` - 去重
- `ace_config.curator.max_playbook_size` - playbook维护
- `rag_config.retrieval.top_k` - 模板检索
- `chatbot_config.llm.enable_thinking` - qwen-plus特性

### 5. 待改进项

- `LOG_LEVEL`未应用到所有loggers
- `DEBUG`未集成到中心化系统
- `ENABLE_CACHE`未控制RAG缓存
- MOSES_LLM_MODEL未从env动态加载
- 某些配置项定义但未使用（如generator.output_format）

---

## 测试和验证

### 配置文件测试

- `tests/test_section_manager.py` - SectionManager全面测试
- `tests/test_curator_section_sync.py` - Section同步测试
- `tests/verify_section_sync_fix.py` - Section同步验证脚本

### 配置加载测试

建议添加：
```python
def test_ace_config_loading():
    config = get_ace_config()
    assert config.model.provider == "qwen"
    assert config.generator.max_playbook_bullets == 50

def test_rag_config_loading():
    config = get_rag_config()
    assert config.retrieval.top_k == 5
    assert config.vector_store.type == "chroma"
```

---

## 总结

本项目采用多层次、模块化的配置系统：

- **YAML配置文件**: 应用级参数和默认值
- **环境变量**: 敏感信息和路径
- **Pydantic模型**: 类型安全和验证
- **配置加载器**: 单例模式和懒加载

所有关键配置项已详细记录使用位置和用途，为未来维护和扩展提供参考。
