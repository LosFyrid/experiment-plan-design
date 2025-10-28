# 建议修改文件详细分析

**生成时间**: 2025-10-28
**目标**: 深入分析三个"建议修改"文件的领域特定性及适配必要性

---

## 总览表

| 文件 | 领域特定度 | 不修改的影响 | 修改难度 | 优先级 |
|------|-----------|-------------|---------|-------|
| `chatbot_config.yaml` | 🟡 低 | 用户体验不佳 | 🟢 极低 | P2 |
| `evaluator.py` | 🟠 中 | 评估维度可能不准确 | 🟡 中 | P1 |
| `generator/prompts.py` | 🟠 中高 | 生成结果格式可能不匹配 | 🟡 中 | P1 |

---

## 文件 1: chatbot_config.yaml

### 位置与作用
- **文件路径**: `configs/chatbot_config.yaml`
- **作用范围**: MOSES聊天机器人的系统提示词
- **使用场景**: 用户与系统对话时，机器人的角色定位

### 当前内容分析

**第29-35行 - system_prompt**:
```yaml
system_prompt: |
  你是一个专业的化学实验助手。你可以：
  1. 查询化学本体知识库来回答化学相关问题
  2. 提供实验方案建议
  3. 解释化学概念和原理

  请用专业但易懂的语言回答问题。当需要查询本体知识库时，会自动调用工具。
```

### 领域特定性分析

#### ✅ 通用部分（70%）
```yaml
你是一个专业的[领域]实验助手。你可以：
1. 查询[领域]本体知识库来回答[领域]相关问题  # 框架通用
2. 提供实验方案建议                             # 通用功能
3. 解释[领域]概念和原理                         # 通用功能

请用专业但易懂的语言回答问题。                   # 通用要求
当需要查询本体知识库时，会自动调用工具。          # 技术实现通用
```

#### ⚠️ 领域特定部分（30%）
- **"化学实验助手"** → 明确指向化学领域
- **"化学本体知识库"** → 实际是DSS材料科学本体
- **"化学概念和原理"** → 但用户可能问的是材料科学问题

### 不修改会怎样？

#### 场景1: 系统保持DSS领域，用户使用
```
用户: 如何提高2205 DSS的耐点蚀性能？
机器人: （自我介绍）我是化学实验助手...
用户内心OS: 🤔 我在问材料科学问题，你怎么说你是化学助手？
```

**影响等级**: 🟡 **中等** - 造成认知混乱，但不影响功能

#### 场景2: 系统迁移到有机合成，未修改提示词
```
用户: 如何合成苯甲酸乙酯？
机器人: 我是化学实验助手...
用户: ✅ 没问题，这就是化学问题
```

**影响等级**: 🟢 **无影响** - 有机合成本身就是化学

#### 场景3: 系统迁移到电池材料，未修改提示词
```
用户: NCM811正极材料的合成条件是什么？
机器人: 我是化学实验助手...
用户内心OS: 🤔 这是电化学/材料科学，不是传统化学实验
```

**影响等级**: 🟡 **中等** - 用户可能质疑系统专业性

### 修改建议

#### 方案A: 直接替换（最简单）
```yaml
# 适配到DSS材料科学
system_prompt: |
  你是一个专业的材料科学实验助手，专注于双相不锈钢（DSS）研究。你可以：
  1. 查询材料科学本体知识库来回答DSS相关问题
  2. 提供热处理、腐蚀测试、微观组织分析等实验方案建议
  3. 解释相平衡、腐蚀机理等材料科学概念

  请用专业但易懂的语言回答问题。当需要查询本体知识库时，会自动调用工具。
```

#### 方案B: 配置变量化（推荐）
```yaml
# configs/domain_config.yaml（新建）
domain:
  name: "材料科学"
  subdomain: "双相不锈钢（DSS）"
  capabilities:
    - "查询材料科学本体知识库"
    - "提供热处理、腐蚀测试等实验方案"
    - "解释相平衡、腐蚀机理等概念"

# chatbot_config.yaml（修改为引用）
system_prompt: |
  你是一个专业的{{ domain.name }}实验助手，专注于{{ domain.subdomain }}研究。你可以：
  {% for capability in domain.capabilities %}
  {{ loop.index }}. {{ capability }}
  {% endfor %}

  请用专业但易懂的语言回答问题。当需要查询本体知识库时，会自动调用工具。
```

### 修改难度
- ⏱️ **时间**: 5分钟
- 🔧 **技术难度**: 🟢 极低（纯文本替换）
- 🧪 **测试需求**: 运行聊天机器人验证提示词显示

---

## 文件 2: evaluator.py

### 位置与作用
- **文件路径**: `src/evaluation/evaluator.py`
- **作用范围**: ACE框架中的Feedback系统，为Reflector提供评估结果
- **使用场景**: Generator生成方案后，Evaluator打分，Reflector根据分数改进Playbook

### 当前内容分析

**第264-273行 - LLMJudgeEvaluator系统提示**:
```python
def _get_system_prompt(self) -> str:
    """获取系统prompt"""
    return """你是一位资深的化学实验专家和教育者，负责评估实验方案的质量。

你的任务是从以下几个维度对实验方案进行客观、专业的评分：
- completeness（完整性）：是否包含所有必需部分
- safety（安全性）：安全提示是否充分
- clarity（清晰度）：描述是否清晰易懂
- executability（可执行性）：是否可以实际执行
- cost_effectiveness（成本效益）：材料和时间成本是否合理

请以JSON格式返回评分结果。"""
```

### 领域特定性分析

#### 🔍 评估维度深度分析

| 评估维度 | 当前定义 | 化学实验适用性 | DSS材料科学适用性 | 有机合成适用性 |
|---------|---------|--------------|-----------------|--------------|
| **completeness** | 是否包含所有必需部分 | ✅ 适用 | ⚠️ 需调整（缺少微观组织检测） | ✅ 适用 |
| **safety** | 安全提示是否充分 | ✅ 适用 | ✅ 适用（高温、腐蚀性溶液） | ✅ 适用 |
| **clarity** | 描述是否清晰易懂 | ✅ 适用 | ✅ 适用 | ✅ 适用 |
| **executability** | 是否可以实际执行 | ✅ 适用 | ⚠️ 需细化（设备可得性、时间尺度） | ✅ 适用 |
| **cost_effectiveness** | 材料和时间成本合理 | ✅ 适用 | ⚠️ 需调整（DSS实验动辄数天） | ✅ 适用 |

#### ⚠️ DSS材料科学缺失的评估维度

```python
# 当前缺失，但对DSS很重要的维度：
- phase_balance（相平衡质量）：铁素体/奥氏体比例是否在40-60%范围
- microstructure_characterization（微观组织表征充分性）：是否包含XRD、SEM等必要检测
- corrosion_test_validity（腐蚀测试有效性）：测试方法是否符合标准（ASTM G61等）
- heat_treatment_precision（热处理精度）：温度控制、冷却速率是否明确
- reproducibility（可重复性）：关键参数是否足够详细以供他人复现
```

#### ✅ 有机合成完全适用
当前5个维度对有机合成实验来说是**完全适用**的：
- ✅ completeness - 反应物、溶剂、催化剂齐全
- ✅ safety - 易燃易爆、毒性警告
- ✅ clarity - 步骤清晰、参数明确
- ✅ executability - 实验室条件可实现
- ✅ cost_effectiveness - 试剂成本、反应时间合理

### 不修改会怎样？

#### 场景1: 评估DSS固溶处理方案
```python
# Generator生成的DSS方案：
plan = {
    "title": "DSS 2205固溶处理优化",
    "procedure": [
        "升温至1050°C，保温30分钟",
        "水淬冷却",
        "XRD检测相比例",
        "SEM观察晶粒尺寸"
    ]
}

# Evaluator当前评分：
{
    "completeness": 0.9,  # ✅ 步骤齐全
    "safety": 0.7,        # ⚠️ 未检测到高温安全警告（评估器不懂材料科学特定风险）
    "executability": 0.8, # ⚠️ 未考虑设备（需要高温炉、XRD、SEM）
    "cost_effectiveness": 0.6  # ⚠️ 评估器认为"太耗时"，但实际DSS实验需要这么长
}

# 问题：
- 评估器给了safety 0.7分，但实际上高温操作（1050°C）风险很高，应该0.5分
- executability 0.8分，但未考虑设备可得性（XRD和SEM不是每个实验室都有）
- cost_effectiveness 0.6分偏低，因为评估器用化学实验标准（2-3小时），
  而DSS实验合理时间是3-4小时
```

**影响等级**: 🟠 **中高** - 评分不准确，导致Reflector提取错误的"改进建议"

#### 场景2: 评估有机合成方案（不修改）
```python
# Generator生成的阿司匹林合成方案
plan = {
    "title": "阿司匹林合成",
    "procedure": [
        "水杨酸2.76g + 乙酸酐5mL，加2滴浓硫酸",
        "80°C水浴加热20分钟",
        "冷却至室温，加入冰水析晶"
    ]
}

# Evaluator评分：
{
    "completeness": 0.95,  # ✅ 完整
    "safety": 0.9,         # ✅ 有浓硫酸警告
    "executability": 0.9,  # ✅ 设备简单（烧杯、水浴）
    "cost_effectiveness": 0.95  # ✅ 材料便宜、时间短
}
```

**影响等级**: 🟢 **无影响** - 现有评估维度完全适用

### 修改建议

#### 方案A: 为DSS添加专用评估维度（推荐）

```python
# src/evaluation/evaluator.py

class DSSEvaluator(LLMJudgeEvaluator):
    """DSS材料科学专用评估器"""

    def _get_system_prompt(self) -> str:
        return """你是一位资深的材料科学专家，专注于双相不锈钢（DSS）研究，负责评估实验方案质量。

你的任务是从以下维度对DSS实验方案进行专业评分：

**通用维度**：
- completeness（完整性）：是否包含热处理参数、测试方法、分析手段
- safety（安全性）：高温操作、腐蚀性溶液、设备安全
- clarity（清晰度）：温度、时间、冷却速率等参数是否明确

**DSS特定维度**：
- phase_balance（相平衡控制）：是否明确铁素体/奥氏体目标比例（40-60%）
- microstructure_quality（组织质量）：是否包含XRD物相分析、SEM组织观察
- test_validity（测试规范性）：腐蚀测试是否遵循标准（ASTM G61、G48等）
- heat_treatment_precision（热处理精度）：升温速率、保温时间、冷却方式是否详细
- reproducibility（可重复性）：关键参数是否足够详细供他人复现

请以JSON格式返回评分结果。"""

    def evaluate(self, plan: ExperimentPlan, criteria: List[str]) -> Feedback:
        # 使用DSS特定标准
        if criteria is None:
            criteria = [
                "completeness",
                "safety",
                "clarity",
                "phase_balance",          # DSS特有
                "microstructure_quality",  # DSS特有
                "test_validity",          # DSS特有
                "reproducibility"
            ]
        return super().evaluate(plan, criteria)
```

#### 方案B: 配置驱动的评估维度（灵活性最高）

```yaml
# configs/evaluation_config.yaml（新建）

evaluation:
  # 通用维度（所有领域）
  universal_criteria:
    completeness:
      weight: 1.0
      description: "是否包含所有必需部分"
    safety:
      weight: 1.2  # 权重更高
      description: "安全提示是否充分"
    clarity:
      weight: 1.0
      description: "描述是否清晰易懂"

  # 领域特定维度
  domain_specific:
    dss_materials:
      criteria:
        phase_balance:
          weight: 1.5
          description: "铁素体/奥氏体相比例控制（目标40-60%）"
          check_points:
            - "是否明确固溶温度和保温时间"
            - "是否包含相比例检测方法（XRD）"

        microstructure_quality:
          weight: 1.3
          description: "微观组织表征充分性"
          check_points:
            - "是否包含SEM组织观察"
            - "是否测量晶粒尺寸"

        corrosion_test_validity:
          weight: 1.4
          description: "腐蚀测试规范性"
          check_points:
            - "是否遵循标准（ASTM G61、G48等）"
            - "测试条件是否明确（温度、溶液浓度、时间）"

    organic_synthesis:
      criteria:
        yield_optimization:
          weight: 1.2
          description: "产率优化策略"

        purification_method:
          weight: 1.1
          description: "提纯方法适当性"
```

```python
# src/evaluation/evaluator.py（修改为读取配置）

import yaml

class ConfigurableEvaluator(LLMJudgeEvaluator):
    """配置驱动的评估器"""

    def __init__(self, llm_provider: BaseLLMProvider, domain: str = "dss_materials"):
        super().__init__(llm_provider)
        self.domain = domain
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        with open("configs/evaluation_config.yaml") as f:
            return yaml.safe_load(f)

    def _get_system_prompt(self) -> str:
        domain_config = self.config["evaluation"]["domain_specific"][self.domain]

        # 动态构建评估标准说明
        criteria_desc = []
        for criterion, details in domain_config["criteria"].items():
            criteria_desc.append(f"- {criterion}: {details['description']}")

        prompt = f"""你是一位资深的实验方案评估专家。

评估标准：
{"".join(criteria_desc)}

请以JSON格式返回评分结果。"""
        return prompt
```

### 修改难度
- ⏱️ **时间**:
  - 方案A（添加DSS类）: 1-2小时
  - 方案B（配置化）: 3-4小时
- 🔧 **技术难度**: 🟡 中等（需要理解评估逻辑）
- 🧪 **测试需求**:
  - 生成测试方案
  - 对比修改前后评分差异
  - 验证新维度是否生效

---

## 文件 3: generator/prompts.py

### 位置与作用
- **文件路径**: `src/ace_framework/generator/prompts.py`
- **作用范围**: ACE Generator的核心提示词模板
- **使用场景**: Generator根据Requirements + Playbook + Templates生成实验方案

### 当前内容分析

**第135-211行 - SYSTEM_PROMPT**:
```python
SYSTEM_PROMPT = """You are an expert chemistry experiment planner with extensive knowledge in organic synthesis, materials science, and laboratory best practices.

Your task is to generate detailed, safe, and executable experiment plans based on:
1. **User Requirements**: The specific goals and constraints
2. **Playbook Guidance**: Accumulated best practices and lessons learned
3. **Template References**: Relevant example procedures

You must produce a structured experiment plan that includes:
- Clear objective statement
- Complete materials list with specifications
- Detailed step-by-step procedure
- Safety protocols and warnings
- Quality control checkpoints
- Expected outcomes

**Critical Guidelines**:
- Always prioritize safety - include all relevant warnings
- Be specific with quantities, temperatures, and durations
- Reference playbook bullets that inform your decisions (use bullet IDs like [mat-00001])
- Explain your reasoning for key choices
- Ensure the procedure is executable by a trained chemist

Output your response as a JSON object with the following structure:
{
  "plan": {
    "title": "...",
    "materials": [
      {
        "name": "...",
        "amount": "...",
        "purity": "...",
        "cas_number": "...",      # ⚠️ 化学特定字段
        "hazard_info": "..."       # ⚠️ 化学特定字段
      }
    ],
    ...
  }
}
```

### 领域特定性分析

#### 🔍 提示词层次分解

| 层次 | 内容 | 领域特定度 | 说明 |
|-----|------|----------|------|
| **角色定位** | "expert chemistry experiment planner" | 🟠 中 | 可改为"materials scientist"或"organic chemist" |
| **知识领域** | "organic synthesis, materials science" | 🟡 低 | 已包含材料科学，较泛化 |
| **输入结构** | Requirements + Playbook + Templates | ✅ 通用 | 框架级设计，完全领域无关 |
| **输出字段** | materials.cas_number, hazard_info | 🟠 中高 | 化学特定，DSS需要不同字段 |
| **质量要求** | "executable by trained chemist" | 🟠 中 | 可改为"materials engineer"或"chemist" |

#### ⚠️ 输出格式的领域特定性

**当前JSON Schema（化学导向）**:
```json
{
  "materials": [
    {
      "name": "盐酸",
      "amount": "50 mL",
      "purity": "分析纯",
      "cas_number": "7647-01-0",     // ⚠️ 化学试剂特有
      "hazard_info": "腐蚀性"         // ⚠️ 化学安全标签
    }
  ]
}
```

**DSS材料科学需要的字段**:
```json
{
  "materials": [
    {
      "name": "DSS 2205板材",
      "amount": "100 x 50 x 3 mm",
      "composition": "Fe-22Cr-5Ni-3Mo-0.15N",  // 🆕 成分
      "supplier": "宝钢",                      // 🆕 供应商
      "heat_treatment_state": "固溶态",       // 🆕 热处理状态
      "phase_ratio": "α/γ ≈ 50/50"           // 🆕 相比例
    }
  ],
  "equipment": [                              // 🆕 DSS实验依赖设备
    {
      "name": "高温箱式炉",
      "temperature_range": "室温~1200°C",
      "atmosphere_control": "氩气保护"
    },
    {
      "name": "X射线衍射仪",
      "model": "Bruker D8 Discover"
    }
  ]
}
```

**有机合成适用性**:
```json
{
  "materials": [
    {
      "name": "无水乙醇",
      "amount": "100 mL",
      "purity": "99.9%",
      "cas_number": "64-17-5",        // ✅ 完全适用
      "hazard_info": "易燃"            // ✅ 完全适用
    }
  ]
}
```

### 不修改会怎样？

#### 场景1: 生成DSS实验方案（当前系统）

**用户输入**:
```
需求：研究固溶温度对DSS 2205相比例的影响
```

**Generator当前输出** (受prompts.py限制):
```json
{
  "plan": {
    "title": "DSS 2205固溶处理相比例研究",
    "materials": [
      {
        "name": "DSS 2205板材",
        "amount": "100 x 50 x 3 mm",
        "purity": null,              // ⚠️ 金属材料没有"纯度"概念
        "cas_number": null,          // ⚠️ 合金材料没有CAS号
        "hazard_info": "高温操作注意防烫伤"
      },
      {
        "name": "氩气",
        "amount": "适量",
        "cas_number": "7440-37-1",   // ✅ 保护气体有CAS号
        "hazard_info": "惰性气体"
      }
    ],
    "procedure": [
      // ⚠️ 缺少设备字段，无法明确指定"需要Bruker D8 XRD"
      // ⚠️ 缺少相比例目标字段
    ]
  }
}
```

**问题**:
1. ❌ `cas_number` 对合金材料无意义（LLM会填null或瞎编）
2. ❌ `purity` 字段不适用（合金是多元素体系，用composition更合适）
3. ❌ 缺少 `equipment` 字段（DSS实验严重依赖设备）
4. ❌ 缺少 `phase_ratio` 字段（这是DSS实验的核心评价指标）

**影响等级**: 🟠 **中高** - 生成的JSON结构不完全匹配DSS需求，后续处理需要额外转换

#### 场景2: 迁移到有机合成（不修改）

**用户输入**:
```
需求：合成阿司匹林
```

**Generator输出**:
```json
{
  "plan": {
    "materials": [
      {
        "name": "水杨酸",
        "amount": "2.76 g",
        "purity": "分析纯",
        "cas_number": "69-72-7",     // ✅ 完美适配
        "hazard_info": "刺激性"       // ✅ 完美适配
      }
    ]
  }
}
```

**影响等级**: 🟢 **无影响** - 完全适用

### 修改建议

#### 方案A: 为DSS创建专用提示词（推荐）

```python
# src/ace_framework/generator/prompts.py

DSS_SYSTEM_PROMPT = """You are an expert materials scientist specializing in Duplex Stainless Steel (DSS) research, with deep knowledge in:
- Heat treatment and phase balance control (ferrite/austenite ratio)
- Corrosion testing methodologies (pitting, intergranular, stress corrosion)
- Microstructure characterization (XRD, SEM, EBSD)
- Mechanical property testing (tensile, impact, hardness)

Your task is to generate detailed, executable DSS experiment plans based on:
1. **User Requirements**: Specific research objectives (e.g., optimize phase ratio, improve corrosion resistance)
2. **Playbook Guidance**: Best practices for DSS processing and testing
3. **Template References**: Previous successful DSS experiments

You must produce a structured plan that includes:
- Clear objective statement
- Material specifications (composition, supplier, initial state)
- Equipment requirements (furnaces, XRD, SEM, electrochemical workstation)
- Detailed procedure with precise parameters (temperature, time, cooling rate)
- Characterization methods (phase ratio measurement, corrosion testing)
- Quality control checkpoints (target phase ratio, acceptable corrosion rate)

**Critical Guidelines for DSS**:
- Always specify ferrite/austenite target ratio (typically 40-60%)
- Include cooling rate for heat treatment (critical for phase balance)
- Reference standard test methods (ASTM G61, G48, E112, etc.)
- Specify equipment models when critical (e.g., XRD with specific detector)
- Ensure reproducibility with detailed parameter documentation

Output your response as a JSON object with the following structure:
```json
{
  "plan": {
    "title": "Experiment title",
    "objective": "...",
    "materials": [
      {
        "name": "DSS grade (e.g., 2205, 2507)",
        "amount": "Dimensions with unit",
        "composition": "Chemical composition (e.g., Fe-22Cr-5Ni-3Mo)",
        "supplier": "Manufacturer name",
        "heat_treatment_state": "As-received state",
        "target_phase_ratio": "Ferrite/Austenite target (optional)"
      }
    ],
    "equipment": [
      {
        "name": "Equipment name",
        "model": "Specific model (optional)",
        "specifications": "Key specs (temp range, atmosphere, etc.)"
      }
    ],
    "procedure": [
      {
        "step_number": 1,
        "description": "...",
        "temperature": "Temperature with precision",
        "duration": "Time duration",
        "cooling_rate": "Cooling rate (critical for DSS)",
        "atmosphere": "Protective atmosphere if needed",
        "notes": "Additional notes"
      }
    ],
    "characterization": [
      {
        "method": "XRD, SEM, corrosion test, etc.",
        "purpose": "What to measure",
        "standard": "ASTM or GB/T standard reference",
        "acceptance_criteria": "Target values or ranges"
      }
    ],
    "safety_notes": ["..."],
    "expected_outcome": {
      "phase_ratio": "Expected ferrite/austenite ratio",
      "microstructure": "Expected grain size, morphology",
      "performance": "Expected corrosion resistance, mechanical properties"
    }
  },
  "reasoning": {
    "trajectory": [...],
    "bullets_used": [...]
  }
}
```
"""

# 工厂函数选择提示词
def get_system_prompt(domain: str = "chemistry") -> str:
    """根据领域返回对应的系统提示词"""
    if domain == "dss_materials":
        return DSS_SYSTEM_PROMPT
    elif domain == "organic_synthesis":
        return ORGANIC_SYNTHESIS_SYSTEM_PROMPT  # 可选：进一步细化
    else:
        return SYSTEM_PROMPT  # 默认通用化学提示词
```

#### 方案B: 动态字段模板（最灵活）

```yaml
# configs/generator_schemas.yaml（新建）

schemas:
  dss_materials:
    materials:
      required_fields:
        - name
        - amount
        - composition
      optional_fields:
        - supplier
        - heat_treatment_state
        - target_phase_ratio

    equipment:
      required: true
      fields:
        - name
        - model
        - specifications

    characterization:
      required: true
      fields:
        - method
        - standard
        - acceptance_criteria

  organic_synthesis:
    materials:
      required_fields:
        - name
        - amount
        - purity
      optional_fields:
        - cas_number
        - hazard_info
        - molecular_weight

    equipment:
      required: false
```

```python
# generator/prompts.py（读取配置生成提示词）

import yaml

def build_dynamic_system_prompt(domain: str) -> str:
    with open("configs/generator_schemas.yaml") as f:
        schemas = yaml.safe_load(f)

    schema = schemas["schemas"][domain]

    # 动态构建JSON schema说明
    json_schema = {
        "materials": {
            field: "..." for field in schema["materials"]["required_fields"]
        }
    }

    if schema.get("equipment", {}).get("required"):
        json_schema["equipment"] = [...]

    prompt = f"""You are an expert in {domain} experiments.

Output JSON structure:
{json.dumps(json_schema, indent=2)}
"""
    return prompt
```

### 修改难度
- ⏱️ **时间**:
  - 方案A（添加DSS提示词）: 2-3小时
  - 方案B（动态模板）: 4-6小时
- 🔧 **技术难度**: 🟡 中等（需要设计JSON Schema）
- 🧪 **测试需求**:
  - 生成多个DSS方案
  - 验证JSON字段完整性
  - 检查输出是否符合DSS实验规范

---

## 总结与优先级建议

### 修改成本对比

| 文件 | 方案A时间 | 方案B时间 | 推荐方案 | 原因 |
|------|---------|---------|---------|------|
| chatbot_config.yaml | 5分钟 | 1小时 | 方案A | 简单直接，配置化收益不大 |
| evaluator.py | 2小时 | 4小时 | 方案B | 支持多领域长期价值高 |
| generator/prompts.py | 3小时 | 6小时 | 方案A | DSS字段明确，配置化过度设计 |

### 适配场景决策树

```
是否保留DSS领域？
├─ 是 → 必须修改全部3个文件（更新为DSS专用）
│   ├─ chatbot_config: "材料科学助手"
│   ├─ evaluator: 添加phase_balance等维度
│   └─ generator/prompts: 添加composition, equipment字段
│
└─ 否，迁移到其他领域
    ├─ 目标：有机合成
    │   ├─ chatbot_config: 保持"化学实验助手" ✅
    │   ├─ evaluator: 无需修改 ✅
    │   └─ generator/prompts: 保持cas_number字段 ✅
    │
    ├─ 目标：电池材料
    │   ├─ chatbot_config: 改为"电化学助手" ⚠️
    │   ├─ evaluator: 添加electrochemical_performance维度 ⚠️
    │   └─ generator/prompts: 添加electrode_structure字段 ⚠️
    │
    └─ 目标：药物合成
        ├─ chatbot_config: 改为"药物化学助手" ⚠️
        ├─ evaluator: 添加purity_analysis维度 ⚠️
        └─ generator/prompts: 添加pharmacopoeia_compliance字段 ⚠️
```

### 最终建议

#### 如果系统保持DSS领域 ✅
**必做** (P0):
1. ✅ **generator/prompts.py** → 添加DSS特定字段（2-3小时）
2. ✅ **evaluator.py** → 添加phase_balance等维度（2小时）

**可选** (P1):
3. 🔵 **chatbot_config.yaml** → 更新为"材料科学助手"（5分钟）

#### 如果迁移到有机合成 🎯
**建议修改** (P2):
1. 🔵 **chatbot_config.yaml** → 保持或微调（5分钟）
2. ⚪ **evaluator.py** → 无需修改
3. ⚪ **generator/prompts.py** → 无需修改

#### 如果迁移到电池材料/其他领域 ⚠️
**必须修改** (P0):
- 全部3个文件都需要适配（总计7-10小时）

---

**报告结束**
