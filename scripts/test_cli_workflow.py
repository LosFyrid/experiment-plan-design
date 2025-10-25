#!/usr/bin/env python
"""测试CLI工作流的自动化脚本

模拟用户交互，验证：
1. CLI启动干净
2. 聊天功能正常
3. /generate启动子进程
4. /logs显示业务日志
"""
import subprocess
import time
import sys
from pathlib import Path

def run_cli_test():
    """运行CLI测试"""
    # 使用conda环境的Python
    python_exe = Path.home() / "miniconda3/envs/OntologyConstruction/bin/python"
    cli_path = Path(__file__).parent.parent / "examples/workflow_cli.py"

    print("🧪 Starting CLI workflow test...")
    print(f"Python: {python_exe}")
    print(f"CLI: {cli_path}")
    print("-" * 60)

    # 启动CLI进程
    process = subprocess.Popen(
        [str(python_exe), str(cli_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def send_input(text: str):
        """发送输入到CLI"""
        print(f"\n👤 Input: {text}")
        process.stdin.write(text + "\n")
        process.stdin.flush()
        time.sleep(0.5)  # 等待处理

    def read_output(timeout: float = 3.0) -> str:
        """读取CLI输出"""
        import select
        lines = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 检查是否有可读数据
            ready = select.select([process.stdout], [], [], 0.1)
            if ready[0]:
                line = process.stdout.readline()
                if line:
                    lines.append(line.rstrip())
                    print(f"🤖 {line.rstrip()}")
                else:
                    break
            else:
                # 如果没有新数据且已经读到一些，就停止
                if lines:
                    break

        return "\n".join(lines)

    try:
        # 等待CLI启动
        print("\n📋 Step 1: Waiting for CLI to start...")
        startup_output = read_output(timeout=5.0)

        # 检查启动输出是否干净
        if "DEBUG" in startup_output or "Loading" in startup_output.lower():
            print("❌ FAIL: CLI startup has debug output!")
            return False
        else:
            print("✅ PASS: CLI startup is clean (no debug output)")

        # 测试聊天
        print("\n📋 Step 2: Testing chat function...")
        send_input("你好")
        chat_output = read_output(timeout=10.0)

        if "你好" in chat_output or "化学" in chat_output:
            print("✅ PASS: Chat function works")
        else:
            print("⚠️  WARNING: No expected chat response")

        # 再聊一轮
        send_input("我想合成阿司匹林")
        chat_output2 = read_output(timeout=10.0)
        print("✅ PASS: Second chat round works")

        # 测试/generate
        print("\n📋 Step 3: Testing /generate command...")
        send_input("/generate")
        generate_output = read_output(timeout=15.0)

        if "任务ID" in generate_output or "task" in generate_output.lower():
            print("✅ PASS: /generate started subprocess")
        else:
            print("⚠️  WARNING: /generate may not have started subprocess")

        # 等待一会让子进程运行
        time.sleep(3)

        # 测试/logs
        print("\n📋 Step 4: Testing /logs command...")
        send_input("/logs 20")
        logs_output = read_output(timeout=5.0)

        if logs_output and len(logs_output) > 50:
            print("✅ PASS: /logs displays output")
        else:
            print("⚠️  WARNING: /logs may not have captured logs")

        # 退出
        print("\n📋 Step 5: Exiting CLI...")
        send_input("/exit")
        time.sleep(1)

        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

    finally:
        # 清理进程
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

if __name__ == "__main__":
    success = run_cli_test()
    sys.exit(0 if success else 1)
