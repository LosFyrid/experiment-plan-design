# Section管理架构改进方案

## 当前问题分析

### 问题1：Section信息传递不完整

**现状**：
- ❌ **Reflector不知道valid sections**
  - prompt中没有包含sections列表
  - 导致LLM"盲目"建议target_section（如 "waste_disposal", "reaction_conditions"）
  - 依赖Curator事后修复，效率低且浪费token

- ✅ **Curator知道sections**
  - 从config加载id_prefixes间接知道
  - 但只能被动修复，不能主动预防

- ⚠️ **Generator部分知道**
  - 可以按section检索，但不验证

**影响**：
1. Reflector生成无效section → Curator映射修复 → 效率低
2. LLM token浪费
3. 用户看到Warning但问题本应上游预防

### 问题2：缺乏动态扩展section的机制

**现状**：
- ❌ **Sections列表固定在配置文件中**
  - 6个预设section（material_selection, procedure_design, ...）
  - 无法根据实际需求动态添加

- ❌ **LLM发现新类别时无权限建议**
  - 当前方案：硬编码映射（waste_disposal → safety_protocols）
  - 不够灵活，可能损失有价值的知识分类

**影响**：
1. Playbook结构僵化，无法适应新知识类型
2. 强制映射可能导致语义不匹配
3. 限制了ACE的自适应能力

---

## 改进方案

### 方案1：让Reflector知道Valid Sections（立即实施）

#### 1.1 修改Reflector Prompt

**位置**：`src/ace_framework/reflector/prompts.py`

**修改点1**：添加sections参数到prompt构建函数

```python
def build_initial_reflection_prompt(
    plan: ExperimentPlan,
    feedback: Feedback,
    trajectory: List[TrajectoryStep],
    bullets_used: List[str],
    bullet_contents: Dict[str, str],
    valid_sections: List[str]  # ✅ 新增参数
) -> str:
```

**修改点2**：在prompt中包含sections信息

```python
# 在prompt中添加section说明
sections.append("\n## Available Playbook Sections")
sections.append("When suggesting target_section for insights, choose from:")
for section in valid_sections:
    # 可以添加section的描述
    sections.append(f"- **{section}**: [用途描述]")

sections.append("\n**Important**: Only use sections from the list above.")
sections.append("If you believe a new section category is needed, ")
sections.append("use the closest existing section and explain in 'description'.")
```

**修改点3**：更新Reflector类调用

```python
# src/ace_framework/reflector/reflector.py
def reflect(self, ...):
    # 获取valid sections
    valid_sections = list(self.config.playbook.sections)

    # 构建prompt时传入
    prompt = build_initial_reflection_prompt(
        plan=generation_result.plan,
        feedback=feedback,
        trajectory=generation_result.trajectory,
        bullets_used=generation_result.bullets_used,
        bullet_contents=bullet_contents,
        valid_sections=valid_sections  # ✅ 传入sections
    )
```

#### 1.2 预期效果

- ✅ Reflector知道哪些section有效
- ✅ 减少无效section建议
- ✅ 降低Curator修复负担
- ✅ 节省LLM token

---

### 方案2：支持动态Section提议（中期实施）

#### 2.1 设计原则

1. **谨慎但允许**：LLM可以提议新section，但需要充分理由
2. **审批机制**：新section需经过验证才能加入配置
3. **向后兼容**：保持现有6个section稳定

#### 2.2 Schema扩展

**新增NewSectionProposal schema**：

```python
# src/ace_framework/playbook/schemas.py

class NewSectionProposal(BaseModel):
    """LLM提议的新section。"""

    proposed_name: str = Field(..., description="建议的section名称")
    justification: str = Field(..., description="为什么需要这个新section")
    example_bullets: List[str] = Field(..., description="属于该section的示例bullets")
    closest_existing: Optional[str] = Field(None, description="最接近的现有section")

    # 审批状态
    status: Literal["pending", "approved", "rejected"] = "pending"
    review_notes: Optional[str] = None
```

**扩展Insight schema**：

```python
class Insight(BaseModel):
    # ... 现有字段 ...

    # ✅ 新增：如果target_section不在valid list，可以提议新section
    new_section_proposal: Optional[NewSectionProposal] = None
```

#### 2.3 Reflector Prompt修改

```python
# 在prompt中添加新section提议指南

"""
## Proposing New Sections (Advanced)

If you believe the existing sections cannot adequately categorize an insight:

1. Choose the **closest existing section** as target_section
2. Provide a **new_section_proposal** with:
   - Proposed name (snake_case)
   - Strong justification (why existing sections are insufficient)
   - 3+ example bullets that would belong to this section

Example:
{
  "type": "new_category",
  "target_section": "safety_protocols",  // Closest existing
  "new_section_proposal": {
    "proposed_name": "environmental_impact",
    "justification": "Many insights relate to environmental concerns...",
    "example_bullets": ["...", "...", "..."]
  }
}

**Criteria for new sections**:
- Must represent a distinct knowledge category
- Should have 5+ potential bullets
- Cannot overlap significantly with existing sections
"""
```

#### 2.4 Curator处理逻辑

**修改Curator的section验证逻辑**：

```python
# src/ace_framework/curator/curator.py

def _validate_and_handle_section(
    self,
    insight: Insight,
    valid_sections: Set[str]
) -> Tuple[str, Optional[NewSectionProposal]]:
    """
    验证section，处理新section提议。

    Returns:
        (final_section, new_section_proposal)
    """
    target = insight.target_section

    # Case 1: Valid section
    if target in valid_sections:
        return target, None

    # Case 2: Has new section proposal
    if insight.new_section_proposal:
        proposal = insight.new_section_proposal

        # Log proposal for human review
        self.logger.log_new_section_proposal(
            proposed_name=proposal.proposed_name,
            justification=proposal.justification,
            fallback_section=proposal.closest_existing or target
        )

        # For now, use closest existing section
        # Future: Auto-approve if criteria met
        return proposal.closest_existing or target, proposal

    # Case 3: Invalid section without proposal (fallback to mapping)
    mapped_section = self._map_invalid_section(target)
    self.logger.warning(f"Invalid section '{target}' mapped to '{mapped_section}'")
    return mapped_section, None
```

#### 2.5 审批流程

**自动审批条件**（可选，高级功能）：

```python
def _auto_approve_section_proposal(
    self,
    proposal: NewSectionProposal
) -> bool:
    """
    自动审批新section提议的条件。
    """
    # 检查是否已有足够的pending bullets支持这个section
    pending_bullets = self._count_bullets_for_proposed_section(proposal)

    if pending_bullets >= 5:  # 阈值：至少5个bullets
        # 检查与现有sections的语义重叠
        overlap = self._check_semantic_overlap(proposal, self.valid_sections)

        if overlap < 0.7:  # 相似度阈值
            return True

    return False
```

**人工审批**（配置驱动）：

```yaml
# configs/ace_config.yaml

curator:
  # ... 现有配置 ...

  # 新section管理
  allow_new_sections: true  # 是否允许提议新section
  auto_approve_sections: false  # 是否自动审批（谨慎）
  min_bullets_for_new_section: 5  # 新section最少需要几个bullets
  section_overlap_threshold: 0.7  # 与现有section的最大重叠度
```

#### 2.6 Section审批工具

**创建管理工具**：`scripts/manage_sections.py`

```python
#!/usr/bin/env python3
"""
Section管理工具：审批、添加、删除sections
"""

def list_pending_proposals():
    """列出所有待审批的section提议"""
    pass

def approve_section(proposal_id: str):
    """审批新section，添加到配置"""
    # 1. 更新 configs/ace_config.yaml
    # 2. 重新分类相关bullets
    # 3. 记录审批历史
    pass

def reject_section(proposal_id: str, reason: str):
    """拒绝section提议"""
    pass
```

---

## 实施计划

### Phase 1：立即实施（解决问题1）

✅ **优先级：HIGH**

1. [ ] 修改Reflector prompt，添加valid_sections参数
2. [ ] 更新Reflector类，传递sections信息
3. [ ] 同时更新build_refinement_prompt
4. [ ] 测试Reflector生成的insights是否使用valid sections
5. [ ] 验证Curator的Warning减少

**预计工作量**：2-3小时
**影响范围**：小（仅Reflector模块）

### Phase 2：中期实施（解决问题2）

⚠️ **优先级：MEDIUM**

1. [ ] 设计NewSectionProposal schema
2. [ ] 扩展Insight schema支持new_section_proposal
3. [ ] 修改Reflector prompt添加新section提议指南
4. [ ] 更新Curator处理逻辑
5. [ ] 实现section审批工具
6. [ ] 添加配置项控制功能开关

**预计工作量**：1-2天
**影响范围**：中（涉及schema、Reflector、Curator）

### Phase 3：高级功能（可选）

📚 **优先级：LOW**

1. [ ] 实现自动审批逻辑
2. [ ] Section语义重叠检测
3. [ ] Section使用统计分析
4. [ ] Section合并建议

**预计工作量**：2-3天
**影响范围**：大（需要embedding分析、统计系统）

---

## 配置示例

### 更新后的ace_config.yaml

```yaml
playbook:
  # 现有sections
  sections:
    - material_selection
    - procedure_design
    - safety_protocols
    - quality_control
    - troubleshooting
    - common_mistakes

  # Section描述（用于Reflector prompt）
  section_descriptions:
    material_selection: "选择实验材料、试剂、溶剂的指导原则"
    procedure_design: "实验流程设计、操作步骤优化"
    safety_protocols: "安全操作规范、应急处理措施"
    quality_control: "质量检测方法、标准和验收准则"
    troubleshooting: "常见问题诊断和解决方案"
    common_mistakes: "需要避免的错误和注意事项"

  # ID前缀（现有）
  id_prefixes:
    material_selection: "mat"
    procedure_design: "proc"
    safety_protocols: "safe"
    quality_control: "qc"
    troubleshooting: "ts"
    common_mistakes: "err"

  # 新section管理（Phase 2）
  dynamic_sections:
    enabled: false  # 初始关闭，Phase 1完成后开启
    auto_approve: false
    min_bullets_threshold: 5
    overlap_threshold: 0.7

    # 已审批的自定义sections（动态更新）
    custom_sections: []
    # 示例：
    # - name: environmental_impact
    #   prefix: env
    #   description: 环境影响评估和绿色化学实践
    #   approved_at: 2025-10-24
    #   approved_by: human
```

---

## 向后兼容性

### 兼容性保证

1. **配置兼容**：
   - 新增字段都有默认值
   - dynamic_sections默认disabled
   - 不影响现有playbooks

2. **数据兼容**：
   - 现有bullets的section不受影响
   - NewSectionProposal是Optional字段

3. **行为兼容**：
   - Phase 1只是增强Reflector的输入
   - Curator的映射逻辑保留（向后兼容）

---

## 测试策略

### Unit Tests

```python
# tests/ace_framework/test_reflector_sections.py

def test_reflector_receives_valid_sections():
    """测试Reflector prompt包含valid sections"""
    prompt = build_initial_reflection_prompt(
        ...,
        valid_sections=["material_selection", "safety_protocols"]
    )
    assert "Available Playbook Sections" in prompt
    assert "material_selection" in prompt

def test_reflector_suggests_valid_section():
    """测试Reflector建议valid section"""
    # Mock LLM返回
    # 验证target_section在valid_sections中
    pass

# tests/ace_framework/test_curator_new_sections.py

def test_curator_handles_section_proposal():
    """测试Curator处理新section提议"""
    insight = Insight(
        target_section="waste_disposal",
        new_section_proposal=NewSectionProposal(
            proposed_name="waste_disposal",
            justification="...",
            example_bullets=[...]
        )
    )

    section, proposal = curator._validate_and_handle_section(
        insight, valid_sections
    )

    assert section in valid_sections  # 使用fallback
    assert proposal is not None  # 提议被记录
```

### Integration Tests

```python
# tests/integration/test_section_workflow.py

def test_full_section_proposal_workflow():
    """测试完整的section提议工作流"""
    # 1. Generator生成计划
    # 2. Reflector提议新section
    # 3. Curator记录提议并使用fallback
    # 4. 验证日志中有new_section_proposal
    pass
```

---

## 风险评估

### 风险1：LLM滥用新section提议

**风险**：LLM频繁提议无意义的新sections

**缓解措施**：
- Prompt中强调"谨慎使用"
- 要求充分的justification
- 设置审批阈值
- 人工审批（初期）

### 风险2：Section碎片化

**风险**：sections过多导致playbook难以管理

**缓解措施**：
- 设置最小bullets数阈值（5+）
- 定期review和合并相似sections
- Section使用统计和分析

### 风险3：破坏现有工作流

**风险**：改动影响现有功能

**缓解措施**：
- 分阶段实施（Phase 1先）
- 完整的测试覆盖
- 配置开关控制新功能
- 向后兼容保证

---

## 总结

### 核心改进

1. **问题1解决**：Reflector prompt包含valid sections ✅
   - 预防无效section建议
   - 提高效率，节省token

2. **问题2解决**：支持动态section提议 ⚠️
   - 保持灵活性
   - 谨慎的审批机制
   - 不破坏现有结构

### 建议实施顺序

1. **立即**：实施Phase 1（Reflector知道sections）
2. **观察**：运行几次ACE，验证效果
3. **评估**：是否确实需要Phase 2（动态sections）
4. **谨慎**：如需Phase 2，先在测试环境验证

### 开放问题

1. 是否真的需要动态sections？还是6个固定section已经足够？
2. 如果需要，自动审批的阈值如何设定？
3. Section审批应该完全人工，还是半自动？

---

**作者**: Claude
**日期**: 2025-10-23
**版本**: v1.0
**状态**: 设计中，待讨论
