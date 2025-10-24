"""Chatbot配置加载模块"""
import yaml
from typing import Dict, Any
from pathlib import Path


def load_config(config_path: str = "configs/chatbot_config.yaml") -> Dict[str, Any]:
    """加载chatbot配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: 配置文件格式错误
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 验证必要的配置项
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """验证配置完整性

    Args:
        config: 配置字典

    Raises:
        ValueError: 缺少必要配置项
    """
    required_keys = ["chatbot"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"配置文件缺少必要字段: {key}")

    chatbot_config = config["chatbot"]
    required_chatbot_keys = ["llm", "moses", "memory"]
    for key in required_chatbot_keys:
        if key not in chatbot_config:
            raise ValueError(f"chatbot配置缺少必要字段: {key}")
