#!/usr/bin/env python3
"""
OWL Ontology Class Hierarchy Exporter

This script exports all classes from an OWL ontology file in hierarchical format
to both JSON and Markdown (unordered list) formats.

Usage:
    python export_ontology_hierarchy.py <ontology_file> [--output <output_prefix>]

Example:
    python export_ontology_hierarchy.py my_ontology.owl --output results/ontology
"""

import argparse
import json
import os
from typing import Dict, List, Any
from owlready2 import get_ontology, Thing, ThingClass


def build_class_hierarchy(cls: ThingClass, visited: set = None) -> Dict[str, Any]:
    """
    递归构建类的层级结构

    Args:
        cls: 当前要处理的类
        visited: 已访问过的类集合，用于避免循环引用

    Returns:
        包含类信息和子类的字典
    """
    if visited is None:
        visited = set()

    # 避免循环引用
    if cls in visited:
        return {
            'name': cls.name,
            'iri': cls.iri,
            'note': 'circular_reference',
            'children': []
        }

    visited.add(cls)

    # 获取类的标签（如果有）
    label = None
    if hasattr(cls, 'label') and cls.label:
        if isinstance(cls.label, list) and len(cls.label) > 0:
            label = str(cls.label[0])
        else:
            label = str(cls.label)

    # 获取类的注释（如果有）
    comment = None
    if hasattr(cls, 'comment') and cls.comment:
        if isinstance(cls.comment, list) and len(cls.comment) > 0:
            comment = str(cls.comment[0])
        else:
            comment = str(cls.comment)

    # 构建类信息
    class_info = {
        'name': cls.name,
        'iri': cls.iri,
    }

    if label:
        class_info['label'] = label
    if comment:
        class_info['comment'] = comment

    # 递归获取所有子类
    children = []
    for subclass in cls.subclasses():
        # 创建新的visited副本，避免兄弟节点之间的干扰
        child_info = build_class_hierarchy(subclass, visited.copy())
        children.append(child_info)

    class_info['children'] = children

    return class_info


def export_to_json(hierarchy: Dict[str, Any], output_file: str) -> None:
    """
    将层级结构导出为JSON文件

    Args:
        hierarchy: 类层级结构字典
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON格式已导出到: {output_file}")


def export_to_markdown(hierarchy: Dict[str, Any], output_file: str) -> None:
    """
    将层级结构导出为Markdown格式的无序列表

    Args:
        hierarchy: 类层级结构字典
        output_file: 输出文件路径
    """
    def write_class_tree(f, class_info: Dict[str, Any], level: int = 0) -> None:
        """递归写入类树结构"""
        indent = '  ' * level

        # 构建类的显示名称
        display_name = class_info['name']
        if 'label' in class_info:
            display_name = f"{class_info['label']} ({class_info['name']})"

        # 写入当前类
        f.write(f"{indent}- **{display_name}**")

        # 如果有注释，添加注释
        if 'comment' in class_info:
            f.write(f"\n{indent}  - Comment: {class_info['comment']}")

        # 如果有循环引用标记
        if 'note' in class_info and class_info['note'] == 'circular_reference':
            f.write(f"\n{indent}  - Note: *Circular reference detected*")

        f.write('\n')

        # 递归写入子类
        if class_info['children']:
            for child in class_info['children']:
                write_class_tree(f, child, level + 1)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# Ontology Class Hierarchy\n\n')
        f.write(f"Total classes: {count_classes(hierarchy)}\n\n")
        f.write('---\n\n')
        write_class_tree(f, hierarchy)

    print(f"✓ Markdown格式已导出到: {output_file}")


def count_classes(hierarchy: Dict[str, Any]) -> int:
    """
    统计层级结构中的类总数

    Args:
        hierarchy: 类层级结构字典

    Returns:
        类的总数
    """
    count = 1
    for child in hierarchy.get('children', []):
        count += count_classes(child)
    return count


def export_flat_list(ontology, output_file: str) -> None:
    """
    导出所有类的扁平列表（包含父类信息）

    Args:
        ontology: 本体对象
        output_file: 输出文件路径
    """
    classes_list = []

    for cls in ontology.classes():
        # 获取直接父类
        parents = [p.name for p in cls.is_a if isinstance(p, ThingClass)]

        # 获取标签
        label = None
        if hasattr(cls, 'label') and cls.label:
            if isinstance(cls.label, list) and len(cls.label) > 0:
                label = str(cls.label[0])
            else:
                label = str(cls.label)

        class_info = {
            'name': cls.name,
            'iri': cls.iri,
            'direct_parents': parents,
        }

        if label:
            class_info['label'] = label

        classes_list.append(class_info)

    # 按名称排序
    classes_list.sort(key=lambda x: x['name'])

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(classes_list, f, indent=2, ensure_ascii=False)

    print(f"✓ 扁平列表已导出到: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Export OWL ontology class hierarchy to JSON and Markdown formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ontology.owl
  %(prog)s ontology.owl --output results/my_ontology
  %(prog)s ontology.owl -o output/hierarchy --flat
        """
    )

    parser.add_argument(
        'ontology_file',
        help='Path to the OWL ontology file (.owl, .rdf, etc.)'
    )

    parser.add_argument(
        '-o', '--output',
        default='ontology_hierarchy',
        help='Output file prefix (default: ontology_hierarchy)'
    )

    parser.add_argument(
        '--flat',
        action='store_true',
        help='Also export a flat list of all classes with parent information'
    )

    parser.add_argument(
        '--root',
        default='Thing',
        help='Root class name to start the hierarchy from (default: Thing)'
    )

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.ontology_file):
        print(f"错误: 文件不存在: {args.ontology_file}")
        return 1

    # 创建输出目录（如果需要）
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✓ 创建输出目录: {output_dir}")

    print(f"正在加载本体文件: {args.ontology_file}")

    try:
        # 加载本体
        ontology = get_ontology(f"file://{os.path.abspath(args.ontology_file)}").load()
        print(f"✓ 本体加载成功")

        # 确定根类
        if args.root == 'Thing':
            root_class = Thing
        else:
            # 尝试从本体中获取指定的根类
            root_class = getattr(ontology, args.root, None)
            if root_class is None:
                print(f"警告: 找不到类 '{args.root}'，使用默认的 Thing 作为根类")
                root_class = Thing

        print(f"正在构建类层级结构（从 {root_class.name} 开始）...")

        # 构建层级结构
        hierarchy = build_class_hierarchy(root_class)

        total_classes = count_classes(hierarchy)
        print(f"✓ 层级结构构建完成，共 {total_classes} 个类")

        # 导出为JSON
        json_file = f"{args.output}.json"
        export_to_json(hierarchy, json_file)

        # 导出为Markdown
        md_file = f"{args.output}.md"
        export_to_markdown(hierarchy, md_file)

        # 如果需要，导出扁平列表
        if args.flat:
            flat_file = f"{args.output}_flat.json"
            export_flat_list(ontology, flat_file)

        print(f"\n✓ 所有导出完成!")
        print(f"  - 类层级总数: {total_classes}")
        print(f"  - 本体中定义的类总数: {len(list(ontology.classes()))}")

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())