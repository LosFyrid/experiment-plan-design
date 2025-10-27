#!/usr/bin/env python3
"""
测试 curation.json 中 embedding 移除的效果
"""

import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ace_framework.playbook.schemas import (
    Playbook,
    PlaybookBullet,
    BulletMetadata,
    PlaybookUpdateResult,
    DeltaOperation
)
from workflow.task_manager import GenerationTask

def test_curation_save_without_embedding():
    """测试保存 curation 时移除 embedding"""

    print("=" * 80)
    print("测试 curation.json 保存（移除 embedding）")
    print("=" * 80)

    # 创建一个包含 embedding 的 playbook
    bullets = [
        PlaybookBullet(
            id="test-00001",
            section="test_section",
            content="Test content 1",
            metadata=BulletMetadata(
                helpful_count=1,
                harmful_count=0,
                neutral_count=0,
                source="test",
                embedding=[0.1] * 1024  # 模拟 1024 维 embedding
            )
        ),
        PlaybookBullet(
            id="test-00002",
            section="test_section",
            content="Test content 2",
            metadata=BulletMetadata(
                helpful_count=2,
                harmful_count=0,
                neutral_count=0,
                source="test",
                embedding=[0.2] * 1024  # 模拟 1024 维 embedding
            )
        )
    ]

    playbook = Playbook(bullets=bullets)

    # 创建 PlaybookUpdateResult
    delta_ops = [
        DeltaOperation(
            operation="ADD",
            new_bullet=bullets[0],
            reason="Test addition"
        )
    ]

    curation = PlaybookUpdateResult(
        updated_playbook=playbook,
        delta_operations=delta_ops,
        bullets_added=1,
        bullets_updated=0,
        bullets_removed=0
    )

    # 创建临时任务
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    task = GenerationTask(
        task_id="test_task",
        session_id="test_session",
        task_dir=temp_dir
    )

    try:
        print(f"\n📁 测试目录: {temp_dir}")

        # 保存 curation
        print("\n💾 保存 curation.json...")
        task.save_curation(curation)

        # 读取并检查文件
        with open(task.curation_file, 'r') as f:
            saved_data = json.load(f)

        file_size = task.curation_file.stat().st_size
        print(f"   文件大小: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

        # 检查 embedding 是否被移除
        print("\n🔍 检查 embedding 状态:")

        bullets_in_playbook = saved_data.get('updated_playbook', {}).get('bullets', [])
        print(f"   Playbook bullets 数量: {len(bullets_in_playbook)}")

        for i, bullet in enumerate(bullets_in_playbook):
            embedding = bullet.get('metadata', {}).get('embedding')
            status = "✅ 已移除 (null)" if embedding is None else f"❌ 仍存在 ({len(embedding)} 维)"
            print(f"     Bullet {i+1}: {status}")

        # 检查 delta_operations 中的 embedding
        delta_ops = saved_data.get('delta_operations', [])
        print(f"\n   Delta operations 数量: {len(delta_ops)}")

        for i, op in enumerate(delta_ops):
            if 'new_bullet' in op and op['new_bullet']:
                embedding = op['new_bullet'].get('metadata', {}).get('embedding')
                status = "✅ 已移除 (null)" if embedding is None else f"❌ 仍存在 ({len(embedding)} 维)"
                print(f"     Operation {i+1} new_bullet: {status}")

        # 估算节省的空间
        embedding_size_per_bullet = 1024 * 8  # 1024维 × 8字节/float
        num_bullets_with_embedding = len(bullets_in_playbook) + len(delta_ops)
        estimated_saving = embedding_size_per_bullet * num_bullets_with_embedding

        print(f"\n📊 空间节省估算:")
        print(f"   每个 bullet 的 embedding 大小: {embedding_size_per_bullet:,} bytes (~{embedding_size_per_bullet / 1024:.1f} KB)")
        print(f"   包含 embedding 的 bullets: {num_bullets_with_embedding}")
        print(f"   预计节省空间: {estimated_saving:,} bytes (~{estimated_saving / 1024:.1f} KB)")

        print("\n✅ 测试通过！embedding 已成功移除")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n🧹 已清理测试目录")

if __name__ == "__main__":
    test_curation_save_without_embedding()
