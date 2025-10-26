#!/usr/bin/env python3
"""
构建 RAG 索引

使用方法：
    conda activate OntologyConstruction
    python build_rag_index.py
"""

import sys
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from external.rag.largerag import LargeRAG

def main():
    print("=" * 70)
    print("构建 RAG 索引")
    print("=" * 70)

    # 数据路径
    data_path = "src/external/rag/data/test_papers"

    print(f"\n数据目录: {data_path}")
    print("正在初始化 LargeRAG...")

    try:
        rag = LargeRAG()
        print("✅ LargeRAG 初始化完成")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n开始构建索引...")
    print("(这可能需要几分钟，请耐心等待...)")

    try:
        success = rag.index_from_folders(data_path)

        if success:
            print("\n" + "=" * 70)
            print("✅ 索引构建成功！")
            print("=" * 70)

            # 获取统计信息
            try:
                stats = rag.get_stats()
                print(f"\n索引统计:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            except:
                pass

            return True
        else:
            print("\n❌ 索引构建失败！")
            return False

    except Exception as e:
        print(f"\n❌ 构建过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()

    if success:
        print("\n下一步:")
        print("  python test_rag_integration.py  # 测试 RAG 集成")
        sys.exit(0)
    else:
        print("\n故障排查:")
        print("  1. 检查数据目录是否存在")
        print("  2. 检查 DASHSCOPE_API_KEY 是否配置")
        print("  3. 查看详细错误信息")
        sys.exit(1)
