# DSS领域适配指南

**生成时间**: 2025-10-28
**目标**: 识别系统中DSS双相不锈钢特定的组件，说明如何适配到其他材料/化学领域

---

## 执行摘要

本系统目前**为DSS（双相不锈钢）材料科学领域定制**，包含DSS特定的：
1. **本体知识库** (MOSES/DSS.owl - 12MB)
2. **实验模板库** (data/mock/dss_templates.json - 8个模板)
3. **RAG文献库** (约10篇DSS腐蚀/微观组织论文)
4. **Playbook种子数据** (包含材料表征、腐蚀测试相关bullets)

如果要适配到**其他领域**（如有机合成、催化、电池材料、生物材料），需要替换以上4类资源。

---

## 一、DSS特定组件清单

### 1. 本体知识库（MOSES）

#### ① DSS.owl - 核心本体文件
**位置**: `src/external/MOSES/data/ontology/DSS.owl`
**大小**: 12 MB
**内容**: DSS材料科学本体

**关键类和属性**（基于OWL头部）:
```xml
<!-- 对象属性 -->
has_primary_phase          # 主相
has_secondary_phase        # 次相
has_ferrite_stabilizer     # 铁素体稳定元素
has_austenite_stabilizer   # 奥氏体稳定元素
has_corrosion_resistance   # 耐腐蚀性
enables_passive_film_formation  # 钝化膜形成
causes_secondary_phase_precipitation  # 二次相析出
causes_embrittlement       # 脆化
```

**领域特定性**: **极高** ⚗️⚗️⚗️
- 双相组织（铁素体/奥氏体）
- 相稳定元素（Cr, Ni, Mo, N）
- 腐蚀机制（点蚀、晶间腐蚀）
- 二次相析出（σ相、χ相）

**适配方法**:
```bash
# 为新领域构建本体
# 示例1: 有机合成领域
cp DSS.owl organic_synthesis.owl
# 修改类和属性为：
# - 反应类型（取代、加成、消除）
# - 官能团（羟基、羰基、氨基）
# - 反应机理（SN1、SN2、E1、E2）

# 示例2: 电池材料领域
cp DSS.owl battery_materials.owl
# 修改为：
# - 正极材料（NCM、LFP）
# - 电解质类型（液态、固态）
# - 电化学性能（容量、循环寿命）
```

---

#### ② chem_ontology.owl - 通用化学本体（与DSS.owl相同）
**位置**: `src/external/MOSES/data/ontology/chem_ontology.owl`
**大小**: 12 MB
**内容**: 与DSS.owl完全相同（可能是符号链接或备份）

**适配操作**: 与DSS.owl同步修改

---

#### ③ MOSES配置（指定本体文件）
**位置**: `src/external/MOSES/config/settings.yaml`

**当前配置** (推测):
```yaml
# 可能包含本体路径配置
ontology:
  default_file: "data/ontology/DSS.owl"
```

**适配方法**:
```yaml
# 修改为新领域本体
ontology:
  default_file: "data/ontology/organic_synthesis.owl"
```

---

### 2. 实验模板库（RAG）

#### ① DSS实验模板文件
**位置**: `data/mock/dss_templates.json`
**模板数量**: 8个
**语言**: 中文

**模板内容清单**:
1. **DSS 2205双相不锈钢固溶处理工艺**
   - 固溶温度: 1050-1080°C
   - 铁素体相体积分数: 40-60%
   - 有害相检查: σ相、χ相

2. **DSS点腐蚀电位测试（ASTM G61）**
   - 6% FeCl3溶液
   - 临界点蚀温度（CPT）测定

3. **DSS显微组织金相分析**
   - 电解腐蚀: 20% NaOH, 3V, 5-10秒
   - 相比例定量分析

4. **DSS热变形实验（Gleeble模拟）**
   - 变形温度: 950-1150°C
   - 应变速率: 0.01-10 s⁻¹

5. **DSS焊接接头力学性能测试**
   - 拉伸、冲击、硬度测试

6. **DSS晶间腐蚀敏感性评价（DL-EPR法）**
   - 双环动电位再活化
   - 再活化率 < 1%为合格

7. **DSS应力腐蚀开裂测试（U型弯试样）**
   - 3.5% NaCl沸腾溶液
   - 测试时长: 720小时

8. **DSS析出相XRD物相分析**
   - Cu Kα射线
   - Rietveld精修定量

**领域特定性**: **极高** ⚗️⚗️⚗️
- 所有模板都是DSS材料的热处理、腐蚀、力学表征

**适配方法**:
```json
// 有机合成领域模板示例
{
  "title": "Williamson醚合成反应",
  "procedure_summary": "醇钠与卤代烃在无水条件下反应生成醚...",
  "key_points": [
    "使用无水溶剂（DMF或THF）",
    "反应温度60-80°C",
    "碱催化（NaH或KOtBu）"
  ],
  "source": "有机化学实验教程",
  "reaction_type": "亲核取代",
  "difficulty": "intermediate"
}
```

**替换文件**:
- 删除 `data/mock/dss_templates.json`
- 创建 `data/mock/organic_synthesis_templates.json`
- 修改代码中的引用路径:
  - `src/workflow/mock_rag.py:14` → 修改默认文件路径
  - `src/workflow/mock_rag.py:149` → 修改默认参数

---

#### ② 对比：阿司匹林模板（泛化学实验）
**位置**: `data/mock/aspirin_templates.json`
**模板数量**: 4个
**领域**: 有机化学合成

**内容**:
1. 阿司匹林合成标准流程（酯化反应）
2. 微量合成方案
3. 工业级制备流程
4. 安全优化方案

**特点**:
- 通用有机化学实验
- 不涉及DSS特定术语
- 可作为迁移到有机合成领域的参考

---

#### ③ RAG配置文件
**位置**: `configs/rag_config.yaml`

**当前配置**:
```yaml
rag:
  vector_store:
    collection_name: "experiment_templates"  # 通用名称

  indexing:
    template_directory: "data/templates"  # 模板目录
    index_metadata:
      - domain  # 领域标签（需在模板中指定）
```

**领域特定性**: **低** 🟢（配置本身是通用的）

**适配方法**: 无需修改（自动加载新模板）

---

### 3. RAG文献库（科研论文）

**位置**: `src/external/rag/data/test_papers/`

**DSS论文清单**（前5篇）:
1. **Busschaert (2013)** - 低温下DSS的挑战
2. **Chail & Kangas (2016)** - 超级和超高强双相不锈钢
3. **Chen et al. (2021)** - 2205 DSS钝化行为与表面化学
4. **Cheng et al. (2018)** - 奥氏体-铁素体相交互对钝化性能的影响
5. **Ha et al. (2014)** - 铁素体比例与点蚀抗性的关系

**总数**: 约10篇DSS相关论文（已索引到ChromaDB）

**领域特定性**: **极高** ⚗️⚗️⚗️
- 全部论文都关于DSS腐蚀、微观组织、力学性能

**适配方法**:
```bash
# 1. 清空现有文献库
rm -rf src/external/rag/data/test_papers/*

# 2. 添加新领域论文
# 示例：有机合成领域
cp ~/papers/organic_synthesis/*.pdf src/external/rag/data/test_papers/

# 3. 重建RAG索引
python src/external/rag/scripts/build_index.py
```

**ChromaDB向量数据库**:
- **位置**: `src/external/rag/data/chroma_db/`
- **大小**: 包含DSS论文的嵌入向量
- **清理方法**: 删除目录后重新索引

---

### 4. Playbook种子数据

**位置**: `data/playbooks/chemistry_playbook.json`

**DSS/材料科学特定Bullets分析**:

虽然文件名为 `chemistry_playbook`，但内容已经包含**大量材料科学/DSS相关**的bullets：

#### 材料表征相关bullets:
- **proc-00007** (第343行):
  ```
  For any analytical or testing methods, provide detailed setup for:
  - potentiodynamic polarization (电化学极化测试 - DSS常用)
  - electrolyte composition (电解质 - 腐蚀测试)
  ```

- **qc-00005** (第371行):
  ```
  Verify phase composition and grain size using:
  - XRD to determine α/γ phase ratio (铁素体/奥氏体相比 - DSS核心指标)
  - SEM to measure grain size
  ```

- **qc-00006** (第399行):
  ```
  Follow test standards: ASTM G1-03
  - 3.5% NaCl solution (海洋环境腐蚀 - DSS典型应用)
  - exposure time: 72 hours
  ```

- **proc-00007** (第385行):
  ```
  Quenching processes with cooling rate (100°C/s)
  - 用于DSS固溶处理后快速冷却
  ```

- **proc-00009** (第455行):
  ```
  Salt spray test: 24 hours, 35°C, 5% NaCl
  - 腐蚀测试（DSS主要性能指标）
  ```

- **proc-00011** (第497行):
  ```
  XRD: Bruker D8 Discover with LynxEye detector
  SEM: Zeiss Merlin with InLens detector
  - 材料表征设备（DSS组织分析）
  ```

- **proc-00012** (第553行):
  ```
  SEM accelerating voltage: 15 kV, magnification: 5000x
  - 微观组织观察参数
  ```

- **proc-00013** (第567行):
  ```
  Grain size measurement following ASTM E112
  - 晶粒尺寸测量（DSS组织评价）
  ```

- **qc-00007** (第539行):
  ```
  Salt fog test → weight loss measurements → corrosion rate
  - 腐蚀速率计算（DSS性能评估）
  ```

#### 通用化学bullets（可保留）:
- **mat-00001**: 溶剂选择（SN1/SN2机理） - 有机化学通用
- **mat-00002**: 试剂纯度验证 - 通用
- **safe-00001**: 格氏试剂操作 - 有机化学
- **safe-00002**: 酸碱稀释规则 - 通用

**DSS特定度**: **约40%的bullets与材料科学/DSS相关**

**适配方法**:
```bash
# 1. 备份现有playbook
cp data/playbooks/chemistry_playbook.json data/playbooks/chemistry_playbook_dss_backup.json

# 2. 选项A: 从头构建新领域playbook
cat > data/playbooks/organic_synthesis_playbook.json <<EOF
{
  "bullets": [
    {
      "id": "mat-00001",
      "section": "material_selection",
      "content": "选择合适的催化剂（Lewis酸、Brønsted酸）...",
      ...
    }
  ],
  "sections": [...],
  "version": "1.0.0"
}
EOF

# 3. 选项B: 清理现有playbook中的DSS相关bullets
# 删除bullets: qc-00005, qc-00006, qc-00007, proc-00007, proc-00009, proc-00011, proc-00012, proc-00013
# 保留通用化学bullets
```

---

## 二、代码中的硬编码引用

### 1. Mock RAG引用DSS模板

**文件**: `src/workflow/mock_rag.py`

**第14行**:
```python
def __init__(self, templates_file: str = "data/mock/dss_templates.json"):
```

**第149行**:
```python
def create_mock_rag_retriever(templates_file: str = "data/mock/dss_templates.json"):
```

**适配操作**:
```python
# 修改为新领域模板
def __init__(self, templates_file: str = "data/mock/organic_synthesis_templates.json"):
```

**或者使用配置文件驱动**:
```python
# 从配置读取
from config import load_config
config = load_config("configs/domain_config.yaml")
templates_file = config["domain"]["templates_file"]
```

---

### 2. MOSES测试代码引用DSS本体

**文件**: `src/external/MOSES/test/question_answering/workflow_test.py`

**第147行**:
```python
ontology_file_name="DSS.owl",  # Use the desired ontology file
```

**适配操作**:
```python
ontology_file_name="organic_synthesis.owl",  # 修改为新本体
```

---

### 3. E2E测试文档引用

**文件**: `docs/E2E_TESTING.md`

**第18行**:
```markdown
- **RAG模板检索** - 使用 `data/mock/dss_templates.json`（8个DSS实验模板）
```

**第407行**:
```bash
ls -l data/mock/dss_templates.json
```

**适配操作**: 更新文档说明

---

## 三、领域无关组件（无需修改）

### ✅ ACE框架核心逻辑
- **Generator**: `src/ace_framework/generator/` - 系统提示词可保持通用
- **Reflector**: `src/ace_framework/reflector/` - 反思机制通用
- **Curator**: `src/ace_framework/curator/` - Delta update逻辑通用

### ✅ 评估系统
- **Evaluator**: `src/evaluation/evaluator.py` - 评估维度可配置

### ✅ 任务调度系统
- **TaskScheduler**: `src/workflow/task_scheduler.py` - 完全通用
- **TaskWorker**: `src/workflow/task_worker.py` - 完全通用

### ✅ MOSES查询管道
- **QueryParser**: 实体提取逻辑通用
- **ToolPlanner**: 工具规划逻辑通用
- **ValidationAgent**: 结果验证逻辑通用

---

## 四、领域适配完整清单

### 必须修改的文件 ⚠️

| 文件 | 当前内容 | 适配操作 | 难度 |
|------|---------|---------|------|
| `src/external/MOSES/data/ontology/DSS.owl` | DSS材料本体 | 构建新领域本体（OWL格式） | 🔴 高 |
| `data/mock/dss_templates.json` | 8个DSS实验模板 | 编写新领域实验模板（JSON） | 🟡 中 |
| `src/external/rag/data/test_papers/` | DSS论文PDF | 添加新领域科研论文 | 🟢 低 |
| `data/playbooks/chemistry_playbook.json` | 40% DSS相关bullets | 清理DSS bullets，添加新领域最佳实践 | 🟡 中 |
| `src/workflow/mock_rag.py:14,149` | 硬编码dss_templates.json | 修改默认文件路径 | 🟢 低 |
| `src/external/MOSES/test/*/workflow_test.py:147` | 硬编码DSS.owl | 修改测试用本体 | 🟢 低 |

### 建议修改的文件 🔵

| 文件 | 当前内容 | 适配操作 | 原因 |
|------|---------|---------|------|
| `configs/chatbot_config.yaml` | "化学实验助手" | 改为"有机合成助手" | 提升用户体验 |
| `src/evaluation/evaluator.py` | 化学实验评估标准 | 调整评估维度 | 领域特定评价 |
| `src/ace_framework/generator/prompts.py` | "chemistry experiment planner" | 改为具体领域 | 增强专业性 |

### 无需修改的文件 ✅

- `src/ace_framework/curator/` - Delta update机制通用
- `src/workflow/task_scheduler.py` - 任务调度通用
- `configs/ace_config.yaml` - 模型配置通用
- `configs/rag_config.yaml` - RAG配置通用

---

## 五、迁移工作量评估

### 场景1: 迁移到有机合成领域

**所需资源**:
1. **本体构建** (3-5天):
   - 定义反应类型（酯化、氧化、还原...）
   - 定义官能团类和属性
   - 建立反应机理关系

2. **模板准备** (2-3天):
   - 编写10-15个经典有机反应模板
   - 包括：Grignard反应、Friedel-Crafts、Diels-Alder等

3. **文献库** (1天):
   - 收集20-30篇有机合成方法论文
   - 重建RAG索引

4. **Playbook清理** (1天):
   - 删除DSS相关bullets（约15个）
   - 添加有机合成最佳实践（溶剂选择、温度控制、后处理）

5. **代码修改** (0.5天):
   - 修改4处硬编码路径

**总工作量**: **7-10天** （1-2人周）

---

### 场景2: 迁移到电池材料领域

**所需资源**:
1. **本体构建** (5-7天):
   - 更复杂的材料体系（正极、负极、电解质、SEI膜）
   - 电化学性能属性（容量、循环寿命、倍率）

2. **模板准备** (3-4天):
   - 电池组装流程
   - 电化学测试（CV、EIS、GCD）
   - 材料表征（XRD、TEM、XPS）

3. **文献库** (1-2天):
   - 电池材料论文30-50篇

4. **Playbook构建** (2-3天):
   - 电池材料合成最佳实践
   - 电化学测试标准流程
   - 安全操作（锂金属、有机电解液）

5. **代码修改** (0.5天)

**总工作量**: **12-17天** （约2-3人周）

---

## 六、领域适配最佳实践

### 1. 本体构建建议

**使用工具**:
- **Protégé** (推荐): 可视化OWL编辑器
- **Owlready2** (Python): 程序化构建本体

**参考DSS.owl结构**:
```python
# 使用Owlready2构建新本体
from owlready2 import *

onto = get_ontology("http://www.example.org/organic_synthesis.owl")

with onto:
    class Reaction(Thing): pass
    class Reagent(Thing): pass
    class Product(Thing): pass

    class has_reagent(ObjectProperty):
        domain = [Reaction]
        range = [Reagent]

    class has_product(ObjectProperty):
        domain = [Reaction]
        range = [Product]

onto.save("organic_synthesis.owl")
```

---

### 2. 模板编写建议

**JSON模板结构**（参考dss_templates.json）:
```json
{
  "title": "实验名称",
  "procedure_summary": "简要概述（1-2句）",
  "key_points": [
    "关键步骤1（具体参数）",
    "关键步骤2（注意事项）",
    "关键步骤3（质量控制）"
  ],
  "source": "参考文献或标准",
  "reaction_type": "领域特定分类",
  "difficulty": "beginner|intermediate|advanced",
  "estimated_time": "预计时间"
}
```

**质量标准**:
- 每个模板至少5个key_points
- 包含具体数值参数（温度、时间、浓度）
- 注明标准方法（如ASTM、GB/T编号）

---

### 3. 渐进式迁移策略

**阶段1: 双系统并存** (推荐用于开发阶段)
```bash
data/
  ontologies/
    DSS.owl              # 保留
    organic_synthesis.owl  # 新增
  mock/
    dss_templates.json   # 保留
    organic_synthesis_templates.json  # 新增
  playbooks/
    chemistry_playbook_dss.json  # 重命名
    chemistry_playbook_organic.json  # 新建
```

**阶段2: 配置驱动切换**
```yaml
# configs/domain_config.yaml
domain:
  active: "organic_synthesis"  # 或 "dss"

  dss:
    ontology: "data/ontologies/DSS.owl"
    templates: "data/mock/dss_templates.json"
    playbook: "data/playbooks/chemistry_playbook_dss.json"

  organic_synthesis:
    ontology: "data/ontologies/organic_synthesis.owl"
    templates: "data/mock/organic_synthesis_templates.json"
    playbook: "data/playbooks/chemistry_playbook_organic.json"
```

**阶段3: 多领域聚合**（未来扩展）
- 支持同时加载多个领域本体
- RAG检索时自动匹配领域标签
- Playbook按领域分section

---

## 七、验证清单

迁移完成后，使用以下清单验证：

### ✅ 本体验证
- [ ] 新本体可在Protégé中无错误打开
- [ ] 包含至少20个类（Class）
- [ ] 包含至少10个对象属性（ObjectProperty）
- [ ] MOSES可成功加载并查询

### ✅ 模板验证
- [ ] 至少10个高质量模板
- [ ] 每个模板包含完整字段（title, procedure_summary, key_points）
- [ ] RAG检索返回相关模板（相似度>0.7）

### ✅ 文献库验证
- [ ] 至少20篇领域相关论文
- [ ] ChromaDB索引构建成功
- [ ] 查询返回相关文献片段

### ✅ Playbook验证
- [ ] 包含30-50个bullets
- [ ] 覆盖6个sections（material_selection, procedure_design等）
- [ ] 无旧领域特定术语残留

### ✅ 功能验证
- [ ] MOSES查询返回领域相关答案
- [ ] Generator生成的方案符合新领域规范
- [ ] E2E工作流完整运行无报错

---

## 八、常见问题

### Q1: 本体构建太复杂，可以跳过吗？
**A**: 不建议。本体是MOSES知识检索的核心，决定了查询结果的质量。如果实在困难，可以：
1. 使用简化本体（只包含核心类和属性）
2. 参考现有领域本体（如ChEBI化学本体）
3. 逐步迭代，初始版本50-100个实体即可

### Q2: 没有足够的科研论文怎么办？
**A**:
- 最小可行数量：10-15篇综述性论文
- 使用教科书章节PDF（扫描版需OCR）
- 从开放获取期刊下载（如PLOS ONE, Scientific Reports）

### Q3: Playbook是否必须手动编写？
**A**:
- 初始种子数据：需要领域专家手动编写（20-30个bullets）
- 后续：通过ACE循环自动进化
- 可从教科书、实验手册中提取关键要点

### Q4: DSS.owl有12MB，新本体也需要这么大吗？
**A**: 不需要。DSS.owl可能包含大量实例数据。新本体初始：
- 轻量版：50-100 KB（类和属性定义）
- 标准版：500 KB - 1 MB（包含少量实例）
- 丰富版：5-10 MB（包含大量材料实例）

---

## 九、总结与建议

### 核心结论

1. **系统架构良好分层**: 60%的代码是领域无关的（ACE框架、任务调度、RAG配置）
2. **DSS特定度**: 主要集中在数据层（本体、模板、文献、Playbook）
3. **迁移成本**: 中等（1-3人周），主要是知识准备而非代码修改

### 优先级建议

**如果时间有限，最小化适配**:
1. **必做**: 替换模板文件（dss_templates.json → new_domain_templates.json）
2. **必做**: 修改代码中的2处硬编码路径
3. **可选**: 构建新本体（或使用通用化学本体）
4. **可选**: 清理Playbook中的DSS bullets

**如果追求完整适配**:
- 按照本文档"迁移工作量评估"部分执行
- 预留10-15个工作日
- 需要1位领域专家 + 1位工程师配合

---

**报告结束**

如有疑问，请参考：
- `CLAUDE.md` - 项目总体架构
- `ARCHITECTURE.md` - 技术架构细节
- `docs/E2E_TESTING.md` - 端到端测试流程
