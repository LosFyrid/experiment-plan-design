# 配置修复立即行动方案

**创建日期**: 2025-10-28
**优先级**: 🔥 高优先级
**预计工时**: 4-6小时
**风险等级**: 🟡 中等

---

## 目录

1. [行动1: 修复 ace.embedding 配置加载](#行动1-修复-aceembedding-配置加载)
2. [行动2: 使用 ace.playbook.sections_config](#行动2-使用-aceplaybooksections_config)
3. [行动3: 配置化硬编码阈值](#行动3-配置化硬编码阈值)
4. [测试计划](#测试计划)
5. [回滚方案](#回滚方案)
6. [风险评估](#风险评估)

---

## 行动1: 修复 ace.embedding 配置加载

### 问题描述

**当前状态**:
- `configs/ace_config.yaml:12-15` 定义了 `ace.embedding` 配置节
- `src/utils/config_loader.py` 的 `ACEConfig` 类**没有**加载这个配置节
- 导致无法通过配置文件控制embedding参数

**影响范围**:
- Curator的语义去重功能
- 可能影响playbook bullet的deduplication行为

### 具体修改

#### 修改1.1: 添加 EmbeddingConfig Pydantic模型

**文件**: `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py`

**位置**: 在 `ModelConfig` 之后（约第26行）

**添加内容**:
```python
class EmbeddingConfig(BaseModel):
    """Embedding configuration for ACE framework."""
    model: str = Field(default="text-embedding-v4", description="Qwen embedding model")
    batch_size: int = Field(default=10, gt=0, le=25, description="Qwen API batch size limit")
```

**代码插入位置**:
```python
# ============================================================================
# Model Configuration
# ============================================================================

class ModelConfig(BaseModel):
    """LLM model configuration."""
    provider: str = Field(default="qwen", pattern="^(qwen|openai|anthropic)$")
    model_name: str = Field(default="qwen-max")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)


# 👇 在这里添加 EmbeddingConfig
class EmbeddingConfig(BaseModel):
    """Embedding configuration for ACE framework."""
    model: str = Field(default="text-embedding-v4", description="Qwen embedding model")
    batch_size: int = Field(default=10, gt=0, le=25, description="Qwen API batch size limit")


# ============================================================================
# ACE Component Configurations
# ============================================================================
```

#### 修改1.2: 在 ACEConfig 中添加 embedding 字段

**文件**: `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py`

**位置**: 约第119行，`ACEConfig` 类定义

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

#### 修改1.3: 在 Curator 中使用配置

**文件**: `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py`

**位置**: 约第91行，`__init__` 方法

**查找当前代码**:
```python
# Initialize embedding manager for deduplication
self.embedding_manager = EmbeddingManager(
    model_name="BAAI/bge-small-zh-v1.5"  # 👈 当前硬编码
)
```

**需要修改为**:
```python
# Initialize embedding manager for deduplication
# Load ACE config to get embedding settings
from src.utils.config_loader import get_ace_config
ace_config = get_ace_config()

self.embedding_manager = EmbeddingManager(
    model_name=ace_config.embedding.model  # 👈 从配置读取
)
```

**但是注意**: 检查 `EmbeddingManager` 是否支持 `batch_size` 参数

**需要检查**: `/home/syk/projects/experiment-plan-design/src/utils/embedding_utils.py`

如果不支持，需要同步修改 `EmbeddingManager` 类。

#### 修改1.4: 更新 EmbeddingManager（如果需要）

**文件**: `/home/syk/projects/experiment-plan-design/src/utils/embedding_utils.py`

**当前签名**（约第20行）:
```python
class EmbeddingManager:
    def __init__(self, model_name: str = "text-embedding-v4"):
        self.model_name = model_name
        # ...
```

**可能需要添加**:
```python
class EmbeddingManager:
    def __init__(
        self,
        model_name: str = "text-embedding-v4",
        batch_size: int = 10  # 👈 添加batch_size参数
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        # ...
```

**然后在 `encode()` 方法中使用** (约第30-50行):
```python
def encode(self, texts: List[str]) -> np.ndarray:
    """Encode texts to embeddings."""
    # 使用 self.batch_size 而不是硬编码的10
    for i in range(0, len(texts), self.batch_size):
        batch = texts[i:i + self.batch_size]
        # ...
```

### 验证步骤

#### 步骤1: 验证配置加载
```python
# 测试脚本
from src.utils.config_loader import get_ace_config

config = get_ace_config()
print(f"Embedding model: {config.embedding.model}")
print(f"Embedding batch_size: {config.embedding.batch_size}")

# 预期输出:
# Embedding model: text-embedding-v4
# Embedding batch_size: 10
```

#### 步骤2: 验证Curator使用
```python
# 运行 examples/ace_cycle_example.py 或创建测试
from src.ace_framework.curator.curator import create_curator

curator = create_curator()
print(f"Curator embedding model: {curator.embedding_manager.model_name}")

# 预期输出:
# Curator embedding model: text-embedding-v4
```

#### 步骤3: 修改配置并验证
```yaml
# 修改 configs/ace_config.yaml
ace:
  embedding:
    model: "text-embedding-v3"  # 改为v3测试
    batch_size: 5
```

重新运行步骤1和步骤2，确认读取了新值。

### 回滚方案

如果出现问题，执行以下回滚：

1. **Git回滚**: `git checkout -- src/utils/config_loader.py src/ace_framework/curator/curator.py src/utils/embedding_utils.py`
2. **手动回滚**: 删除添加的 `EmbeddingConfig` 类和 `ACEConfig.embedding` 字段

---

## 行动2: 使用 ace.playbook.sections_config

### 问题描述

**当前状态**:
- `configs/ace_config.yaml:45` 定义了 `sections_config: "configs/playbook_sections.yaml"`
- `src/utils/section_manager.py:21` **硬编码**了配置路径

**硬编码位置**:
```python
# src/utils/section_manager.py:21
DEFAULT_CONFIG_PATH = "configs/playbook_sections.yaml"  # 👈 硬编码
```

**影响**:
- 无法通过配置灵活指定sections配置文件路径
- 测试时无法使用独立配置文件

### 具体修改

#### 修改2.1: SectionManager 支持从ACE配置读取路径

**文件**: `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py`

**位置**: 约第13-30行

**修改前**:
```python
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from datetime import datetime


DEFAULT_CONFIG_PATH = "configs/playbook_sections.yaml"


class SectionManager:
    """管理playbook sections配置"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        allow_new_sections: Optional[bool] = None
    ):
        """
        Args:
            config_path: sections配置文件路径（默认从ace_config读取）
            allow_new_sections: 是否允许新增sections（运行时覆盖）
        """
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH)
```

**修改后**:
```python
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from datetime import datetime


class SectionManager:
    """管理playbook sections配置"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        allow_new_sections: Optional[bool] = None
    ):
        """
        Args:
            config_path: sections配置文件路径（默认从ace_config读取）
            allow_new_sections: 是否允许新增sections（运行时覆盖）
        """
        # 👇 修改：从ACE配置读取默认路径
        if config_path is None:
            try:
                from src.utils.config_loader import get_ace_config
                ace_config = get_ace_config()
                config_path = ace_config.playbook.sections_config
            except Exception as e:
                # Fallback to default if config loading fails
                config_path = "configs/playbook_sections.yaml"
                print(f"Warning: Could not load sections_config from ace_config, using default. Error: {e}")

        self.config_path = Path(config_path)
```

#### 修改2.2: 添加 sections_config 到 PlaybookConfig

**检查**: `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py`

**查找 PlaybookConfig** (约第61-83行):

**当前代码**:
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

**需要添加**:
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

### 验证步骤

#### 步骤1: 验证默认路径读取
```python
from src.utils.section_manager import SectionManager

# 不传入config_path，应该从ace_config读取
manager = SectionManager()
print(f"Config path: {manager.config_path}")

# 预期输出:
# Config path: configs/playbook_sections.yaml
```

#### 步骤2: 验证自定义路径
```python
# 创建测试配置文件
test_config_path = "configs/test_playbook_sections.yaml"

# 手动指定路径
manager = SectionManager(config_path=test_config_path)
print(f"Config path: {manager.config_path}")

# 预期输出:
# Config path: configs/test_playbook_sections.yaml
```

#### 步骤3: 修改ace_config并验证
```yaml
# 修改 configs/ace_config.yaml
ace:
  playbook:
    sections_config: "configs/custom_sections.yaml"  # 改为自定义路径
```

重新运行步骤1，确认读取了新路径。

### 回滚方案

1. **Git回滚**: `git checkout -- src/utils/section_manager.py src/utils/config_loader.py`
2. **手动回滚**: 恢复 `DEFAULT_CONFIG_PATH` 常量

---

## 行动3: 配置化硬编码阈值

### 问题描述

**当前硬编码位置**:

1. **模板相似度阈值**: `src/ace_framework/generator/prompts.py:50`
   ```python
   similarity_threshold=0.3  # 👈 硬编码
   ```

2. **Few-shot top_k**: `src/ace_framework/generator/prompts.py:144`
   ```python
   top_k=3  # 👈 硬编码
   ```

3. **其他硬编码**: 详见配置审计报告第8节

**影响**:
- 无法通过配置调整模板检索策略
- 无法通过配置调整few-shot示例数量

### 具体修改

#### 修改3.1: 在 GeneratorConfig 中添加参数

**文件**: `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py`

**位置**: 约第31-37行，`GeneratorConfig` 类

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
    include_examples: bool = Field(default=True)
    enable_few_shot: bool = Field(default=True)
    few_shot_count: int = Field(default=3, ge=0)
    few_shot_top_k: int = Field(default=3, ge=1, le=10, description="Top-k for few-shot examples")  # 👈 新增
    output_format: str = Field(default="structured", pattern="^(structured|markdown)$")
    template_similarity_threshold: float = Field(  # 👈 新增
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for template retrieval"
    )
```

#### 修改3.2: 在 ace_config.yaml 中添加配置

**文件**: `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml`

**位置**: 约第19-23行，`generator` 节

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
    include_examples: true
    enable_few_shot: true
    few_shot_count: 3
    few_shot_top_k: 3  # 👈 新增: Few-shot示例检索数量
    output_format: "structured"  # "structured" or "markdown"
    template_similarity_threshold: 0.3  # 👈 新增: 模板相似度阈值 (0-1)
```

#### 修改3.3: 在 Generator 中使用配置

**文件**: `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/prompts.py`

**位置1**: 约第50行

**修改前**:
```python
def select_relevant_templates(
    templates: List[Dict[str, Any]],
    requirements: Dict[str, Any],
    top_k: int = 5,
    similarity_threshold: float = 0.3  # 👈 硬编码默认值
) -> List[Dict[str, Any]]:
```

**修改后**:
```python
def select_relevant_templates(
    templates: List[Dict[str, Any]],
    requirements: Dict[str, Any],
    top_k: int = 5,
    similarity_threshold: float = 0.3  # 保留默认值作为fallback
) -> List[Dict[str, Any]]:
```

**位置2**: 约第144行

**修改前**:
```python
def get_few_shot_examples(
    playbook_bullets: List[PlaybookBullet],
    top_k: int = 3  # 👈 硬编码默认值
) -> List[Dict[str, Any]]:
```

**修改后**:
```python
def get_few_shot_examples(
    playbook_bullets: List[PlaybookBullet],
    top_k: int = 3  # 保留默认值作为fallback
) -> List[Dict[str, Any]]:
```

**调用位置**: `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py`

**需要查找**: 在 `generate()` 方法中调用这些函数的位置

**预期修改**（需要找到确切行号）:
```python
# 修改前
relevant_templates = select_relevant_templates(
    templates=templates,
    requirements=requirements,
    top_k=5,
    similarity_threshold=0.3  # 👈 硬编码
)

few_shot_examples = get_few_shot_examples(
    playbook_bullets=relevant_bullets,
    top_k=3  # 👈 硬编码
)

# 修改后
relevant_templates = select_relevant_templates(
    templates=templates,
    requirements=requirements,
    top_k=5,
    similarity_threshold=self.config.template_similarity_threshold  # 👈 从配置读取
)

few_shot_examples = get_few_shot_examples(
    playbook_bullets=relevant_bullets,
    top_k=self.config.few_shot_top_k  # 👈 从配置读取
)
```

**⚠️ 重要**: 需要先用Grep找到确切的调用位置和行号：

```bash
# 搜索调用位置
cd /home/syk/projects/experiment-plan-design
grep -n "select_relevant_templates" src/ace_framework/generator/generator.py
grep -n "get_few_shot_examples" src/ace_framework/generator/generator.py
```

### 验证步骤

#### 步骤1: 验证配置加载
```python
from src.utils.config_loader import get_ace_config

config = get_ace_config()
print(f"Template similarity threshold: {config.generator.template_similarity_threshold}")
print(f"Few-shot top_k: {config.generator.few_shot_top_k}")

# 预期输出:
# Template similarity threshold: 0.3
# Few-shot top_k: 3
```

#### 步骤2: 验证Generator使用
```python
from src.ace_framework.generator.generator import create_generator

generator = create_generator()
print(f"Generator config threshold: {generator.config.template_similarity_threshold}")
print(f"Generator config few_shot_top_k: {generator.config.few_shot_top_k}")

# 预期输出:
# Generator config threshold: 0.3
# Generator config few_shot_top_k: 3
```

#### 步骤3: 修改配置并运行完整生成
```yaml
# 修改 configs/ace_config.yaml
ace:
  generator:
    template_similarity_threshold: 0.5  # 提高阈值
    few_shot_top_k: 5  # 增加示例数量
```

运行 `examples/run_simple_ace.py`，检查日志中是否使用了新值。

### 回滚方案

1. **Git回滚**: `git checkout -- src/utils/config_loader.py configs/ace_config.yaml src/ace_framework/generator/generator.py`
2. **配置回滚**: 将配置值改回0.3和3

---

## 测试计划

### 单元测试

#### 测试1: 配置加载测试

**创建文件**: `tests/test_config_fixes.py`

```python
import pytest
from src.utils.config_loader import get_ace_config


def test_embedding_config_loaded():
    """测试 embedding 配置正确加载"""
    config = get_ace_config()

    # 验证字段存在
    assert hasattr(config, 'embedding')

    # 验证默认值
    assert config.embedding.model == "text-embedding-v4"
    assert config.embedding.batch_size == 10


def test_playbook_sections_config_loaded():
    """测试 playbook.sections_config 配置正确加载"""
    config = get_ace_config()

    # 验证字段存在
    assert hasattr(config.playbook, 'sections_config')

    # 验证默认值
    assert config.playbook.sections_config == "configs/playbook_sections.yaml"


def test_generator_thresholds_loaded():
    """测试 generator 阈值配置正确加载"""
    config = get_ace_config()

    # 验证新增字段
    assert hasattr(config.generator, 'template_similarity_threshold')
    assert hasattr(config.generator, 'few_shot_top_k')

    # 验证默认值
    assert config.generator.template_similarity_threshold == 0.3
    assert config.generator.few_shot_top_k == 3

    # 验证范围
    assert 0.0 <= config.generator.template_similarity_threshold <= 1.0
    assert 1 <= config.generator.few_shot_top_k <= 10
```

运行测试:
```bash
conda activate OntologyConstruction
cd /home/syk/projects/experiment-plan-design
pytest tests/test_config_fixes.py -v
```

#### 测试2: 组件集成测试

```python
def test_curator_uses_embedding_config():
    """测试 Curator 使用 embedding 配置"""
    from src.ace_framework.curator.curator import create_curator
    from src.utils.config_loader import get_ace_config

    config = get_ace_config()
    curator = create_curator()

    # 验证使用了配置中的模型
    assert curator.embedding_manager.model_name == config.embedding.model


def test_section_manager_uses_config_path():
    """测试 SectionManager 使用配置路径"""
    from src.utils.section_manager import SectionManager
    from src.utils.config_loader import get_ace_config

    config = get_ace_config()
    manager = SectionManager()  # 不传入路径

    # 验证使用了配置中的路径
    assert str(manager.config_path) == config.playbook.sections_config


def test_generator_uses_threshold_config():
    """测试 Generator 使用阈值配置"""
    from src.ace_framework.generator.generator import create_generator
    from src.utils.config_loader import get_ace_config

    config = get_ace_config()
    generator = create_generator()

    # 验证配置可访问
    assert generator.config.template_similarity_threshold == config.generator.template_similarity_threshold
    assert generator.config.few_shot_top_k == config.generator.few_shot_top_k
```

### 集成测试

#### 测试3: 端到端配置修改测试

**测试步骤**:
1. 备份当前配置
2. 修改 `configs/ace_config.yaml`:
   ```yaml
   ace:
     embedding:
       model: "text-embedding-v3"
       batch_size: 5
     generator:
       template_similarity_threshold: 0.5
       few_shot_top_k: 5
     playbook:
       sections_config: "configs/playbook_sections.yaml"
   ```
3. 运行 `examples/run_simple_ace.py`
4. 检查日志确认使用了新配置值
5. 恢复配置

**预期结果**:
- 日志中显示 `text-embedding-v3`
- 模板检索使用 threshold 0.5
- Few-shot 使用 top_k=5

### 回归测试

运行现有测试套件确保没有破坏现有功能:

```bash
# 运行所有ACE框架测试
pytest tests/ace_framework/ -v

# 运行配置相关测试
pytest tests/test_config_loader.py -v
pytest tests/test_section_manager.py -v

# 运行Curator测试
pytest tests/test_curator*.py -v
```

---

## 回滚方案

### 自动回滚脚本

**创建文件**: `scripts/rollback_config_fixes.sh`

```bash
#!/bin/bash
# 配置修复回滚脚本

echo "🔄 开始回滚配置修复..."

# 回滚Git修改
git checkout -- src/utils/config_loader.py
git checkout -- src/ace_framework/curator/curator.py
git checkout -- src/utils/embedding_utils.py
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

使用方法:
```bash
chmod +x scripts/rollback_config_fixes.sh
./scripts/rollback_config_fixes.sh
```

### 手动回滚清单

如果自动脚本失败，按以下步骤手动回滚：

- [ ] 删除 `src/utils/config_loader.py` 中的 `EmbeddingConfig` 类
- [ ] 删除 `ACEConfig.embedding` 字段
- [ ] 删除 `PlaybookConfig.sections_config` 字段
- [ ] 删除 `GeneratorConfig.template_similarity_threshold` 字段
- [ ] 删除 `GeneratorConfig.few_shot_top_k` 字段
- [ ] 恢复 `src/utils/section_manager.py` 中的 `DEFAULT_CONFIG_PATH`
- [ ] 恢复 `src/ace_framework/curator/curator.py` 中硬编码的 embedding model
- [ ] 恢复 `src/ace_framework/generator/generator.py` 中的硬编码阈值
- [ ] 删除 `configs/ace_config.yaml` 中新增的配置项
- [ ] 删除 `tests/test_config_fixes.py`

---

## 风险评估

### 🟢 低风险

**行动2: 使用 ace.playbook.sections_config**
- **风险**: 低
- **原因**: 仅修改路径读取逻辑，有fallback机制
- **缓解**: 异常处理确保失败时使用默认路径

### 🟡 中等风险

**行动1: 修复 ace.embedding 配置加载**
- **风险**: 中等
- **原因**:
  - 修改Curator初始化逻辑
  - 可能影响embedding行为
  - EmbeddingManager可能需要同步修改
- **缓解**:
  - 保持默认值与原硬编码值一致
  - 充分测试Curator去重功能
  - 提供清晰的回滚路径

**行动3: 配置化硬编码阈值**
- **风险**: 中等
- **原因**:
  - 修改Generator核心逻辑
  - 影响模板检索和few-shot行为
  - 可能影响生成质量
- **缓解**:
  - 保持默认值与原硬编码值一致
  - 运行端到端测试验证生成质量
  - 准备回滚方案

### 🔴 高风险

**无高风险项** - 所有修改都保持了向后兼容性

### 风险缓解措施

1. **保持默认值不变**: 所有新配置项默认值与原硬编码值相同
2. **异常处理**: 配置加载失败时fallback到默认值
3. **充分测试**: 单元测试 + 集成测试 + 回归测试
4. **Git分支**: 在feature分支上进行修改
5. **代码审查**: 提交前进行peer review
6. **灰度发布**: 先在测试环境验证，再合并到main

---

## 执行时间线

### 阶段1: 准备工作 (30分钟)

- [ ] 创建feature分支: `git checkout -b fix/config-loading`
- [ ] 备份当前配置文件
- [ ] 阅读相关代码，确认修改点
- [ ] 准备测试环境

### 阶段2: 行动1 - Embedding配置 (1.5小时)

- [ ] 修改 `config_loader.py` 添加 `EmbeddingConfig`
- [ ] 修改 `ACEConfig` 添加 `embedding` 字段
- [ ] 检查并修改 `EmbeddingManager` (如需要)
- [ ] 修改 `curator.py` 使用配置
- [ ] 编写单元测试
- [ ] 运行测试验证

### 阶段3: 行动2 - Sections配置路径 (1小时)

- [ ] 修改 `config_loader.py` 添加 `sections_config` 字段
- [ ] 修改 `section_manager.py` 从配置读取路径
- [ ] 编写单元测试
- [ ] 运行测试验证

### 阶段4: 行动3 - 硬编码阈值 (1.5小时)

- [ ] 修改 `config_loader.py` 添加阈值字段
- [ ] 修改 `ace_config.yaml` 添加配置项
- [ ] 搜索确认 `generator.py` 中的调用位置
- [ ] 修改 `generator.py` 使用配置
- [ ] 编写单元测试
- [ ] 运行测试验证

### 阶段5: 综合测试 (1小时)

- [ ] 运行所有单元测试
- [ ] 运行集成测试
- [ ] 运行回归测试
- [ ] 运行端到端测试
- [ ] 修复发现的问题

### 阶段6: 文档和清理 (30分钟)

- [ ] 更新配置文档
- [ ] 添加 CHANGELOG 条目
- [ ] 提交代码: `git commit -m "fix: Add missing config parameters and use config instead of hardcoded values"`
- [ ] 创建PR

**总预计时间**: 6小时

---

## 成功标准

修复完成后，应满足以下标准：

### ✅ 功能标准

- [ ] `ace.embedding` 配置可以正确加载
- [ ] Curator使用配置中的embedding参数
- [ ] `ace.playbook.sections_config` 配置可以正确加载
- [ ] SectionManager从配置读取路径（带fallback）
- [ ] Generator使用配置中的阈值参数
- [ ] 所有新增配置都有合理的默认值
- [ ] 所有新增配置都有Pydantic验证

### ✅ 测试标准

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 回归测试无新增失败
- [ ] 端到端测试生成质量无下降
- [ ] 测试覆盖率 ≥ 80%

### ✅ 代码质量标准

- [ ] 代码符合项目规范
- [ ] 添加了必要的类型注解
- [ ] 添加了docstring
- [ ] 没有硬编码magic number
- [ ] 异常处理完善

### ✅ 文档标准

- [ ] 配置参数有完整说明
- [ ] README更新（如需要）
- [ ] CHANGELOG更新
- [ ] 代码注释清晰

---

## 后续优化建议

完成立即行动后，可考虑以下优化：

1. **配置验证工具**: 创建脚本检查配置文件完整性
2. **配置迁移工具**: 帮助用户从旧版配置迁移到新版
3. **配置模板**: 提供不同场景的配置模板（开发、测试、生产）
4. **配置文档**: 自动生成配置参数文档
5. **配置可视化**: Web界面管理配置参数

---

## 附录

### 附录A: 相关文件清单

**需要修改的文件**:
- `src/utils/config_loader.py` - 添加配置类
- `configs/ace_config.yaml` - 添加配置项
- `src/ace_framework/curator/curator.py` - 使用embedding配置
- `src/utils/embedding_utils.py` - 支持batch_size参数（可能）
- `src/utils/section_manager.py` - 从配置读取路径
- `src/ace_framework/generator/generator.py` - 使用阈值配置

**需要创建的文件**:
- `tests/test_config_fixes.py` - 配置修复测试
- `scripts/rollback_config_fixes.sh` - 回滚脚本（可选）

**需要查看的文件**:
- `src/ace_framework/generator/prompts.py` - 确认硬编码位置
- `docs/config_usage_detailed.md` - 配置审计报告

### 附录B: 命令速查

```bash
# 激活环境
conda activate OntologyConstruction

# 创建分支
git checkout -b fix/config-loading

# 运行测试
pytest tests/test_config_fixes.py -v

# 运行所有测试
pytest tests/ -v

# 代码格式化
black src/ tests/

# 类型检查
mypy src/

# 提交代码
git add .
git commit -m "fix: Add missing config parameters"
git push origin fix/config-loading
```

### 附录C: 问题排查清单

如果修改后出现问题，检查以下事项：

**配置加载失败**:
- [ ] 检查YAML语法是否正确
- [ ] 检查Pydantic model字段名是否匹配
- [ ] 检查默认值是否设置
- [ ] 检查Field验证规则

**Curator初始化失败**:
- [ ] 检查EmbeddingManager是否支持新参数
- [ ] 检查import路径是否正确
- [ ] 检查配置是否成功加载

**Generator行为异常**:
- [ ] 检查阈值范围是否合理
- [ ] 检查配置传递路径
- [ ] 查看日志确认使用的值
- [ ] 对比修改前后的生成结果

**测试失败**:
- [ ] 检查测试环境是否正确
- [ ] 检查配置文件是否存在
- [ ] 检查pytest fixture设置
- [ ] 查看详细错误信息

---

**执行方案版本**: v1.0
**最后更新**: 2025-10-28
**审阅状态**: 待审阅
