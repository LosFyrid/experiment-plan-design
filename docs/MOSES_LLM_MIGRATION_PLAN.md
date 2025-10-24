# MOSES LLM迁移调研报告：从GPT到Qwen

## 调研日期
2025-10-24

## 目标
将MOSES中的LLM从OpenAI GPT系列迁移到阿里云Qwen系列

---

## 当前状态分析

### 配置文件
**位置**：`src/external/MOSES/config/settings.yaml`

**当前配置**：
```yaml
LLM:
  model: "qwen3-max"  # 已改为qwen模型
  streaming: false
  temperature: 0
  max_tokens: 5000
```

### LLM Provider实现
**位置**：`src/external/MOSES/autology_constructor/idea/common/llm_provider.py`

#### 已有函数：

1. **`get_default_llm()`** (第14-34行)
   - 当前逻辑：只支持OpenAI模型
   - 硬编码检查：`openai_api_key`
   - 返回：`ChatOpenAI` 实例
   - **问题**：即使配置文件设置为qwen模型，仍然尝试创建ChatOpenAI

2. **`get_qwen_llm()`** (第36-50行)
   - 已实现！返回 `ChatTongyi` 实例
   - 硬编码模型：`qwen3-14b`
   - 配置：
     ```python
     ChatTongyi(
         model_name="qwen3-14b",
         model_kwargs={
             "temperature": 0,
             "enable_thinking": False,
             "max_tokens": 8192,
         }
     )
     ```

3. **`get_cached_default_llm(qwen=False)`** (第53-61行)
   - 支持 `qwen=True` 参数切换到Qwen
   - 全局缓存：`DEFAULT_LLM_INSTANCE`
   - **问题**：默认 `qwen=False`，需要手动传参

---

## 代码使用位置分析

### 1. 主要入口（✅ 已支持切换）
**文件**：`autology_constructor/idea/query_team/query_workflow.py`

**第38行**：
```python
default_model = get_cached_default_llm()  # ❌ 没有传qwen=True
```

**用途**：
- 创建所有Agent实例（QueryParserAgent, StrategyPlannerAgent等）
- 这是MOSES查询流程的核心入口

**修改方案**：
```python
# 根据配置自动选择
from config.settings import LLM_CONFIG
is_qwen = 'qwen' in LLM_CONFIG.get('model', '').lower()
default_model = get_cached_default_llm(qwen=is_qwen)
```

### 2. 硬编码位置（❌ 需要修改）

#### 位置A：`llm_helpers.py`
**文件**：`autology_constructor/idea/common/llm_helpers.py`

**第5-7行**：
```python
llm_instance = ChatOpenAI(model="gpt-4o", temperature=0.7)
reasoning_llm_instance = ChatOpenAI(model="o3-mini")
```

**影响**：
- 这两个全局实例可能在其他地方被导入使用
- 需要检查是否有代码使用这些实例

**修改方案**：
- 改用 `get_cached_default_llm(qwen=True)` 替代硬编码
- 或者删除这两个实例（如果没被使用）

#### 位置B：`ontology_tools.py`
**文件**：`autology_constructor/idea/query_team/ontology_tools.py`

**第1378行**（某个类的 `__init__` 方法）：
```python
self.llm = ChatOpenAI(temperature=0)
```

**影响**：
- 每次创建该类实例时硬编码使用OpenAI
- 需要检查这个类是什么，是否被使用

**修改方案**：
```python
from autology_constructor.idea.common.llm_provider import get_cached_default_llm
from config.settings import LLM_CONFIG

is_qwen = 'qwen' in LLM_CONFIG.get('model', '').lower()
self.llm = get_cached_default_llm(qwen=is_qwen)
```

---

## 迁移计划

### 阶段1：最小改动方案（推荐）

#### 目标
让MOSES根据配置文件自动选择Qwen/GPT，无需修改大量代码。

#### 修改内容

**1. 修改 `llm_provider.py` 中的 `get_default_llm()` 函数**

```python
def get_default_llm():
    """根据配置自动选择LLM提供商"""
    model_name = LLM_CONFIG.get('model', 'gpt-4.1-mini')

    # 检测模型类型
    if 'qwen' in model_name.lower():
        # 使用Qwen
        return ChatTongyi(
            model_name=model_name,
            model_kwargs={
                "temperature": LLM_CONFIG.get('temperature', 0),
                "enable_thinking": False,
                "max_tokens": LLM_CONFIG.get('max_tokens', 8192),
            }
        )
    else:
        # 使用OpenAI（保持原逻辑）
        openai_api_key = OPENAI_API_KEY if OPENAI_API_KEY != "default_api_key" else None
        if not openai_api_key:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OpenAI API Key is not configured")

        llm_params = {k: v for k, v in LLM_CONFIG.items() if k not in ['model', 'temperature']}
        return ChatOpenAI(
            model_name=model_name,
            temperature=LLM_CONFIG.get('temperature', 0),
            openai_api_key=openai_api_key,
            **llm_params
        )
```

**2. 修改 `query_workflow.py`**

无需修改！自动使用新的 `get_default_llm()` 逻辑。

**3. 修改 `ontology_tools.py:1378`**

```python
# 修改前
self.llm = ChatOpenAI(temperature=0)

# 修改后
from autology_constructor.idea.common.llm_provider import get_cached_default_llm
self.llm = get_cached_default_llm()
```

**4. 处理 `llm_helpers.py`**

**方案A**（推荐）：如果这两个全局实例未被使用，直接删除或注释

**方案B**：如果被使用，改为：
```python
from autology_constructor.idea.common.llm_provider import get_cached_default_llm

llm_instance = get_cached_default_llm()
# reasoning_llm_instance 需要检查是否还需要
```

---

### 阶段2：环境变量支持（可选）

添加环境变量 `DASHSCOPE_API_KEY`（Qwen使用的key），修改 `settings.py`：

```python
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "default_api_key")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")  # 新增
```

---

## 验证检查清单

修改后需要验证：

- [ ] chatbot能成功初始化MOSES
- [ ] 第一次查询能正常调用Qwen模型
- [ ] 查询结果正确（格式化输出无问题）
- [ ] 配置文件切换回GPT模型时仍能工作
- [ ] 无OpenAI API Key相关错误

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `llm_helpers.py` 的全局实例被其他代码使用 | 中 | 先用grep搜索使用位置 |
| Qwen和GPT返回格式不一致 | 中 | 小规模测试验证 |
| `ontology_tools.py` 中的类被频繁实例化 | 低 | 使用缓存实例 |
| 配置文件model名称大小写不一致 | 低 | 使用 `.lower()` 检测 |

---

## 下一步行动

### 立即执行（调研）
1. ✅ 完成调研报告（本文档）
2. [ ] 搜索 `llm_instance` 和 `reasoning_llm_instance` 的使用位置
3. [ ] 确认 `ontology_tools.py:1378` 所在类的用途

### 待用户确认后执行（实施）
4. [ ] 修改 `llm_provider.py` 的 `get_default_llm()` 函数
5. [ ] 修改 `ontology_tools.py:1378`
6. [ ] 处理 `llm_helpers.py`（删除或修改）
7. [ ] 测试验证

---

## 附录：当前配置状态

### MOSES配置
```yaml
# src/external/MOSES/config/settings.yaml
LLM:
  model: "qwen3-max"  # ✅ 已设置为qwen
  streaming: false
  temperature: 0
  max_tokens: 5000
```

### Chatbot配置
```yaml
# configs/chatbot_config.yaml
chatbot:
  llm:
    model_name: "qwen-plus"  # ✅ 已设置为qwen
```

### ACE配置
```yaml
# configs/ace_config.yaml
model:
  provider: "qwen"
  name: "qwen-max"  # ✅ 已设置为qwen
```

**结论**：配置文件已全部改为Qwen，但MOSES代码实现尚未完全支持自动切换。
