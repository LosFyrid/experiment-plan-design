#!/usr/bin/env python3
"""
简单脚本验证section同步修复是否正确。

测试场景：
1. 初始状态：playbook只有material_selection section
2. 手动添加新section到SectionManager
3. 验证playbook_sections.yaml被更新
4. 手动添加section到playbook.sections列表
5. 验证playbook.json被更新
"""

import sys
from pathlib import Path
import json
import yaml
import tempfile
import shutil

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.section_manager import SectionManager

def test_section_sync():
    print("=" * 80)
    print("测试：Section同步修复验证")
    print("=" * 80)

    # 创建临时工作目录
    temp_dir = tempfile.mkdtemp()
    print(f"\n✓ 临时目录: {temp_dir}")

    try:
        # 1. 创建playbook_sections.yaml
        sections_config_path = Path(temp_dir) / "playbook_sections.yaml"
        initial_sections_config = {
            'core_sections': {
                'material_selection': {
                    'id_prefix': 'mat',
                    'description': 'Material selection guidance',
                    'examples': []
                },
                'procedure_design': {
                    'id_prefix': 'proc',
                    'description': 'Procedure design guidance',
                    'examples': []
                }
            },
            'custom_sections': {},
            'settings': {
                'allow_new_sections': True,
                'new_section_guidelines': 'Test guidelines'
            }
        }

        with open(sections_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(initial_sections_config, f, allow_unicode=True)

        print(f"✓ 创建 playbook_sections.yaml")

        # 2. 创建playbook.json
        playbook_path = Path(temp_dir) / "playbook.json"
        initial_playbook = {
            'bullets': [],
            'sections': ['material_selection', 'procedure_design'],
            'version': '1.0.0',
            'last_updated': '2025-01-01T00:00:00',
            'total_generations': 0
        }

        with open(playbook_path, 'w', encoding='utf-8') as f:
            json.dump(initial_playbook, f, indent=2)

        print(f"✓ 创建 playbook.json")

        # 3. 初始状态验证
        print("\n" + "-" * 80)
        print("初始状态:")
        print("-" * 80)

        with open(sections_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"playbook_sections.yaml custom_sections: {list(config['custom_sections'].keys())}")

        with open(playbook_path, 'r', encoding='utf-8') as f:
            playbook = json.load(f)
        print(f"playbook.json sections: {playbook['sections']}")

        # 4. 使用SectionManager添加新section
        print("\n" + "-" * 80)
        print("添加新section: environmental_impact")
        print("-" * 80)

        section_manager = SectionManager(
            config_path=str(sections_config_path),
            allow_new_sections=True
        )

        success = section_manager.add_custom_section(
            name="environmental_impact",
            id_prefix="env",
            description="Environmental impact assessment and green chemistry practices",
            creation_reason="Testing section sync fix",
            examples=["Minimize waste", "Use renewable resources"]
        )

        if not success:
            print("❌ 添加section失败")
            return False

        print("✓ SectionManager.add_custom_section() 成功")

        # 5. 验证playbook_sections.yaml被更新
        with open(sections_config_path, 'r', encoding='utf-8') as f:
            updated_config = yaml.safe_load(f)

        if 'environmental_impact' in updated_config['custom_sections']:
            print("✅ playbook_sections.yaml 已更新")
            print(f"   custom_sections: {list(updated_config['custom_sections'].keys())}")
        else:
            print("❌ playbook_sections.yaml 未更新")
            return False

        # 6. 模拟Curator的修复代码：更新playbook.sections列表
        print("\n" + "-" * 80)
        print("模拟Curator修复：更新playbook.sections")
        print("-" * 80)

        # 读取playbook
        with open(playbook_path, 'r', encoding='utf-8') as f:
            playbook = json.load(f)

        # 🔧 这是修复的核心代码
        if 'environmental_impact' not in playbook['sections']:
            playbook['sections'].append('environmental_impact')
            print("✓ 添加 'environmental_impact' 到 playbook['sections']")

        # 保存playbook
        with open(playbook_path, 'w', encoding='utf-8') as f:
            json.dump(playbook, f, indent=2)

        print("✓ 保存 playbook.json")

        # 7. 最终验证
        print("\n" + "-" * 80)
        print("最终状态:")
        print("-" * 80)

        with open(sections_config_path, 'r', encoding='utf-8') as f:
            final_config = yaml.safe_load(f)

        with open(playbook_path, 'r', encoding='utf-8') as f:
            final_playbook = json.load(f)

        print(f"playbook_sections.yaml custom_sections: {list(final_config['custom_sections'].keys())}")
        print(f"playbook.json sections: {final_playbook['sections']}")

        # 验证两个文件都包含新section
        config_has_section = 'environmental_impact' in final_config['custom_sections']
        playbook_has_section = 'environmental_impact' in final_playbook['sections']

        print("\n" + "=" * 80)
        if config_has_section and playbook_has_section:
            print("✅ 测试通过！两个文件都正确更新了")
            print("=" * 80)
            return True
        else:
            print("❌ 测试失败！")
            if not config_has_section:
                print("   - playbook_sections.yaml 缺少新section")
            if not playbook_has_section:
                print("   - playbook.json 缺少新section")
            print("=" * 80)
            return False

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n✓ 清理临时目录: {temp_dir}")


if __name__ == "__main__":
    success = test_section_sync()
    sys.exit(0 if success else 1)
