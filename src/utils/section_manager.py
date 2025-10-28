"""
Section Manager - 管理playbook sections的加载、验证和动态添加

负责：
1. 加载section配置（core + custom）
2. 提供section查询接口
3. 管理新section的添加和审批
4. 生成Curator prompt所需的section信息
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from datetime import datetime


class SectionManager:
    """管理playbook sections的加载、验证和动态添加"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        allow_new_sections: Optional[bool] = None
    ):
        """
        初始化Section Manager

        Args:
            config_path: Section配置文件路径（默认从ace_config读取）
            allow_new_sections: 运行时覆盖配置文件中的allow_new_sections设置
                               如果为None，则使用配置文件中的值
        """
        # 从 ACE 配置读取默认路径
        if config_path is None:
            try:
                from utils.config_loader import get_ace_config
                ace_config = get_ace_config()
                config_path = ace_config.playbook.sections_config
            except Exception as e:
                # Fallback to default if config loading fails
                config_path = "configs/playbook_sections.yaml"
                print(f"⚠️ Warning: Could not load sections_config from ace_config, using default. Error: {e}")

        project_root = Path(__file__).parent.parent.parent
        self.config_path = project_root / config_path
        self.config = self._load_config()

        # 运行时参数覆盖配置文件
        if allow_new_sections is not None:
            self.config['settings']['allow_new_sections'] = allow_new_sections

    def _load_config(self) -> dict:
        """加载section配置"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Section configuration not found: {self.config_path}"
            )

        with open(self.config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_all_sections(self) -> Dict[str, dict]:
        """
        获取所有sections（core + custom）

        Returns:
            Dict[section_name, section_info]
        """
        sections = {}
        sections.update(self.config['core_sections'])
        sections.update(self.config.get('custom_sections', {}))
        return sections

    def get_section_names(self) -> List[str]:
        """获取所有section名称列表"""
        return list(self.get_all_sections().keys())

    def get_id_prefixes(self) -> Dict[str, str]:
        """
        获取section -> id_prefix映射

        Returns:
            Dict[section_name, id_prefix]
        """
        return {
            name: info['id_prefix']
            for name, info in self.get_all_sections().items()
        }

    def get_section_info(self, section_name: str) -> Optional[dict]:
        """
        获取section的详细信息

        Args:
            section_name: Section名称

        Returns:
            Section信息dict，如果不存在返回None
        """
        return self.get_all_sections().get(section_name)

    def is_section_valid(self, section_name: str) -> bool:
        """检查section是否有效"""
        return section_name in self.get_section_names()

    def is_new_section_allowed(self) -> bool:
        """是否允许提议新sections"""
        return self.config['settings']['allow_new_sections']

    def get_new_section_guidelines(self) -> str:
        """获取新section提议的引导原则（用于Curator prompt）"""
        return self.config['settings']['new_section_guidelines']

    def add_custom_section(
        self,
        name: str,
        id_prefix: str,
        description: str,
        creation_reason: str,
        examples: Optional[List[str]] = None
    ) -> bool:
        """
        添加新的custom section到配置

        Args:
            name: Section名称（snake_case）
            id_prefix: ID前缀（2-4字母）
            description: Section描述
            creation_reason: 创建原因说明
            examples: 示例bullets列表

        Returns:
            是否成功添加
        """
        # 检查是否已存在
        if self.is_section_valid(name):
            print(f"Section '{name}' already exists")
            return False

        # 检查id_prefix是否冲突
        existing_prefixes = self.get_id_prefixes().values()
        if id_prefix in existing_prefixes:
            print(f"ID prefix '{id_prefix}' already in use")
            return False

        # 添加到内存
        if 'custom_sections' not in self.config:
            self.config['custom_sections'] = {}

        self.config['custom_sections'][name] = {
            'id_prefix': id_prefix,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'created_by': 'curator',
            'creation_reason': creation_reason,
            'examples': examples or []
        }

        # 保存到文件
        self._save_config()

        print(f"✅ Added new custom section: {name} ({id_prefix})")
        return True

    def _save_config(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                self.config,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False
            )

    def format_sections_for_prompt(self) -> str:
        """
        格式化sections信息用于Curator prompt

        Returns:
            格式化的sections描述字符串
        """
        sections = self.get_all_sections()
        lines = []

        lines.append("## Available Playbook Sections\n")
        lines.append("When creating delta operations, use 'section' field to specify which section the bullet belongs to.\n")
        lines.append("**Valid sections**:\n")

        for name, info in sections.items():
            desc = info.get('description', 'No description')
            is_custom = name in self.config.get('custom_sections', {})
            custom_marker = " [CUSTOM]" if is_custom else ""

            lines.append(f"\n- **{name}**{custom_marker}: {desc}")

            # 添加examples（如果有）
            examples = info.get('examples', [])
            if examples:
                lines.append(f"  Examples:")
                for ex in examples[:3]:  # 最多显示3个examples
                    lines.append(f"    - {ex}")

        # 添加新section提议说明（如果允许）
        if self.is_new_section_allowed():
            lines.append(f"\n\n## Proposing New Sections\n")
            lines.append(self.get_new_section_guidelines())
        else:
            lines.append(f"\n\n**Important**: Only use sections listed above. Do not create new sections.")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取section统计信息"""
        all_sections = self.get_all_sections()
        return {
            'total_sections': len(all_sections),
            'core_sections': len(self.config['core_sections']),
            'custom_sections': len(self.config.get('custom_sections', {})),
            'allow_new_sections': self.is_new_section_allowed(),
            'sections': list(all_sections.keys())
        }
