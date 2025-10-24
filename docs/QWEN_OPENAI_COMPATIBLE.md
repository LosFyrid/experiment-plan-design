# MOSES使用Qwen通过OpenAI兼容接口

## 概述

本项目使用阿里云DashScope的**OpenAI兼容接口**来调用Qwen模型，而不是使用`ChatTongyi`。

### 为什么选择OpenAI兼容接口？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **ChatOpenAI + OpenAI兼容接口** (✅ 当前) | • 接口行为稳定成熟<br>• 与OpenAI API完全一致<br>• LangChain支持完善<br>• 方便在Qwen/GPT间切换 | 需要配置base_url |
| ChatTongyi | 官方SDK | • 版本较老<br>• 功能行为不完善<br>• 文档较少 |

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中配置：

```bash
# 必需：DashScope API Key
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx

# 可选：Base URL（默认中国区）
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**Base URL选择**：
- **中国区**（默认）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- **国际区**：`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

### 2. 模型配置

在 `src/external/MOSES/config/settings.yaml` 中：

```yaml
LLM:
  model: "qwen3-max"  # 或 qwen-plus, qwen-max, qwen-turbo
  streaming: false
  temperature: 0
  max_tokens: 5000
```

**支持的模型**：
- `qwen-plus` - 通用场景，性价比高（推荐用于MOSES）
- `qwen-max` - 最强性能
- `qwen3-max` - 最新版本
- `qwen-turbo` - 快速响应

## 实现原理

### 代码架构

```
配置文件 (settings.yaml)
    ↓
    model: "qwen3-max"
    ↓
llm_provider.py::get_default_llm()
    ↓
    检测模型名称包含 "qwen"
    ↓
    返回 ChatOpenAI(
        model="qwen3-max",
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    ↓
query_workflow.py::create_query_graph()
    ↓
    所有Agent使用该LLM实例
```

### 关键代码

**位置**: `src/external/MOSES/autology_constructor/idea/common/llm_provider.py`

```python
def get_default_llm():
    model_name = LLM_CONFIG.get('model', 'gpt-4.1-mini')
    temperature = LLM_CONFIG.get('temperature', 0)

    # 自动检测Qwen模型
    if 'qwen' in model_name.lower():
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=dashscope_api_key,
            base_url=base_url,
            **llm_params
        )
    else:
        # 使用原生OpenAI
        return ChatOpenAI(model_name=model_name, ...)
```

## 使用方式

### 自动模式（推荐）

无需修改代码！配置文件中设置 `model: "qwen3-max"` 即可自动使用Qwen。

```yaml
# settings.yaml
LLM:
  model: "qwen3-max"  # 自动检测并使用OpenAI兼容接口
```

### 切换回OpenAI

只需修改模型名称：

```yaml
LLM:
  model: "gpt-4o"  # 自动切换到OpenAI原生接口
```

并确保设置了 `OPENAI_API_KEY`。

## 验证测试

### 测试MOSES查询

```bash
# 启动chatbot
python examples/chatbot_cli.py

# 输入问题测试
你: 什么是水？
```

应该能看到：
```
[MOSES] ✓ 本体查询管理器已就绪
[MOSES]   本体文件: .../chem_ontology.owl
[MOSES]   统计: 338 classes, 250 data properties, 136 object properties
```

### 检查API调用

可以在DashScope控制台查看API调用记录，确认使用的是Qwen模型。

## 常见问题

### Q1: 为什么不直接用ChatTongyi？

**A**: `ChatTongyi` 是较早的实现，功能行为不如OpenAI接口完善。使用OpenAI兼容接口可以：
- 享受成熟的ChatOpenAI接口
- 方便在Qwen/GPT间无缝切换
- 避免潜在的兼容性问题

### Q2: 如何确认正在使用Qwen而不是GPT？

**A**: 有几种方法：
1. **查看初始化日志**：MOSES初始化时会显示使用的模型
2. **检查环境变量**：确保设置了 `DASHSCOPE_API_KEY`
3. **DashScope控制台**：登录查看API调用记录
4. **成本**：Qwen调用费用远低于GPT

### Q3: base_url可以自定义吗？

**A**: 可以！设置环境变量 `QWEN_BASE_URL` 即可：

```bash
# 使用国际区节点
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

### Q4: 支持哪些Qwen模型？

**A**: 所有DashScope支持的Qwen模型，包括：
- 文本模型：qwen-plus, qwen-max, qwen3-max, qwen-turbo
- 代码模型：qwen-coder-plus, qwen-coder-turbo
- 长文本模型：qwen-long

只需在配置文件中修改 `model` 字段即可。

### Q5: 如何调试API调用？

**A**: 启用LangChain的详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

或在环境变量中设置：
```bash
LANGCHAIN_VERBOSE=true
```

## 性能对比

| 指标 | GPT-4 | Qwen3-Max | Qwen-Plus |
|------|-------|-----------|-----------|
| 响应速度 | 中 | 快 | 很快 |
| 成本 | 高 | 中 | 低 |
| 中文能力 | 好 | 优秀 | 很好 |
| 推荐场景 | 复杂推理 | 通用任务 | 高频查询 |

**MOSES推荐配置**：`qwen-plus`（性价比最优）

## 升级日志

### v1.0 (2025-10-24)
- ✅ 实现Qwen通过OpenAI兼容接口调用
- ✅ 自动检测模型类型（qwen/gpt）
- ✅ 支持自定义base_url
- ✅ 向后兼容OpenAI模型

## 参考资料

- [阿里云DashScope OpenAI兼容文档](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
- [Qwen模型列表](https://help.aliyun.com/zh/model-studio/getting-started/models)
- [LangChain ChatOpenAI文档](https://python.langchain.com/docs/integrations/chat/openai)
