#!/usr/bin/env python3
"""测试重试机制

测试场景：
1. 基础重试检查
2. 文件验证
3. 部分重试策略
4. 完全重试策略
5. 重试次数限制
6. 不可重试的错误
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from workflow.task_manager import GenerationTask, TaskStatus, get_task_manager
from workflow.retry_handler import RetryHandler


def test_basic_retry_check():
    """测试1: 基础重试检查"""
    print("=" * 70)
    print("测试1: 基础重试检查")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        # 创建失败的任务
        task = GenerationTask(
            task_id="test-retry-001",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="生成失败: 测试错误",
            failed_stage="generating"
        )

        print(f"\n📋 任务信息:")
        print(f"  - 状态: {task.status.value}")
        print(f"  - 失败阶段: {task.failed_stage}")
        print(f"  - 重试次数: {task.retry_count}/{task.max_retries}")

        # 检查是否可重试
        can_retry, reason = handler.can_retry(task)
        print(f"\n✅ 可重试检查: {can_retry}")
        print(f"   原因: {reason}")

        assert can_retry, "失败任务应该可以重试"

        # 测试非FAILED状态
        task.status = TaskStatus.COMPLETED
        can_retry, reason = handler.can_retry(task)
        print(f"\n✅ COMPLETED状态检查: {can_retry}")
        print(f"   原因: {reason}")

        assert not can_retry, "COMPLETED任务不应该可以重试"

        print(f"\n{'=' * 70}")
        print("✅ 测试1通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_retry_count_limit():
    """测试2: 重试次数限制"""
    print("\n" + "=" * 70)
    print("测试2: 重试次数限制")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        task = GenerationTask(
            task_id="test-retry-002",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="生成失败: 测试错误",
            failed_stage="generating",
            retry_count=3,  # 已经重试3次
            max_retries=3
        )

        print(f"\n📋 任务信息:")
        print(f"  - 重试次数: {task.retry_count}/{task.max_retries}")

        # 不使用force
        can_retry, reason = handler.can_retry(task, force=False)
        print(f"\n❌ 正常重试检查: {can_retry}")
        print(f"   原因: {reason}")
        assert not can_retry, "超过重试次数应该不可重试"

        # 使用force
        can_retry, reason = handler.can_retry(task, force=True)
        print(f"\n✅ 强制重试检查: {can_retry}")
        print(f"   原因: {reason}")
        assert can_retry, "force模式应该忽略重试次数"

        print(f"\n{'=' * 70}")
        print("✅ 测试2通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_non_retryable_errors():
    """测试3: 不可重试的错误"""
    print("\n" + "=" * 70)
    print("测试3: 不可重试的错误")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        # 配置文件不存在
        task = GenerationTask(
            task_id="test-retry-003",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="配置文件不存在: config.yaml",
            failed_stage="generating"
        )

        print(f"\n📋 错误信息: {task.error}")

        can_retry, reason = handler.can_retry(task)
        print(f"❌ 可重试检查: {can_retry}")
        print(f"   原因: {reason}")

        assert not can_retry, "配置错误不应该可以重试"

        # force模式应该仍然可以重试
        can_retry, reason = handler.can_retry(task, force=True)
        print(f"\n✅ 强制重试: {can_retry}")
        assert can_retry

        print(f"\n{'=' * 70}")
        print("✅ 测试3通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_partial_retry_strategy():
    """测试4: 部分重试策略"""
    print("\n" + "=" * 70)
    print("测试4: 部分重试策略")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        # 在generating阶段失败
        task = GenerationTask(
            task_id="test-retry-004",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="生成失败: 测试错误",
            failed_stage="generating"
        )

        # 创建一些中间文件
        (temp_dir / "config.json").write_text("{}")
        (temp_dir / "task.json").write_text("{}")
        (temp_dir / "requirements.json").write_text('{"objective": "test"}')
        (temp_dir / "templates.json").write_text("[]")

        print(f"\n📋 失败阶段: {task.failed_stage}")

        prep_info = handler.prepare_retry(task, clean=False)

        print(f"\n📋 重试策略: {prep_info['strategy']}")
        print(f"  - 恢复到阶段: {prep_info['resume_from_stage']}")
        print(f"  - 恢复到状态: {prep_info['resume_from_status'].value}")
        print(f"  - 保留文件: {', '.join(prep_info['files_to_keep'])}")
        print(f"  - 删除文件: {', '.join(prep_info['files_to_remove'])}")

        assert prep_info['strategy'] == 'partial'
        assert prep_info['resume_from_status'] == TaskStatus.RETRIEVING
        assert 'requirements.json' in prep_info['files_to_keep']
        assert 'templates.json' in prep_info['files_to_keep']

        print(f"\n{'=' * 70}")
        print("✅ 测试4通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_clean_retry_strategy():
    """测试5: 完全重试策略"""
    print("\n" + "=" * 70)
    print("测试5: 完全重试策略")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        task = GenerationTask(
            task_id="test-retry-005",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="生成失败: 测试错误",
            failed_stage="generating"
        )

        print(f"\n📋 失败阶段: {task.failed_stage}")

        prep_info = handler.prepare_retry(task, clean=True)

        print(f"\n📋 重试策略: {prep_info['strategy']}")
        print(f"  - 恢复到阶段: {prep_info['resume_from_stage']}")
        print(f"  - 恢复到状态: {prep_info['resume_from_status'].value}")
        print(f"  - 保留文件: {', '.join(prep_info['files_to_keep'])}")
        print(f"  - 删除文件数量: {len(prep_info['files_to_remove'])}")

        assert prep_info['strategy'] == 'clean'
        assert prep_info['resume_from_status'] == TaskStatus.PENDING
        assert 'config.json' in prep_info['files_to_keep']
        assert 'task.json' in prep_info['files_to_keep']
        assert 'requirements.json' in prep_info['files_to_remove']

        print(f"\n{'=' * 70}")
        print("✅ 测试5通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_validation():
    """测试6: 文件完整性验证"""
    print("\n" + "=" * 70)
    print("测试6: 文件完整性验证")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp())
    handler = RetryHandler()

    try:
        task = GenerationTask(
            task_id="test-retry-006",
            session_id="test-session",
            status=TaskStatus.FAILED,
            task_dir=temp_dir,
            error="生成失败: 测试错误",
            failed_stage="generating"
        )

        # 创建有效的文件
        (temp_dir / "requirements.json").write_text('{"objective": "test obj"}')
        (temp_dir / "templates.json").write_text('[{"title": "Template 1"}]')

        # 创建损坏的文件（无效JSON）
        (temp_dir / "plan.json").write_text("invalid json{{{")

        files_to_check = ["requirements.json", "templates.json", "plan.json"]

        print(f"\n🔍 验证文件: {', '.join(files_to_check)}")

        corrupted = handler.validate_files(task, files_to_check)

        print(f"\n📋 验证结果:")
        print(f"  - 有效文件: requirements.json, templates.json")
        print(f"  - 损坏文件: {', '.join(corrupted)}")

        assert "plan.json" in corrupted, "损坏的文件应该被检测到"
        assert "requirements.json" not in corrupted
        assert "templates.json" not in corrupted

        print(f"\n{'=' * 70}")
        print("✅ 测试6通过！")
        print("=" * 70)
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("重试机制测试套件")
    print("=" * 70)

    tests = [
        test_basic_retry_check,
        test_retry_count_limit,
        test_non_retryable_errors,
        test_partial_retry_strategy,
        test_clean_retry_strategy,
        test_file_validation
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ 测试失败: {test_func.__name__}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"  通过: {passed}/{len(tests)}")
    print(f"  失败: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 所有测试通过！重试机制工作正常。")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} 个测试失败，请检查实现。")
        sys.exit(1)
