# Section管理改进实施方案

> 基于用户反馈的最终方案
> 日期: 2025-10-23

## 📋 改进目标

1. ✅ Reflector不知道section（保持职责分离）
2. ✅ Curator明确知道sections列表
3. ✅ 配置开关控制是否允许新sections
4. ✅ 删除validation+mapping hack
5. ✅ 新sections单独管理（独立配置文件）

## 🎯 实施步骤

### Step 1: 创建独立的section配置 ✅ 完成
- 文件: `configs/playbook_sections.yaml`
- 包含: core_sections, custom_sections, settings

### Step 2: 创建SectionManager工具类 ✅ 完成
- 文件: `src/utils/section_manager.py`
- 功能: 加载、查询、添加、审批sections

### Step 3: 修改Curator ⏳ 进行中

#### 3.1 删除的代码

**位置**: `src/ace_framework/curator/curator.py:350-361`

```python
# ❌ 删除以下validation+mapping代码:
if section not in valid_sections:
    section_mapping = {
        "waste_disposal": "safety_protocols",
        "reaction_conditions": "procedure_design",
        ...
    }
    original_section = section
    section = section_mapping.get(section, "safety_protocols")
    print(f"Warning: Invalid section '{original_section}' mapped to '{section}'")
```

**原因**: 这是hack，不应该事后修正LLM的决策。应该让LLM在prompt中就知道valid sections。

#### 3.2 新增的逻辑

```python
# ✅ 使用SectionManager验证和处理
from utils.section_manager import SectionManager

section_manager = SectionManager()

# 在_generate_delta_operations中
for op_data in operations_data:
    bullet_data = op_data.get("new_bullet")
    section = bullet_data["section"]

    # 检查section是否有效
    if not section_manager.is_section_valid(section):
        # Case 1: 允许新sections且是ADD操作
        if section_manager.is_new_section_allowed() and op_data["operation"] == "ADD":
            # 检查是否包含新section提议信息
            new_section_proposal = op_data.get("new_section_proposal")
            if new_section_proposal:
                # 尝试添加新section
                section_manager.add_custom_section(
                    name=section,
                    id_prefix=new_section_proposal['id_prefix'],
                    description=new_section_proposal['description'],
                    creation_reason=new_section_proposal['justification']
                )
                # 重新加载id_prefixes
                id_prefixes = section_manager.get_id_prefixes()
            else:
                # LLM没有提供完整的新section信息，跳过
                print(f"⚠️  Invalid section '{section}' without proposal, skipping operation")
                continue
        else:
            # Case 2: 不允许新sections，跳过这个操作
            print(f"⚠️  Invalid section '{section}', skipping operation (new sections not allowed)")
            continue

    # 继续生成bullet（section已验证）
    if op_data["operation"] == "ADD":
        prefix = id_prefixes[section]  # 现在可以安全获取
        bullet_id = self.playbook_manager._generate_bullet_id(section, prefix)
    ...
```

#### 3.3 更新Curator的__init__

```python
# src/ace_framework/curator/curator.py

from utils.section_manager import SectionManager

class PlaybookCurator:
    def __init__(self, ...):
        ...
        # 初始化SectionManager
        self.section_manager = SectionManager()
```

#### 3.4 更新update()方法

```python
def update(self, reflection_result, id_prefixes=None):
    # 不再需要从config加载id_prefixes
    # 直接从SectionManager获取
    id_prefixes = self.section_manager.get_id_prefixes()

    ...
```

### Step 4: 更新Curator Prompt

#### 4.1 在prompt中包含sections信息

**位置**: Curator的prompt构建函数

```python
# 构建prompt时添加sections信息
sections_info = self.section_manager.format_sections_for_prompt()

prompt = f"""
You are a master curator of knowledge...

{sections_info}

## Your Task
Based on the reflections, create delta operations...
"""
```

**format_sections_for_prompt()输出示例**:

```
## Available Playbook Sections

When creating delta operations, use 'section' field to specify which section the bullet belongs to.

**Valid sections**:

- **material_selection**: 选择实验材料、试剂、溶剂的指导原则
  Examples:
    - 验证试剂纯度和规格
    - 选择合适的溶剂体系
    - 评估材料的稳定性和兼容性

- **procedure_design**: 实验流程设计、操作步骤优化
  Examples:
    - 反应温度和时间控制策略
    - 搅拌速率和反应器选择
    - 加料顺序和速率控制

[... 其他sections ...]

## Proposing New Sections (如果allow_new_sections=true)

You may propose a new section ONLY if ALL of the following conditions are met:
1. Sufficient Evidence: You have identified 5+ insights that clearly don't fit any existing section
2. Semantic Distinction: The new category is semantically distinct (< 70% overlap)
3. Fundamental Domain: Represents a fundamental knowledge domain
4. Clear Definition: Provide description, ID prefix, 3+ examples, strong justification

Think very carefully before proposing a new section. Prefer using existing sections when possible.
```

#### 4.2 更新输出Schema（如果允许新sections）

如果`allow_new_sections=true`，Curator的输出可以包含新section提议：

```json
{
  "operations": [
    {
      "operation": "ADD",
      "new_bullet": {
        "section": "environmental_impact",  // 新section
        "content": "评估实验的环境影响..."
      },
      "new_section_proposal": {  // 新增字段
        "id_prefix": "env",
        "description": "环境影响评估和绿色化学实践",
        "justification": "发现5个以上insights涉及环保和绿色化学，现有sections无法覆盖",
        "examples": [
          "评估溶剂的环境友好性",
          "优化反应降低废物产生",
          "使用可再生原料"
        ]
      },
      "reason": "新类别需求"
    }
  ]
}
```

### Step 5: 更新ace_config.yaml

#### 5.1 删除重复的sections配置

```yaml
# configs/ace_config.yaml

playbook:
  # ❌ 删除sections和id_prefixes配置
  # sections:
  #   - material_selection
  #   ...
  # id_prefixes:
  #   material_selection: "mat"
  #   ...

  # ✅ 保留playbook路径和其他设置
  default_path: "data/playbooks/chemistry_playbook.json"
  max_size: 200

  # ✅ 添加sections配置文件引用
  sections_config: "configs/playbook_sections.yaml"
```

### Step 6: 更新PlaybookManager

**位置**: `src/ace_framework/playbook/playbook_manager.py`

```python
from utils.section_manager import SectionManager

class PlaybookManager:
    def __init__(self, playbook_path: str):
        ...
        # 使用SectionManager而不是从config读取
        self.section_manager = SectionManager()

    def _generate_bullet_id(self, section: str, prefix: str = None) -> str:
        """Generate a new bullet ID for a section."""
        if prefix is None:
            # 从SectionManager获取prefix
            prefix = self.section_manager.get_id_prefixes().get(section, "unk")
        ...
```

### Step 7: 测试计划

#### 7.1 单元测试

```python
# tests/utils/test_section_manager.py

def test_load_sections():
    sm = SectionManager()
    assert len(sm.get_section_names()) == 6  # 初始只有core sections

def test_add_custom_section():
    sm = SectionManager()
    success = sm.add_custom_section(
        name="environmental_impact",
        id_prefix="env",
        description="环境影响评估",
        creation_reason="测试"
    )
    assert success
    assert "environmental_impact" in sm.get_section_names()

def test_prevent_duplicate_section():
    sm = SectionManager()
    sm.add_custom_section("test_section", "tst", "Test", "Test")
    success = sm.add_custom_section("test_section", "tst", "Test", "Test")
    assert not success  # 不能重复添加
```

#### 7.2 集成测试

**测试场景1: allow_new_sections=false**
- 运行ACE
- Curator不应该生成任何新section
- 所有bullets应该使用6个core sections

**测试场景2: allow_new_sections=true**
- 准备特殊的insights（环保主题）
- Curator应该提议新section "environmental_impact"
- 验证新section被添加到playbook_sections.yaml
- 后续运行应该使用这个新section

#### 7.3 回归测试
- 运行之前成功的ACE示例
- 验证输出一致性
- 确保没有引入新bug

## 📊 预期效果

### 改进前（当前）
```
[Curator运行]
⚠️  Warning: Invalid section 'waste_disposal' mapped to 'safety_protocols'
⚠️  Warning: Invalid section 'reaction_conditions' mapped to 'procedure_design'
Added bullet: unk-00001 (因为section映射后prefix可能还是错)
```

### 改进后（目标）

**Scenario A: allow_new_sections=false**
```
[Curator运行]
  ✓ All operations use valid sections (material_selection, procedure_design, ...)
  ✓ No warnings about invalid sections
  ✓ Proper bullet IDs (safe-00019, proc-00005, ...)
```

**Scenario B: allow_new_sections=true**
```
[Curator运行]
  ℹ️  Curator proposed new section: environmental_impact
  ✅ Added new custom section: environmental_impact (env)
  ✓ Added bullet: env-00001
  ✓ Section saved to configs/playbook_sections.yaml
```

## 🔄 向后兼容性

### 配置迁移
- 旧的`ace_config.yaml`中的sections和id_prefixes会被忽略
- 系统会自动从`playbook_sections.yaml`读取
- 现有playbooks不受影响（bullet structure不变）

### 数据迁移
- 现有playbook中的bullets保持不变
- 如果有custom sections在playbooks中使用，需要手动添加到`playbook_sections.yaml`的`custom_sections`

## ⚠️  注意事项

1. **首次运行前检查**:
   - 确保所有现有playbook中使用的sections都在`playbook_sections.yaml`中定义
   - 运行migration script检查兼容性

2. **Git管理**:
   - `playbook_sections.yaml`应该被track
   - Custom sections的添加应该review后commit

3. **多人协作**:
   - 如果多人使用同一playbook，需要同步sections配置
   - 建议使用version control和code review

4. **性能考虑**:
   - SectionManager在每次Curator调用时重新加载配置
   - 如果性能成为问题，可以添加缓存机制

## 📝 下一步行动

1. ✅ 创建`configs/playbook_sections.yaml` - 完成
2. ✅ 创建`src/utils/section_manager.py` - 完成
3. ✅ 修改Curator代码 - 完成
4. ✅ 更新Curator prompt - 完成
5. ✅ 更新ace_config.yaml - 完成
6. ✅ 编写tests - 完成 (15个单元测试全部通过)
7. ✅ 运行测试验证 - 完成
8. ✅ 文档更新 - 完成

---

**状态**: ✅ 完成
**最后更新**: 2025-10-24
**作者**: Claude

## 🎉 实施总结

Section管理改进已全部完成！

### 完成的工作
1. ✅ 创建独立的section配置文件 `configs/playbook_sections.yaml`
2. ✅ 创建SectionManager工具类 `src/utils/section_manager.py`
3. ✅ 修改Curator集成SectionManager
4. ✅ 更新Curator prompt包含sections信息
5. ✅ 更新ace_config.yaml移除重复配置
6. ✅ 编写15个单元测试，全部通过

### 测试结果
- **SectionManager单元测试**: 15/15 通过 ✅
- **测试覆盖**:
  - 配置加载和查询
  - Section验证
  - 动态添加custom sections
  - 防止重复和冲突
  - Prompt格式化
  - 自动审批条件检查

### 核心改进
1. **职责分离**: Reflector不知道sections（专注于insights），Curator明确知道并管理sections
2. **配置解耦**: Sections配置独立于主配置文件，便于管理和版本控制
3. **动态扩展**: 支持运行时添加新sections（通过allow_new_sections开关控制）
4. **删除hack**: 移除了validation+mapping的事后修正逻辑
5. **LLM引导**: 在prompt中明确提供valid sections和新section提议规则

### 注意事项
- 现有playbook tests有预先存在的问题（与section管理无关）:
  - 部分测试用例content长度<10字符（Pydantic验证失败）
  - 缺少dashscope依赖（embedding provider需要）
  - 这些不影响section管理功能的正确性
