# 配置修复立即行动方案 (更新版)

**创建日期**: 2025-10-28
**更新日期**: 2025-10-28 (代码调研后更新)
**优先级**: 🔥 高优先级
**预计工时**: 3-4小时 (基于实际代码调研后重新评估)
**风险等级**: 🟡 中等

---

## 📋 执行摘要

本方案基于对实际代码的详细调研，修复3个配置问题：

1. ✅ **行动1**: 修复 `ace.embedding` 配置加载 - 让Curator从配置读取embedding model
2. ✅ **行动2**: 使用 `ace.playbook.sections_config` - 让SectionManager从配置读取路径
3. ⚠️ **行动3** (已调整): 配置化 `min_similarity` 阈值 - Generator中的硬编码检索阈值

**重要调整**: 原方案中提到的 `few_shot_top_k` **不存在于当前代码**，已从方案中移除。

---

## 目录

1. [代码调研发现](#代码调研发现)
2. [行动1: 修复 ace.embedding 配置加载](#行动1-修复-aceembedding-配置加载)
3. [行动2: 使用 ace.playbook.sections_config](#行动2-使用-aceplaybooksections_config)
4. [行动3: 配置化 min_similarity 阈值](#行动3-配置化-min_similarity-阈值)
5. [测试计划](#测试计划)
6. [回滚方案](#回滚方案)

---

## 代码调研发现

### 发现总结

| 问题 | 文件位置 | 当前状态 | 修复优先级 |
|------|---------|---------|-----------|
| 1. 缺少 EmbeddingConfig 类 | `config_loader.py:19-25` | ❌ 不存在 | 🔴 高 |
| 2. ACEConfig 缺少 embedding 字段 | `config_loader.py:117-125` | ❌ 不存在 | 🔴 高 |
| 3. PlaybookConfig 缺少 sections_config 字段 | `config_loader.py:61-83` | ❌ 不存在 | 🟡 中 |
| 4. GeneratorConfig 缺少 min_similarity 字段 | `config_loader.py:31-37` | ❌ 不存在 | 🟡 中 |
| 5. Curator embedding 硬编码 | `curator.py:90-92` | ✅ 使用默认值 | 🔴 高 |
| 6. SectionManager 路径硬编码 | `section_manager.py:22` | ✅ 有fallback | 🟡 中 |
| 7. Generator min_similarity 硬编码 | `generator.py:132, 355` | ✅ 硬编码 0.3 | 🟡 中 |

### 关键发现详情

#### 发现1: EmbeddingManager 参数分析

**文件**: `src/utils/embedding_utils.py:20-30`

```python
def __init__(
    self,
    model_name: str = "text-embedding-v4",  # ✅ 需要从配置读取
    api_key: str = None
):
```

**重要**: `batch_size` **不是** `__init__` 参数，而是 `encode()` 方法的参数（默认10）。因此：
- ✅ 需要修改: `model_name` 从配置读取
- ❌ 不需要修改: `batch_size`（已经是方法参数）

#### 发现2: Generator few_shot 机制

**文件**: `src/ace_framework/generator/generator.py:81`

```python
def generate(
    self,
    requirements: Dict[str, Any],
    templates: Optional[List[Dict]] = None,
    few_shot_examples: Optional[List[Dict]] = None,  # ⚠️ 外部传入，不是内部检索
    section_filter: Optional[List[str]] = None
) -> GenerationResult:
```

**重要**: `few_shot_examples` 是**外部传入**的参数，Generator不负责检索few-shot样例。因此原方案提到的 `few_shot_top_k` 配置**不适用**。

#### 发现3: 硬编码阈值位置

**文件**: `src/ace_framework/generator/generator.py`

```python
# 第132行 - 日志记录中硬编码
self.logger.log_bullet_retrieval(
    query=requirements.get("objective", ""),
    bullets_retrieved=len(relevant_bullets),
    top_k=self.config.max_playbook_bullets,
    min_similarity=0.3,  # 👈 硬编码
    ...
)

# 第355行 - 实际检索调用中硬编码
retrieved = self.playbook_manager.retrieve_relevant_bullets(
    query=query,
    top_k=self.config.max_playbook_bullets,
    section_filter=section_filter,
    min_similarity=0.3  # 👈 硬编码
)
```

---

## 行动1: 修复 ace.embedding 配置加载

### 问题描述

**当前状态**:
- ✅ `configs/ace_config.yaml:12-15` 定义了 `ace.embedding` 配置节
- ❌ `src/utils/config_loader.py` 的 `ACEConfig` 类**没有**加载这个配置节
- ❌ `src/ace_framework/curator/curator.py:90-92` 使用默认值创建 EmbeddingManager

**影响**: 无法通过配置文件控制Curator的embedding model

---

### 修改步骤

#### 修改 1.1: 添加 EmbeddingConfig 类

**文件**: `src/utils/config_loader.py`

**插入位置**: 第26行（`ModelConfig` 之后）

**添加代码**:

```python
class EmbeddingConfig(BaseModel):
    """Embedding configuration for ACE framework."""
    model: str = Field(default="text-embedding-v4", description="Qwen embedding model")
    # 注意: batch_size 不需要添加，因为它是 encode() 方法参数而非实例属性
```

**完整上下文**:

```python
# 第19-25行 - ModelConfig
class ModelConfig(BaseModel):
    """LLM model configuration."""
    provider: str = Field(default="qwen", pattern="^(qwen|openai|anthropic)$")
    model_name: str = Field(default="qwen-max")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)

# 👇 在这里添加 EmbeddingConfig（第26行）
class EmbeddingConfig(BaseModel):
    """Embedding configuration for ACE framework."""
    model: str = Field(default="text-embedding-v4", description="Qwen embedding model")

# 第28-37行 - 继续其他配置类
# ============================================================================
# ACE Component Configurations
# ============================================================================
```

---

#### 修改 1.2: 在 ACEConfig 添加 embedding 字段

**文件**: `src/utils/config_loader.py`

**修改位置**: 第117-125行

**修改前**:

```python
class ACEConfig(BaseModel):
    """Complete ACE framework configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    reflector: ReflectorConfig = Field(default_factory=ReflectorConfig)
    curator: CuratorConfig = Field(default_factory=CuratorConfig)
    playbook: PlaybookConfig = Field(default_factory=PlaybookConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
```

**修改后**:

```python
class ACEConfig(BaseModel):
    """Complete ACE framework configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)  # 👈 添加这行
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    reflector: ReflectorConfig = Field(default_factory=ReflectorConfig)
    curator: CuratorConfig = Field(default_factory=CuratorConfig)
    playbook: PlaybookConfig = Field(default_factory=PlaybookConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
```

---

#### 修改 1.3: Curator 使用配置

**文件**: `src/ace_framework/curator/curator.py`

**修改位置**: 第89-92行

**修改前**:

```python
# Embedding manager for deduplication
if embedding_manager is None:
    embedding_manager = EmbeddingManager()  # 👈 使用默认值
self.embedding_manager = embedding_manager
```

**修改后**:

```python
# Embedding manager for deduplication
if embedding_manager is None:
    # Load embedding config from ACE configuration
    from utils.config_loader import get_ace_config
    ace_config = get_ace_config()
    embedding_manager = EmbeddingManager(
        model_name=ace_config.embedding.model  # 👈 从配置读取
    )
self.embedding_manager = embedding_manager
```

---

### 验证步骤

#### 测试 1.1: 验证配置加载

```python
# test_embedding_config.py
from src.utils.config_loader import get_ace_config

config = get_ace_config()
print(f"✅ Embedding model: {config.embedding.model}")

# 预期输出:
# ✅ Embedding model: text-embedding-v4
```

#### 测试 1.2: 验证 Curator 使用配置

```python
from src.ace_framework.curator.curator import PlaybookCurator
from src.ace_framework.playbook.playbook_manager import PlaybookManager
from src.utils.llm_provider import QwenLLMProvider
from src.utils.config_loader import get_ace_config

# 创建组件
config = get_ace_config()
playbook_manager = PlaybookManager(playbook_path="data/playbooks/chemistry_playbook.json")
llm = QwenLLMProvider()

# 创建 Curator（不传入 embedding_manager，测试默认行为）
curator = PlaybookCurator(
    playbook_manager=playbook_manager,
    llm_provider=llm,
    config=config.curator
)

# 验证使用了配置中的模型
print(f"✅ Curator embedding model: {curator.embedding_manager.model_name}")

# 预期输出:
# ✅ Curator embedding model: text-embedding-v4
```

#### 测试 1.3: 修改配置并验证

```yaml
# 临时修改 configs/ace_config.yaml
ace:
  embedding:
    model: "text-embedding-v3"  # 改为 v3 测试
```

重新运行测试 1.1 和 1.2，确认输出变为 `text-embedding-v3`。

---

## 行动2: 使用 ace.playbook.sections_config

### 问题描述

**当前状态**:
- ✅ `configs/ace_config.yaml:45` 定义了 `sections_config: "configs/playbook_sections.yaml"`
- ⚠️ `src/utils/section_manager.py:22` 有默认值 `"configs/playbook_sections.yaml"`，但不从 ace_config 读取

**影响**: 测试时无法灵活指定不同的 sections 配置文件

---

### 修改步骤

#### 修改 2.1: 在 PlaybookConfig 添加 sections_config 字段

**文件**: `src/utils/config_loader.py`

**修改位置**: 第61-83行

**修改前**:

```python
class PlaybookConfig(BaseModel):
    """Playbook structure configuration."""
    default_path: str = Field(default="data/playbooks/chemistry_playbook.json")
    sections: List[str] = Field(
        default_factory=lambda: [
            "material_selection",
            "procedure_design",
            "safety_protocols",
            "quality_control",
            "troubleshooting",
            "common_mistakes"
        ]
    )
    id_prefixes: Dict[str, str] = Field(
        default_factory=lambda: {
            "material_selection": "mat",
            "procedure_design": "proc",
            "safety_protocols": "safe",
            "quality_control": "qc",
            "troubleshooting": "ts",
            "common_mistakes": "err"
        }
    )
```

**修改后**:

```python
class PlaybookConfig(BaseModel):
    """Playbook structure configuration."""
    default_path: str = Field(default="data/playbooks/chemistry_playbook.json")
    sections_config: str = Field(default="configs/playbook_sections.yaml")  # 👈 添加这行
    sections: List[str] = Field(
        default_factory=lambda: [
            "material_selection",
            "procedure_design",
            "safety_protocols",
            "quality_control",
            "troubleshooting",
            "common_mistakes"
        ]
    )
    id_prefixes: Dict[str, str] = Field(
        default_factory=lambda: {
            "material_selection": "mat",
            "procedure_design": "proc",
            "safety_protocols": "safe",
            "quality_control": "qc",
            "troubleshooting": "ts",
            "common_mistakes": "err"
        }
    )
```

---

#### 修改 2.2: SectionManager 从配置读取路径

**文件**: `src/utils/section_manager.py`

**修改位置**: 第17-35行

**修改前**:

```python
class SectionManager:
    """管理playbook sections的加载、验证和动态添加"""

    def __init__(
        self,
        config_path: str = "configs/playbook_sections.yaml",  # 👈 硬编码默认值
        allow_new_sections: Optional[bool] = None
    ):
        """
        初始化Section Manager

        Args:
            config_path: Section配置文件路径
            allow_new_sections: 运行时覆盖配置文件中的allow_new_sections设置
                               如果为None，则使用配置文件中的值
        """
        project_root = Path(__file__).parent.parent.parent
        self.config_path = project_root / config_path
        self.config = self._load_config()

        # 运行时参数覆盖配置文件
        if allow_new_sections is not None:
            self.config['settings']['allow_new_sections'] = allow_new_sections
```

**修改后**:

```python
class SectionManager:
    """管理playbook sections的加载、验证和动态添加"""

    def __init__(
        self,
        config_path: Optional[str] = None,  # 👈 改为 Optional
        allow_new_sections: Optional[bool] = None
    ):
        """
        初始化Section Manager

        Args:
            config_path: Section配置文件路径（默认从ace_config读取）
            allow_new_sections: 运行时覆盖配置文件中的allow_new_sections设置
                               如果为None，则使用配置文件中的值
        """
        # 👇 从 ACE 配置读取默认路径
        if config_path is None:
            try:
                from utils.config_loader import get_ace_config
                ace_config = get_ace_config()
                config_path = ace_config.playbook.sections_config
            except Exception as e:
                # Fallback to default if config loading fails
                config_path = "configs/playbook_sections.yaml"
                print(f"⚠️ Warning: Could not load sections_config from ace_config, using default. Error: {e}")

        project_root = Path(__file__).parent.parent.parent
        self.config_path = project_root / config_path
        self.config = self._load_config()

        # 运行时参数覆盖配置文件
        if allow_new_sections is not None:
            self.config['settings']['allow_new_sections'] = allow_new_sections
```

---

### 验证步骤

#### 测试 2.1: 验证默认路径读取

```python
from src.utils.section_manager import SectionManager

# 不传入 config_path，应该从 ace_config 读取
manager = SectionManager()
print(f"✅ Config path: {manager.config_path}")

# 预期输出:
# ✅ Config path: /path/to/project/configs/playbook_sections.yaml
```

#### 测试 2.2: 验证自定义路径仍然生效

```python
# 手动指定路径（向后兼容）
manager = SectionManager(config_path="configs/test_sections.yaml")
print(f"✅ Custom config path: {manager.config_path}")

# 预期输出:
# ✅ Custom config path: /path/to/project/configs/test_sections.yaml
```

---

## 行动3: 配置化 min_similarity 阈值

### 问题描述

**当前状态**:
- ❌ `src/ace_framework/generator/generator.py:132` - 日志中硬编码 `min_similarity=0.3`
- ❌ `src/ace_framework/generator/generator.py:355` - 检索调用中硬编码 `min_similarity=0.3`

**影响**: 无法通过配置调整playbook bullet检索的相似度阈值

**原方案调整**: 删除了 `few_shot_top_k`（不存在于当前代码）

---

### 修改步骤

#### 修改 3.1: 在 GeneratorConfig 添加 min_similarity 字段

**文件**: `src/utils/config_loader.py`

**修改位置**: 第31-37行

**修改前**:

```python
class GeneratorConfig(BaseModel):
    """Configuration for ACE Generator."""
    max_playbook_bullets: int = Field(default=50, gt=0, description="Top-k bullets to retrieve")
    include_examples: bool = Field(default=True)
    enable_few_shot: bool = Field(default=True)
    few_shot_count: int = Field(default=3, ge=0)
    output_format: str = Field(default="structured", pattern="^(structured|markdown)$")
```

**修改后**:

```python
class GeneratorConfig(BaseModel):
    """Configuration for ACE Generator."""
    max_playbook_bullets: int = Field(default=50, gt=0, description="Top-k bullets to retrieve")
    min_similarity: float = Field(  # 👈 添加这行
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for playbook bullet retrieval"
    )
    include_examples: bool = Field(default=True)
    enable_few_shot: bool = Field(default=True)
    few_shot_count: int = Field(default=3, ge=0)
    output_format: str = Field(default="structured", pattern="^(structured|markdown)$")
```

---

#### 修改 3.2: 在 ace_config.yaml 添加配置

**文件**: `configs/ace_config.yaml`

**修改位置**: 第18-23行

**修改前**:

```yaml
  generator:
    max_playbook_bullets: 50  # Retrieve top-k relevant bullets
    include_examples: true
    enable_few_shot: true
    few_shot_count: 3
    output_format: "structured"  # "structured" or "markdown"
```

**修改后**:

```yaml
  generator:
    max_playbook_bullets: 50  # Retrieve top-k relevant bullets
    min_similarity: 0.3  # 👈 添加: Minimum similarity for bullet retrieval (0-1)
    include_examples: true
    enable_few_shot: true
    few_shot_count: 3
    output_format: "structured"  # "structured" or "markdown"
```

---

#### 修改 3.3: Generator 使用配置（两处修改）

**文件**: `src/ace_framework/generator/generator.py`

**修改位置1**: 第132行（日志记录）

**修改前**:

```python
self.logger.log_bullet_retrieval(
    query=requirements.get("objective", ""),
    bullets_retrieved=len(relevant_bullets),
    top_k=self.config.max_playbook_bullets,
    min_similarity=0.3,  # 👈 硬编码
    top_similarities=similarities,
    sections=section_counts
)
```

**修改后**:

```python
self.logger.log_bullet_retrieval(
    query=requirements.get("objective", ""),
    bullets_retrieved=len(relevant_bullets),
    top_k=self.config.max_playbook_bullets,
    min_similarity=self.config.min_similarity,  # 👈 从配置读取
    top_similarities=similarities,
    sections=section_counts
)
```

---

**修改位置2**: 第355行（实际检索调用）

**修改前**:

```python
# Retrieve bullets
retrieved = self.playbook_manager.retrieve_relevant_bullets(
    query=query,
    top_k=self.config.max_playbook_bullets,
    section_filter=section_filter,
    min_similarity=0.3  # 👈 硬编码
)
```

**修改后**:

```python
# Retrieve bullets
retrieved = self.playbook_manager.retrieve_relevant_bullets(
    query=query,
    top_k=self.config.max_playbook_bullets,
    section_filter=section_filter,
    min_similarity=self.config.min_similarity  # 👈 从配置读取
)
```

---

### 验证步骤

#### 测试 3.1: 验证配置加载

```python
from src.utils.config_loader import get_ace_config

config = get_ace_config()
print(f"✅ Min similarity: {config.generator.min_similarity}")

# 预期输出:
# ✅ Min similarity: 0.3
```

#### 测试 3.2: 验证 Generator 使用配置

```python
from src.ace_framework.generator.generator import PlanGenerator
from src.ace_framework.playbook.playbook_manager import PlaybookManager
from src.utils.llm_provider import QwenLLMProvider
from src.utils.config_loader import get_ace_config

config = get_ace_config()
playbook_manager = PlaybookManager(playbook_path="data/playbooks/chemistry_playbook.json")
llm = QwenLLMProvider()

generator = PlanGenerator(
    playbook_manager=playbook_manager,
    llm_provider=llm,
    config=config.generator
)

print(f"✅ Generator min_similarity: {generator.config.min_similarity}")

# 预期输出:
# ✅ Generator min_similarity: 0.3
```

---

## 测试计划

### 单元测试

创建 `tests/test_config_fixes.py`:

```python
import pytest
from src.utils.config_loader import get_ace_config


def test_embedding_config_loaded():
    """测试 embedding 配置正确加载"""
    config = get_ace_config()

    assert hasattr(config, 'embedding')
    assert config.embedding.model == "text-embedding-v4"


def test_playbook_sections_config_loaded():
    """测试 playbook.sections_config 配置正确加载"""
    config = get_ace_config()

    assert hasattr(config.playbook, 'sections_config')
    assert config.playbook.sections_config == "configs/playbook_sections.yaml"


def test_generator_min_similarity_loaded():
    """测试 generator.min_similarity 配置正确加载"""
    config = get_ace_config()

    assert hasattr(config.generator, 'min_similarity')
    assert config.generator.min_similarity == 0.3
    assert 0.0 <= config.generator.min_similarity <= 1.0


def test_curator_uses_embedding_config():
    """测试 Curator 使用 embedding 配置"""
    from src.ace_framework.curator.curator import PlaybookCurator
    from src.ace_framework.playbook.playbook_manager import PlaybookManager
    from src.utils.llm_provider import QwenLLMProvider

    config = get_ace_config()
    playbook_manager = PlaybookManager(playbook_path="data/playbooks/chemistry_playbook.json")
    llm = QwenLLMProvider()

    curator = PlaybookCurator(
        playbook_manager=playbook_manager,
        llm_provider=llm,
        config=config.curator
    )

    assert curator.embedding_manager.embedding_provider.model == config.embedding.model


def test_section_manager_uses_config_path():
    """测试 SectionManager 使用配置路径"""
    from src.utils.section_manager import SectionManager

    config = get_ace_config()
    manager = SectionManager()  # 不传入路径

    # 验证使用了配置中的路径
    assert str(manager.config_path).endswith(config.playbook.sections_config)
```

运行测试:

```bash
conda activate OntologyConstruction
cd /home/syk/projects/experiment-plan-design
pytest tests/test_config_fixes.py -v
```

---

### 集成测试

#### 端到端配置修改测试

1. 备份 `configs/ace_config.yaml`
2. 修改配置:

```yaml
ace:
  embedding:
    model: "text-embedding-v3"
  generator:
    min_similarity: 0.5
  playbook:
    sections_config: "configs/playbook_sections.yaml"
```

3. 运行完整生成流程，检查日志确认使用了新值
4. 恢复配置

---

## 回滚方案

### 自动回滚脚本

```bash
#!/bin/bash
# scripts/rollback_config_fixes.sh

echo "🔄 开始回滚配置修复..."

# 回滚 Git 修改
git checkout -- src/utils/config_loader.py
git checkout -- src/ace_framework/curator/curator.py
git checkout -- src/utils/section_manager.py
git checkout -- src/ace_framework/generator/generator.py
git checkout -- configs/ace_config.yaml

echo "✅ 代码文件已回滚"

# 删除测试文件（如果存在）
if [ -f "tests/test_config_fixes.py" ]; then
    rm tests/test_config_fixes.py
    echo "✅ 测试文件已删除"
fi

echo "🎉 回滚完成！"
```

---

## 修改文件清单

| 文件 | 修改内容 | 行数变化 |
|------|---------|---------|
| `src/utils/config_loader.py` | 添加 EmbeddingConfig, 3个字段 | +8 |
| `src/ace_framework/curator/curator.py` | 从配置读取 embedding model | +5 |
| `src/utils/section_manager.py` | 从配置读取路径 | +8 |
| `src/ace_framework/generator/generator.py` | 使用配置的 min_similarity | +2 (两处) |
| `configs/ace_config.yaml` | 添加 min_similarity | +1 |
| `tests/test_config_fixes.py` | 新建测试文件 | +80 |

**总计**: 约 112 行代码修改

---

## 执行时间线

| 阶段 | 任务 | 预计时间 |
|------|------|---------|
| 1 | 创建分支、备份配置 | 10分钟 |
| 2 | 行动1 - Embedding配置 | 45分钟 |
| 3 | 行动2 - Sections配置路径 | 30分钟 |
| 4 | 行动3 - Min similarity阈值 | 30分钟 |
| 5 | 编写测试 | 45分钟 |
| 6 | 运行测试和修复问题 | 30分钟 |
| 7 | 文档和提交 | 20分钟 |

**总计**: 约 3.5 小时

---

## 成功标准

### ✅ 功能验证

- [ ] `ace.embedding.model` 配置可以正确加载
- [ ] Curator 使用配置中的 embedding model
- [ ] `ace.playbook.sections_config` 配置可以正确加载
- [ ] SectionManager 从配置读取路径（有fallback）
- [ ] Generator 使用配置中的 `min_similarity`
- [ ] 所有新增配置有合理默认值
- [ ] 所有新增配置有 Pydantic 验证

### ✅ 测试验证

- [ ] 所有单元测试通过
- [ ] 集成测试生成质量无下降
- [ ] 回归测试无新增失败

### ✅ 代码质量

- [ ] 代码符合项目规范
- [ ] 添加必要的类型注解
- [ ] 添加 docstring
- [ ] 异常处理完善
- [ ] 有 fallback 机制

---

## 与原方案的差异

| 原方案内容 | 调整后 | 原因 |
|-----------|-------|------|
| EmbeddingConfig 包含 batch_size | 删除 batch_size | 它是 encode() 方法参数，不是实例属性 |
| 修改 EmbeddingManager.__init__ 添加 batch_size | 不修改 | 当前设计已经合理 |
| 添加 few_shot_top_k 配置 | 删除整个内容 | few_shot_examples 是外部传入的，不是内部检索 |
| template_similarity_threshold | 改为 min_similarity | 与实际代码参数名一致 |
| 预计工时 4-6 小时 | 调整为 3-4 小时 | 减少了不必要的修改 |

---

**方案版本**: v2.0 (基于代码调研更新)
**审阅状态**: ✅ 已完成代码调研
**下一步**: 等待批准后开始执行
