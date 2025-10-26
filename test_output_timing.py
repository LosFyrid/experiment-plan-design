#!/usr/bin/env python3
"""测试MOSES后台线程输出时机"""

import sys
import time
import subprocess
from pathlib import Path

# 启动CLI进程，捕获输出
print("启动CLI进程...")
proc = subprocess.Popen(
    [sys.executable, "examples/workflow_cli.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.PIPE,
    text=True,
    bufsize=1,
    cwd=Path.cwd()
)

print("等待10秒，捕获所有输出...")
time.sleep(10)

# 发送空行，触发一个响应
proc.stdin.write("\n")
proc.stdin.flush()

time.sleep(2)

# 终止进程
proc.terminate()
time.sleep(1)

# 读取所有输出
output, _ = proc.communicate()

print("\n" + "="*70)
print("捕获的输出:")
print("="*70)
print(output)
print("="*70)

# 分析输出
lines = output.splitlines()
print(f"\n总共 {len(lines)} 行输出")

# 找出关键行
for i, line in enumerate(lines):
    if "初始化" in line or "MOSES" in line or "完成" in line or "你:" in line:
        print(f"[{i:3d}] {line}")
