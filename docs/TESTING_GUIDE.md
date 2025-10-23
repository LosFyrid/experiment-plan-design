# ACE Framework 测试指南

本文档详细说明如何测试ACE框架的各个层级。

---

## 🎯 测试分层架构

```
测试层级                    | 依赖组件            | 运行难度 | 当前状态
---------------------------|-------------------|---------|----------
Level 0: 配置验证          | 无                | ⭐       | ✅ 可运行
Level 1: 单元测试          | 无LLM API         | ⭐       | ✅ 可运行
Level 2: ACE组件测试       | LLM API           | ⭐⭐     | ✅ 可运行
Level 3: Mock集成测试      | LLM API           | ⭐⭐     | ✅ 可运行
Level 4: 完整集成测试      | MOSES + RAG + LLM | ⭐⭐⭐⭐  | ❌ 未实现
Level 5: 端到端测试        | 全部组件          | ⭐⭐⭐⭐⭐ | ❌ 未实现
```

---

## Level 0: 配置验证（0分钟设置）

### 目的
验证配置文件格式正确，无需任何API key。

### 运行步骤

```bash
# 1. 验证YAML语法
python -c "
import yaml
with open('configs/ace_config.yaml') as f:
    config = yaml.safe_load(f)
print('✓ ace_config.yaml is valid')

with open('configs/rag_config.yaml') as f:
    config = yaml.safe_load(f)
print('✓ rag_config.yaml is valid')
"

# 2. 验证Pydantic模型加载
python -c "
from src.utils.config_loader import get_ace_config, get_rag_config

ace_config = get_ace_config()
print(f'✓ ACE config loaded: {ace_config.model.model_name}')

rag_config = get_rag_config()
print(f'✓ RAG config loaded: {rag_config.embeddings.model_name}')
"

# 3. 检查文件结构
python -c "
from pathlib import Path

required_files = [
    'configs/ace_config.yaml',
    'configs/rag_config.yaml',
    'data/playbooks/chemistry_playbook.json',
    'src/ace_framework/generator/generator.py',
    'src/ace_framework/reflector/reflector.py',
    'src/ace_framework/curator/curator.py',
]

missing = [f for f in required_files if not Path(f).exists()]
if missing:
    print('❌ Missing files:', missing)
else:
    print('✓ All required files present')
"
```

### 预期输出

```
✓ ace_config.yaml is valid
✓ rag_config.yaml is valid
✓ ACE config loaded: qwen-max
✓ RAG config loaded: BAAI/bge-large-zh-v1.5
✓ All required files present
```

### 常见问题

**Error: `ModuleNotFoundError: No module named 'yaml'`**
```bash
pip install pyyaml
```

**Error: `FileNotFoundError: configs/ace_config.yaml`**
```bash
# 检查当前目录
pwd  # 应该在项目根目录

# 或者设置PROJECT_ROOT环境变量
export PROJECT_ROOT=/path/to/experiment-plan-design
```

---

## Level 1: 单元测试（5分钟设置）

### 目的
测试Playbook数据结构和基础功能，**无需LLM API**。

### 准备工作

```bash
# 1. 安装测试依赖
pip install pytest pytest-cov

# 2. 安装轻量级embedding模型（用于测试）
pip install sentence-transformers
# 首次运行会自动下载 sentence-transformers/all-MiniLM-L6-v2 (~80MB)
```

### 运行测试

```bash
# 运行所有单元测试
pytest tests/test_playbook.py -v

# 运行特定测试类
pytest tests/test_playbook.py::TestBulletMetadata -v
pytest tests/test_playbook.py::TestPlaybookManager -v

# 带覆盖率报告
pytest tests/test_playbook.py --cov=src.ace_framework.playbook --cov-report=term-missing

# 详细输出
pytest tests/test_playbook.py -vv -s
```

### 测试内容

#### 1. BulletMetadata测试
```python
# 测试helpfulness_score计算
def test_helpfulness_score_calculation():
    # All helpful
    metadata = BulletMetadata(helpful_count=10, harmful_count=0)
    assert metadata.helpfulness_score == 1.0

    # All harmful
    metadata = BulletMetadata(helpful_count=0, harmful_count=10)
    assert metadata.helpfulness_score == 0.0

    # Mixed
    metadata = BulletMetadata(helpful_count=7, harmful_count=3)
    assert metadata.helpfulness_score == 0.7
```

#### 2. PlaybookBullet测试
```python
# 测试ID验证
def test_bullet_id_validation():
    # Valid ID
    bullet = PlaybookBullet(id="mat-00001", section="material_selection", ...)
    assert bullet.id == "mat-00001"

    # Invalid ID (应该抛出ValueError)
    with pytest.raises(ValueError):
        PlaybookBullet(id="invalid", section="test", ...)
```

#### 3. PlaybookManager测试
```python
# 测试save/load
def test_save_and_load(temp_playbook_path):
    manager = PlaybookManager(playbook_path=str(temp_playbook_path))
    playbook = Playbook()
    playbook.bullets.append(PlaybookBullet(...))

    manager._playbook = playbook
    manager.save()

    manager2 = PlaybookManager(playbook_path=str(temp_playbook_path))
    loaded = manager2.load()

    assert loaded.size == 1
```

### 预期输出

```
tests/test_playbook.py::TestBulletMetadata::test_default_values PASSED          [ 14%]
tests/test_playbook.py::TestBulletMetadata::test_helpfulness_score_calculation PASSED [ 28%]
tests/test_playbook.py::TestPlaybookBullet::test_bullet_creation PASSED        [ 42%]
tests/test_playbook.py::TestPlaybookBullet::test_bullet_id_validation PASSED   [ 57%]
tests/test_playbook.py::TestPlaybook::test_playbook_creation PASSED            [ 71%]
tests/test_playbook.py::TestPlaybook::test_get_bullets_by_section PASSED       [ 85%]
tests/test_playbook.py::TestPlaybookManager::test_save_and_load PASSED         [100%]

========================== 7 passed in 2.34s ==========================
```

### 运行时间
- 首次运行: ~30秒（下载embedding模型）
- 后续运行: ~2-3秒

---

## Level 2: ACE组件测试（10分钟设置）

### 目的
测试Generator/Reflector/Curator三个核心组件，**需要LLM API**。

### 准备工作

```bash
# 1. 创建.env文件
cp .env.example .env

# 2. 编辑.env，添加API key
vim .env
# 添加: DASHSCOPE_API_KEY=your_key_here

# 3. 验证API key
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('DASHSCOPE_API_KEY')
if api_key:
    print(f'✓ API key loaded: {api_key[:10]}...')
else:
    print('❌ API key not found')
"

# 4. 测试LLM连接
python -c "
from src.utils.llm_provider import create_llm_provider

llm = create_llm_provider(provider='qwen', model_name='qwen-max')
response = llm.generate('Hello', system_prompt='You are a helpful assistant.')
print(f'✓ LLM connection successful: {len(response)} chars')
"
```

### 运行完整ACE循环

```bash
# 运行示例
python examples/ace_cycle_example.py

# 预期运行时间: ~2-3分钟
# - Generator: ~30秒
# - Reflector (5 rounds): ~90秒
# - Curator: ~30秒
```

### 测试输出解读

#### Step [5/7]: Generator
```
[5/7] Generating experiment plan...
  Target: Aspirin (Acetylsalicylic acid)
  Objective: Synthesize aspirin from salicylic acid via acetylation
  ✓ Plan generated: Synthesis of Aspirin from Salicylic Acid
  - Materials: 5 items
  - Procedure: 8 steps
  - Safety notes: 3
  - Bullets used: 7
```

**验证点**:
- ✓ `Materials` 应包含 salicylic acid, acetic anhydride, sulfuric acid
- ✓ `Procedure` 应有合理步骤数（通常6-10步）
- ✓ `Safety notes` 应提到酸性催化剂和放热反应
- ✓ `Bullets used` 表示从Playbook检索到的bullets数量

#### Step [7/7]: Reflector
```
[7/7] Running Reflector...
  ✓ Reflection complete: 3 insights extracted
  - Bullet tags: 7
  - Refinement rounds: 5

  Key Insights:
    1. [high] safety_issue: Need more specific catalyst handling instructions...
    2. [medium] best_practice: Recrystallization procedure could be more detailed...
    3. [low] optimization: Consider temperature monitoring...
```

**验证点**:
- ✓ `insights` 数量应在2-5之间（过少说明没发现问题，过多说明噪声）
- ✓ `priority` 分布合理（high < medium < low）
- ✓ `type` 应包括 safety_issue, best_practice, error_pattern 等
- ✓ `Refinement rounds: 5` 表示完成全部迭代

#### Step [8/7]: Curator
```
[8/7] Running Curator...
  ✓ Playbook updated
  - Bullets added: 2
  - Bullets updated: 1
  - Bullets removed: 0
  - Total changes: 3
  - Deduplicated: 0
  - Final playbook size: 21
```

**验证点**:
- ✓ `Total changes` 应与insights数量相关
- ✓ `Deduplicated` 表示有多少重复bullets被合并
- ✓ `Final playbook size` 应逐渐增长（但不能爆炸式增长）

### 多轮测试建议

```bash
# 运行3次，观察Playbook演化
for i in {1..3}; do
    echo "=== Run $i ==="
    python examples/ace_cycle_example.py
    cp data/playbooks/chemistry_playbook.json \
       data/playbooks/chemistry_playbook_run${i}.json
done

# 对比Playbook变化
python -c "
import json

for i in range(1, 4):
    with open(f'data/playbooks/chemistry_playbook_run{i}.json') as f:
        pb = json.load(f)
    print(f'Run {i}: {len(pb[\"bullets\"])} bullets')
"
```

**预期结果**:
```
Run 1: 21 bullets  (+3 from seed 18)
Run 2: 23 bullets  (+2)
Run 3: 24 bullets  (+1, 开始deduplication)
```

### 常见问题

#### 问题1: `Failed to parse generation output`

```
原因: LLM返回的JSON格式不正确

调试步骤:
1. 检查LLM响应:
   python -c "
   from src.ace_framework.generator.generator import PlanGenerator
   # ... 初始化generator
   # 在generator.py的generate()中添加:
   print('LLM response:', response)
   "

2. 检查prompt:
   # 在generator/prompts.py中临时添加:
   with open('debug_prompt.txt', 'w') as f:
       f.write(user_prompt)

3. 调整temperature:
   # configs/ace_config.yaml
   model:
     temperature: 0.3  # 降低随机性
```

#### 问题2: `Refinement round X failed`

```
原因: Reflector迭代过程中LLM输出不稳定

临时解决:
1. 减少refinement轮数:
   # configs/ace_config.yaml
   reflector:
     max_refinement_rounds: 2  # 从5降到2

2. 或跳过迭代:
   reflector:
     enable_iterative: false  # 只做初始reflection
```

#### 问题3: `Playbook增长过快`

```
原因: Deduplication threshold过高，无法合并相似bullets

解决:
# configs/ace_config.yaml
curator:
  deduplication_threshold: 0.80  # 从0.85降到0.80
  max_playbook_size: 50          # 设置更小的上限
```

---

## Level 3: Mock集成测试（当前推荐）

### 目的
测试ACE框架与模拟的MOSES和RAG集成。

### 创建Mock数据

```python
# tests/integration/test_ace_with_mocks.py
import pytest
from src.ace_framework.generator.generator import create_generator
from src.utils.llm_provider import create_llm_provider

# Mock MOSES输出
def mock_moses_output():
    """模拟MOSES提取的requirements"""
    return {
        "target_compound": "Ethyl acetate",
        "objective": "Synthesize ethyl acetate via Fischer esterification",
        "materials": ["ethanol", "acetic acid", "sulfuric acid (catalyst)"],
        "constraints": [
            "Reflux at 60-70°C",
            "Use Dean-Stark apparatus for water removal"
        ]
    }

# Mock RAG输出
def mock_rag_templates():
    """模拟RAG检索的templates"""
    return [
        {
            "title": "Fischer Esterification Template",
            "procedure": [
                "Add alcohol and carboxylic acid to round-bottom flask",
                "Add catalytic amount of sulfuric acid",
                "Attach reflux condenser with Dean-Stark trap",
                # ...
            ]
        }
    ]

# Mock Evaluation输出
def mock_evaluation_feedback():
    """模拟评估反馈"""
    from src.ace_framework.playbook.schemas import Feedback, FeedbackScore

    return Feedback(
        scores=[
            FeedbackScore(criterion="completeness", score=0.85, ...),
            FeedbackScore(criterion="safety", score=0.80, ...),
        ],
        overall_score=0.83,
        feedback_source="auto"
    )

# 集成测试
def test_ace_cycle_with_mocks(tmp_path):
    """完整ACE循环测试（使用mocks）"""

    # 1. 模拟MOSES
    requirements = mock_moses_output()

    # 2. 模拟RAG
    templates = mock_rag_templates()

    # 3. Generator生成
    generator = create_generator(...)
    generation_result = generator.generate(
        requirements=requirements,
        templates=templates
    )

    assert generation_result.generated_plan.title is not None
    assert len(generation_result.generated_plan.materials) > 0

    # 4. 模拟Evaluation
    feedback = mock_evaluation_feedback()

    # 5. Reflector分析
    reflector = create_reflector(...)
    reflection_result = reflector.reflect(
        generated_plan=generation_result.generated_plan,
        feedback=feedback,
        trajectory=generation_result.trajectory,
        playbook_bullets_used=generation_result.relevant_bullets
    )

    assert len(reflection_result.insights) > 0
    assert len(reflection_result.bullet_tags) > 0

    # 6. Curator更新
    curator = create_curator(...)
    update_result = curator.update(
        reflection_result=reflection_result,
        id_prefixes={...}
    )

    assert update_result.total_changes > 0
    assert update_result.updated_playbook.size >= playbook_before.size
```

### 运行Mock集成测试

```bash
# 创建测试文件
mkdir -p tests/integration
# 复制上面的代码到 tests/integration/test_ace_with_mocks.py

# 运行测试
pytest tests/integration/test_ace_with_mocks.py -v

# 带详细输出
pytest tests/integration/test_ace_with_mocks.py -v -s
```

### 优势

✅ **无需实现MOSES** - 用mock替代
✅ **无需实现RAG** - 用mock替代
✅ **无需实现Evaluation** - 用mock替代
✅ **测试ACE核心逻辑** - Generator/Reflector/Curator完整交互
✅ **快速迭代** - 修改mock数据即可测试不同场景

---

## Level 4: 完整集成测试（未来）

### 依赖组件

```
┌─────────────────────────────────────────────┐
│ User Input: "如何合成阿司匹林?"              │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ MOSES Chatbot                               │
│ - Dialogue management                       │
│ - Ontology query (src/external/MOSES)      │
│ - Requirement extraction                    │
└─────────────────┬───────────────────────────┘
                  ↓
         ┌────────────────┐
         │ Requirements   │ (结构化输出)
         └────────┬───────┘
                  ↓
┌─────────────────────────────────────────────┐
│ RAG Template Library                        │
│ - ChromaDB vector search                    │
│ - Template retrieval (top-5)               │
└─────────────────┬───────────────────────────┘
                  ↓
         ┌────────────────┐
         │ Templates      │
         └────────┬───────┘
                  ↓
┌─────────────────────────────────────────────┐
│ ACE Generator                               │
│ + Playbook bullets                          │
│ + Requirements                              │
│ + Templates                                 │
└─────────────────┬───────────────────────────┘
                  ↓
         ┌────────────────┐
         │ Experiment Plan│
         └────────┬───────┘
                  ↓
┌─────────────────────────────────────────────┐
│ Evaluation System                           │
│ - Auto-checks (completeness, safety)       │
│ - LLM-as-judge                             │
│ - (Optional) Human feedback                 │
└─────────────────┬───────────────────────────┘
                  ↓
         ┌────────────────┐
         │ Feedback       │
         └────────┬───────┘
                  ↓
┌─────────────────────────────────────────────┐
│ ACE Reflector + Curator                     │
│ - Analyze plan + feedback                   │
│ - Extract insights                          │
│ - Update playbook                           │
└─────────────────────────────────────────────┘
```

### 实现清单

- [ ] **MOSES集成**
  - [ ] Chatbot wrapper (`src/chatbot/`)
  - [ ] Requirement schema mapping
  - [ ] Error handling

- [ ] **RAG集成**
  - [ ] ChromaDB setup (`src/external/rag/`)
  - [ ] Template indexing
  - [ ] Retrieval API

- [ ] **Evaluation系统**
  - [ ] Auto-check rules (`src/evaluation/auto_checks.py`)
  - [ ] LLM-as-judge (`src/evaluation/llm_judge.py`)
  - [ ] Human feedback interface (optional)

- [ ] **端到端测试**
  - [ ] Integration test suite
  - [ ] Performance benchmarks
  - [ ] Regression tests

### 预计工作量

- MOSES集成: 3-5天
- RAG集成: 2-3天
- Evaluation系统: 3-4天
- 端到端测试: 2-3天
- **总计: 10-15天**

---

## Level 5: 端到端测试（生产环境）

### 真实用户流程

```bash
# 1. 启动系统
python app.py  # 假设有web界面或CLI

# 2. 用户输入
User: "我想合成阿司匹林，但只有家里的基础化学试剂"

# 3. MOSES对话
MOSES: "请问你有以下哪些试剂？"
User: "水杨酸、醋酸酐、浓硫酸"
MOSES: "好的，我会为你设计一个使用这些试剂的方案"

# 4. RAG检索
RAG: 从模板库检索到3个相关方案

# 5. Generator生成
Generator: 结合Playbook + RAG templates → 生成实验方案

# 6. 返回给用户
System: 显示完整实验方案（材料、步骤、安全注意事项）

# 7. 用户反馈
User: "这个方案很好，但我想知道如何判断反应是否完成"

# 8. Evaluation (可选自动 + 人工)
- Auto-check: 方案完整性90%，安全性85%
- User rating: 4/5 stars

# 9. 后台学习 (异步)
Reflector: 分析方案 + 反馈 → 提取insights
Curator: 更新Playbook
- 新增bullet: "在酯化反应中，可用TLC监测反应进度"

# 10. 下次生成时
Generator: 使用更新后的Playbook → 包含TLC监测建议
```

### 测试场景

#### 场景1: 新用户冷启动
```
目标: 测试seed playbook是否足够支撑基础生成
步骤:
1. 清空playbook，只保留18个seed bullets
2. 输入标准化学实验需求
3. 验证生成质量是否可接受（baseline）
```

#### 场景2: 多轮对话
```
目标: 测试MOSES对话能力和需求澄清
步骤:
1. 输入模糊需求: "我想做一个有机合成"
2. MOSES应追问: 目标化合物？起始物？约束条件？
3. 经过3-5轮对话后，提取完整requirements
4. 验证requirements结构化程度
```

#### 场景3: Playbook演化
```
目标: 测试长期学习效果
步骤:
1. 运行100次不同实验生成
2. 每10次保存Playbook快照
3. 对比Playbook演化:
   - Size变化
   - 平均helpfulness_score变化
   - Section分布变化
4. 验证是否收敛（不会无限增长）
```

#### 场景4: 错误处理
```
目标: 测试系统鲁棒性
步骤:
1. 输入无效需求（空、乱码、超长）
2. 模拟LLM API失败
3. 模拟Playbook文件损坏
4. 验证优雅降级和错误恢复
```

---

## 🎯 当前推荐测试策略

基于现有实现，推荐以下测试顺序：

### 第1天: 基础验证
```bash
# ✅ Level 0: 配置验证 (5分钟)
python -c "from src.utils.config_loader import get_ace_config; print(get_ace_config())"

# ✅ Level 1: 单元测试 (10分钟)
pytest tests/test_playbook.py -v
```

### 第2天: ACE组件测试
```bash
# ✅ Level 2: ACE循环 (配置API key)
cp .env.example .env
vim .env  # 添加DASHSCOPE_API_KEY

# 运行1次
python examples/ace_cycle_example.py

# 验证输出
cat data/playbooks/chemistry_playbook.json | jq '.bullets | length'
# 应该从18增加到21左右
```

### 第3天: 多轮演化测试
```bash
# ✅ 运行多次，观察Playbook演化
for i in {1..5}; do
    echo "=== Run $i ==="
    python examples/ace_cycle_example.py | tee logs/run_${i}.log
    cp data/playbooks/chemistry_playbook.json \
       data/playbooks/snapshot_run${i}.json
done

# 分析演化
python scripts/analyze_evolution.py data/playbooks/snapshot_*.json
```

### 第4天: 参数敏感性测试
```bash
# 测试不同配置的影响

# 测试1: 不同deduplication threshold
for threshold in 0.75 0.80 0.85 0.90; do
    # 修改configs/ace_config.yaml
    sed -i "s/deduplication_threshold: .*/deduplication_threshold: $threshold/" \
        configs/ace_config.yaml

    python examples/ace_cycle_example.py
    # 记录最终playbook size
done

# 测试2: 不同refinement rounds
for rounds in 1 3 5; do
    sed -i "s/max_refinement_rounds: .*/max_refinement_rounds: $rounds/" \
        configs/ace_config.yaml

    python examples/ace_cycle_example.py
    # 记录insights质量
done
```

### 第5天: 创建Mock集成测试
```bash
# ✅ Level 3: Mock集成
# 创建tests/integration/test_ace_with_mocks.py
# (参考上面的代码)

pytest tests/integration/test_ace_with_mocks.py -v
```

---

## 📊 测试指标

### Generator指标
- **生成成功率**: 成功解析的方案数 / 总生成次数
- **平均token数**: 衡量成本
- **平均生成时间**: 衡量性能
- **Bullet使用数**: 平均每次检索多少bullets

### Reflector指标
- **Insights数量**: 平均每次提取多少insights
- **Insights质量**: High/Medium/Low优先级分布
- **Bullet tagging准确性**: 与ground truth对比（如果有）
- **Refinement改进幅度**: Round 1 vs Round 5的质量差异

### Curator指标
- **Playbook增长率**: 每次ACE循环增加多少bullets
- **Deduplication效率**: 检测到的重复数 / 总候选数
- **Pruning准确性**: 被删除的bullets是否确实无用
- **Metadata质量**: Helpfulness_score的分布

### 端到端指标
- **用户满意度**: 人工评分（1-5星）
- **方案可执行性**: 化学家能否按照方案操作
- **安全性**: 是否包含必要的安全警告
- **完整性**: 是否包含所有必需部分

---

## 🐛 调试技巧

### 1. 保存所有中间输出

```python
# 在examples/ace_cycle_example.py中添加:
import json
from datetime import datetime

run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# 保存Generator输出
with open(f"logs/runs/{run_id}_generation.json", "w") as f:
    json.dump(generation_result.dict(), f, indent=2)

# 保存Reflector输出
with open(f"logs/runs/{run_id}_reflection.json", "w") as f:
    json.dump(reflection_result.dict(), f, indent=2)

# 保存Curator输出
with open(f"logs/runs/{run_id}_curation.json", "w") as f:
    json.dump(update_result.dict(), f, indent=2)
```

### 2. 对比两次运行的差异

```bash
# 使用jq对比JSON差异
diff <(jq -S . logs/runs/run1_generation.json) \
     <(jq -S . logs/runs/run2_generation.json)
```

### 3. 追踪特定bullet的演化

```python
# scripts/track_bullet.py
import json
import sys

bullet_id = sys.argv[1]  # e.g., "mat-00001"
versions_dir = "data/playbook_versions"

for version_file in sorted(Path(versions_dir).glob("playbook_*.json")):
    with open(version_file) as f:
        playbook = json.load(f)

    bullet = next((b for b in playbook["bullets"] if b["id"] == bullet_id), None)

    if bullet:
        print(f"\n{version_file.name}:")
        print(f"  Helpful: {bullet['metadata']['helpful_count']}")
        print(f"  Harmful: {bullet['metadata']['harmful_count']}")
        print(f"  Helpfulness: {bullet['metadata']['helpfulness_score']:.2f}")
    else:
        print(f"\n{version_file.name}: [REMOVED]")
```

---

## ✅ 测试检查清单

在每次重要更新后，运行以下检查：

- [ ] **Level 0**: 配置文件valid
- [ ] **Level 1**: 单元测试全部通过
- [ ] **Level 2**: ACE循环成功运行
- [ ] **Playbook**: 文件格式正确，可加载
- [ ] **Playbook Size**: 在合理范围内（15-50 bullets）
- [ ] **Deduplication**: 有重复时能正确合并
- [ ] **Pruning**: Size超限时能正确删除低质量bullets
- [ ] **日志**: 无error级别日志（warning可接受）
- [ ] **性能**: Generator < 1分钟，Reflector < 2分钟，Curator < 30秒
- [ ] **成本**: 单次ACE循环token数 < 10K

---

## 📚 延伸阅读

- `OBSERVABILITY_GUIDE.md`: 详细的可观测性和调试指南
- `ARCHITECTURE.md`: 系统架构和数据流
- `CLAUDE.md`: ACE框架核心概念
- Paper §4: ACE论文的实验设置和评估方法

---

*最后更新: 2025-01-23*
