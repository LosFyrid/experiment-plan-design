import os
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_community.chat_models.tongyi import ChatTongyi
# from langchain_anthropic import ChatAnthropic


try:
    from config.settings import LLM_CONFIG, OPENAI_API_KEY
except ImportError as e:
    print(f"Error: Could not import configuration from config.settings: {e}. ")


def get_default_llm():
    """Instantiates and returns the default LLM based on configuration.

    支持两种模式：
    1. Qwen模型：通过OpenAI兼容接口调用（推荐，接口行为稳定）
    2. OpenAI模型：原生调用
    """
    model_name = LLM_CONFIG.get('model', 'gpt-4.1-mini')
    temperature = LLM_CONFIG.get('temperature', 0)

    # 检测是否为Qwen模型
    if 'qwen' in model_name.lower():
        # 使用OpenAI兼容接口调用Qwen
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        if not dashscope_api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY is not configured in environment variables. "
                "Please set it in your .env file."
            )

        # 从配置或环境变量获取base_url（支持自定义）
        base_url = os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 默认中国区
        )

        llm_params = {k: v for k, v in LLM_CONFIG.items()
                      if k not in ['model', 'temperature']}

        return ChatOpenAI(
            model=model_name,  # 注意：这里用model而不是model_name
            temperature=temperature,
            api_key=dashscope_api_key,
            base_url=base_url,
            **llm_params
        )
    else:
        # 原生OpenAI模式
        openai_api_key_to_use = OPENAI_API_KEY if OPENAI_API_KEY and OPENAI_API_KEY != "default_api_key" else None

        if not openai_api_key_to_use:
            # Check env var as a last resort if needed, or raise error
            openai_api_key_to_use = os.getenv("OPENAI_API_KEY")
            if not openai_api_key_to_use:
                 raise ValueError("OpenAI API Key is not configured in environment variables.")

        llm_params = {k: v for k, v in LLM_CONFIG.items() if k not in ['model', 'temperature']}
        return ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=openai_api_key_to_use,
            **llm_params
        )

def get_qwen_llm():
    """使用ChatTongyi调用Qwen（已弃用，推荐使用get_default_llm的OpenAI兼容模式）"""
    # return ChatOllama(
    #         model="myaniu/qwen2.5-1m:14b",
    #         base_url="https://30a6-36-5-153-246.ngrok-free.app",
    #         temperature=0,
    #         max_tokens=8192,
    #     )
    return ChatTongyi(
            model_name="qwen3-14b",
            model_kwargs={
                "temperature": 0,
                "enable_thinking": False,
                "max_tokens": 8192,
            }
        )
# Cached instance logic
DEFAULT_LLM_INSTANCE = None
def get_cached_default_llm(qwen=False):
    """Returns a cached instance of the default LLM."""
    global DEFAULT_LLM_INSTANCE
    if DEFAULT_LLM_INSTANCE is None:
        if qwen:
            DEFAULT_LLM_INSTANCE = get_qwen_llm()
        else:
            DEFAULT_LLM_INSTANCE = get_default_llm()
    return DEFAULT_LLM_INSTANCE 