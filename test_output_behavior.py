#!/usr/bin/env python3
"""测试当前的输出行为"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path.cwd() / "src"))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("测试输出行为")
print("=" * 70)
print()

# 模拟 workflow_cli.py 的初始化流程
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

print("Step 1: 初始化Chatbot（输出应该重定向到chatbot_init.log）")
chatbot_log = log_dir / "chatbot_init.log"

original_stdout = sys.stdout
original_stderr = sys.stderr

try:
    with open(chatbot_log, 'w', encoding='utf-8') as f:
        sys.stdout = f
        sys.stderr = f

        # 初始化Chatbot（会启动MOSES后台线程）
        from chatbot.chatbot import Chatbot
        bot = Chatbot(config_path="configs/chatbot_config.yaml")

finally:
    sys.stdout = original_stdout
    sys.stderr = original_stderr

print("\nStep 2: 等待MOSES后台线程完成...")
import time
time.sleep(5)  # 等待MOSES初始化完成并打印摘要

print("\nStep 3: 检查日志文件")
print("\n--- chatbot_init.log ---")
if chatbot_log.exists():
    content = chatbot_log.read_text()
    print(f"文件大小: {len(content)} bytes")
    if content:
        print("内容预览:")
        print(content[:500] if len(content) > 500 else content)
    else:
        print("(空文件)")
else:
    print("(文件不存在)")

moses_log = log_dir / "moses_init.log"
print("\n--- moses_init.log ---")
if moses_log.exists():
    content = moses_log.read_text()
    print(f"文件大小: {len(content)} bytes")
    if content:
        print("内容预览:")
        lines = content.splitlines()
        print(f"总共 {len(lines)} 行")
        print("前10行:")
        for line in lines[:10]:
            print(f"  {line}")
    else:
        print("(空文件)")
else:
    print("(文件不存在)")

print("\n" + "=" * 70)
print("预期行为:")
print("  1. chatbot_init.log: 空文件（Chatbot自己没有print输出）")
print("  2. moses_init.log: 包含MOSES初始化的详细输出")
print("  3. 控制台: 应该看到MOSES的统计摘要")
print("=" * 70)
