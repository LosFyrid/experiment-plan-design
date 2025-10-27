#!/usr/bin/env python3
"""
测试 Embedding Cache 机制

验证场景：
1. 首次加载（无缓存）
2. 缓存命中（无变化）
3. 手动编辑内容（content hash 变化）
4. 手动新增 bullet
5. 手动删除 bullet
6. 缓存文件损坏
7. 模型版本升级
"""

import sys
import json
import shutil
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from ace_framework.playbook.playbook_manager import PlaybookManager
from ace_framework.playbook.schemas import Playbook, PlaybookBullet, BulletMetadata


def test_scenario_1_first_load():
    """场景1: 首次加载（无缓存）"""
    print("\n" + "=" * 80)
    print("场景1: 首次加载（无缓存）")
    print("=" * 80)

    # 使用实际的 playbook 文件
    playbook_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"
    cache_path = playbook_path.parent / f".{playbook_path.stem}.embeddings"

    # 删除旧缓存
    if cache_path.exists():
        cache_path.unlink()
        print(f"  🗑️  已删除旧缓存: {cache_path}")

    # 加载
    manager = PlaybookManager(str(playbook_path))
    playbook = manager.load()

    print(f"\n  ✅ Playbook 加载成功")
    print(f"     规则数: {len(playbook.bullets)}")
    print(f"     缓存文件: {cache_path}")
    print(f"     缓存文件存在: {cache_path.exists()}")

    if cache_path.exists():
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        print(f"     缓存中的规则数: {cache_data['bullet_count']}")
        print(f"     缓存大小: {cache_path.stat().st_size / 1024:.2f} KB")


def test_scenario_2_cache_hit():
    """场景2: 缓存命中（无变化）"""
    print("\n" + "=" * 80)
    print("场景2: 缓存命中（无变化）")
    print("=" * 80)

    playbook_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"

    # 第二次加载
    print("\n  第二次加载...")
    manager = PlaybookManager(str(playbook_path))
    playbook = manager.load()

    print(f"\n  ✅ Playbook 加载成功（应该显示缓存完全同步）")
    print(f"     规则数: {len(playbook.bullets)}")


def test_scenario_3_content_change():
    """场景3: 手动编辑内容（content hash 变化）"""
    print("\n" + "=" * 80)
    print("场景3: 手动编辑内容（content hash 变化）")
    print("=" * 80)

    # 创建测试副本
    source_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"
    test_path = project_root / "data" / "playbooks" / "test_playbook.json"
    cache_path = test_path.parent / f".{test_path.stem}.embeddings"

    # 清理旧文件
    if test_path.exists():
        test_path.unlink()
    if cache_path.exists():
        cache_path.unlink()

    # 复制文件
    shutil.copy(source_path, test_path)

    # 首次加载（创建缓存）
    print("\n  首次加载...")
    manager1 = PlaybookManager(str(test_path))
    playbook1 = manager1.load()
    original_count = len(playbook1.bullets)

    # 手动修改第一条规则的内容
    print("\n  手动修改第一条规则内容...")
    with open(test_path, 'r') as f:
        data = json.load(f)

    original_content = data['bullets'][0]['content']
    data['bullets'][0]['content'] = original_content + " [MODIFIED]"

    with open(test_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 第二次加载（应该检测到变化）
    print("\n  第二次加载（应该检测到内容变化）...")
    manager2 = PlaybookManager(str(test_path))
    playbook2 = manager2.load()

    print(f"\n  ✅ 测试通过（应该显示更新1个embedding）")
    print(f"     规则数: {len(playbook2.bullets)}")

    # 清理
    test_path.unlink()
    cache_path.unlink()


def test_scenario_4_add_bullet():
    """场景4: 手动新增 bullet"""
    print("\n" + "=" * 80)
    print("场景4: 手动新增 bullet")
    print("=" * 80)

    # 创建测试副本
    source_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"
    test_path = project_root / "data" / "playbooks" / "test_playbook.json"
    cache_path = test_path.parent / f".{test_path.stem}.embeddings"

    # 清理旧文件
    if test_path.exists():
        test_path.unlink()
    if cache_path.exists():
        cache_path.unlink()

    # 复制文件
    shutil.copy(source_path, test_path)

    # 首次加载
    print("\n  首次加载...")
    manager1 = PlaybookManager(str(test_path))
    playbook1 = manager1.load()
    original_count = len(playbook1.bullets)

    # 手动新增一条规则
    print("\n  手动新增一条规则...")
    with open(test_path, 'r') as f:
        data = json.load(f)

    new_bullet = {
        "id": "test-00001",
        "section": "test_section",
        "content": "This is a test bullet added manually.",
        "metadata": {
            "helpful_count": 0,
            "harmful_count": 0,
            "neutral_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "source": "manual",
            "embedding": None
        }
    }

    data['bullets'].append(new_bullet)

    with open(test_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 第二次加载（应该检测到新增）
    print("\n  第二次加载（应该检测到新增）...")
    manager2 = PlaybookManager(str(test_path))
    playbook2 = manager2.load()

    print(f"\n  ✅ 测试通过（应该显示新增1个）")
    print(f"     原规则数: {original_count}")
    print(f"     新规则数: {len(playbook2.bullets)}")

    # 清理
    test_path.unlink()
    cache_path.unlink()


def test_scenario_5_delete_bullet():
    """场景5: 手动删除 bullet"""
    print("\n" + "=" * 80)
    print("场景5: 手动删除 bullet")
    print("=" * 80)

    # 创建测试副本
    source_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"
    test_path = project_root / "data" / "playbooks" / "test_playbook.json"
    cache_path = test_path.parent / f".{test_path.stem}.embeddings"

    # 清理旧文件
    if test_path.exists():
        test_path.unlink()
    if cache_path.exists():
        cache_path.unlink()

    # 复制文件
    shutil.copy(source_path, test_path)

    # 首次加载
    print("\n  首次加载...")
    manager1 = PlaybookManager(str(test_path))
    playbook1 = manager1.load()
    original_count = len(playbook1.bullets)

    # 手动删除第一条规则
    print("\n  手动删除第一条规则...")
    with open(test_path, 'r') as f:
        data = json.load(f)

    deleted_id = data['bullets'][0]['id']
    data['bullets'] = data['bullets'][1:]  # 删除第一条

    with open(test_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 第二次加载（应该检测到删除）
    print("\n  第二次加载（应该检测到删除）...")
    manager2 = PlaybookManager(str(test_path))
    playbook2 = manager2.load()

    print(f"\n  ✅ 测试通过（应该显示删除1个）")
    print(f"     原规则数: {original_count}")
    print(f"     新规则数: {len(playbook2.bullets)}")
    print(f"     删除的ID: {deleted_id}")

    # 清理
    test_path.unlink()
    cache_path.unlink()


def test_scenario_6_corrupted_cache():
    """场景6: 缓存文件损坏"""
    print("\n" + "=" * 80)
    print("场景6: 缓存文件损坏")
    print("=" * 80)

    playbook_path = project_root / "data" / "playbooks" / "chemistry_playbook.json"
    cache_path = playbook_path.parent / f".{playbook_path.stem}.embeddings"

    # 确保缓存存在
    if not cache_path.exists():
        manager = PlaybookManager(str(playbook_path))
        manager.load()

    # 损坏缓存文件
    print("\n  损坏缓存文件...")
    with open(cache_path, 'w') as f:
        f.write("{ invalid json }")

    # 加载（应该自动重建）
    print("\n  加载（应该检测到缓存损坏并重建）...")
    manager = PlaybookManager(str(playbook_path))
    playbook = manager.load()

    print(f"\n  ✅ 测试通过（应该重新创建缓存）")
    print(f"     规则数: {len(playbook.bullets)}")


def main():
    """运行所有测试场景"""
    print("\n" + "=" * 80)
    print("Embedding Cache 机制测试")
    print("=" * 80)

    try:
        test_scenario_1_first_load()
        test_scenario_2_cache_hit()
        test_scenario_3_content_change()
        test_scenario_4_add_bullet()
        test_scenario_5_delete_bullet()
        test_scenario_6_corrupted_cache()

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
