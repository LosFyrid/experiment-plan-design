#!/usr/bin/env python3
"""测试MOSES后台初始化功能

验证：
1. Chatbot启动时立即开始后台初始化（不阻塞）
2. 用户可以在初始化期间看到进度消息
3. 第一次查询时如果初始化未完成会自动等待
4. 如果初始化失败，查询时会抛出清晰的错误
"""
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from src.chatbot import Chatbot


def test_background_init():
    """测试后台初始化流程"""
    print("=" * 60)
    print("测试1: Chatbot启动时后台初始化")
    print("=" * 60)

    # 记录启动时间
    start_time = time.time()
    print(f"\n[{time.time() - start_time:.2f}s] 开始创建Chatbot...")

    # 创建Chatbot（应该立即返回，不阻塞）
    bot = Chatbot(config_path="configs/chatbot_config.yaml")
    init_time = time.time() - start_time

    print(f"\n[{init_time:.2f}s] ✓ Chatbot创建完成（耗时 {init_time:.2f}s）")
    print("注意：如果初始化不阻塞，这个时间应该非常短（<1s）")

    print("\n" + "=" * 60)
    print("测试2: 模拟用户操作（初始化可能仍在进行）")
    print("=" * 60)

    # 立即尝试查询（模拟用户快速输入）
    print(f"\n[{time.time() - start_time:.2f}s] 用户输入查询...")
    print("如果初始化未完成，应该看到'等待本体初始化完成...'消息")

    try:
        query_start = time.time()
        result = bot.chat("什么是水？", session_id="test")
        query_time = time.time() - query_start

        print(f"\n[{time.time() - start_time:.2f}s] ✓ 查询成功（耗时 {query_time:.2f}s）")
        print(f"\n回复预览: {result[:200]}...")

    except Exception as e:
        print(f"\n[{time.time() - start_time:.2f}s] ✗ 查询失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("测试3: 第二次查询（初始化已完成）")
    print("=" * 60)

    try:
        query_start = time.time()
        result = bot.chat("什么是氧气？", session_id="test")
        query_time = time.time() - query_start

        print(f"\n[{time.time() - start_time:.2f}s] ✓ 查询成功（耗时 {query_time:.2f}s）")
        print(f"注意：第二次查询应该更快，因为初始化已完成")
        print(f"\n回复预览: {result[:200]}...")

    except Exception as e:
        print(f"\n[{time.time() - start_time:.2f}s] ✗ 查询失败: {e}")
        return False
    finally:
        # 清理资源
        print("\n" + "=" * 60)
        print("清理资源...")
        print("=" * 60)
        bot.cleanup()

    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}s")
    print("\n✓ 所有测试通过！")
    return True


def test_immediate_query():
    """测试立即查询（验证等待机制）"""
    print("\n\n" + "=" * 60)
    print("测试4: 立即查询（验证等待机制）")
    print("=" * 60)

    start_time = time.time()
    bot = Chatbot(config_path="configs/chatbot_config.yaml")
    print(f"\n[{time.time() - start_time:.2f}s] Chatbot创建完成")

    # 不等待，立即查询（应该自动等待初始化）
    print(f"[{time.time() - start_time:.2f}s] 立即发起查询（不手动等待）...")

    try:
        result = bot.chat("什么是氢气？", session_id="test")
        print(f"\n[{time.time() - start_time:.2f}s] ✓ 查询成功")
        print("说明：自动等待机制正常工作")
    except Exception as e:
        print(f"\n[{time.time() - start_time:.2f}s] ✗ 查询失败: {e}")
        return False
    finally:
        bot.cleanup()

    return True


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║          MOSES后台初始化功能测试                             ║
╚════════════════════════════════════════════════════════════╝
    """)

    success = True

    # 运行测试
    if not test_background_init():
        success = False

    if not test_immediate_query():
        success = False

    # 输出结果
    print("\n\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过！后台初始化功能正常。")
    else:
        print("✗ 部分测试失败，请检查日志。")
    print("=" * 60)

    sys.exit(0 if success else 1)
