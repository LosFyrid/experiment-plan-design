#!/usr/bin/env python3
"""
自动化脚本：使用多个模型运行本体构建

该脚本会依次使用不同的LLM模型运行 ontology_builder.py，
并自动备份每个模型生成的本体文件。

使用方法:
    python run_multiple_models.py
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime

# ==================== 配置区 ====================

# 要测试的模型列表
MODELS = [
    "qwen3-max",
    "qwen3-next-80b-a3b-thinking",
    "qwen3-235b-a22b-thinking-2507"
]

# Python 解释器路径
PYTHON_PATH = "/home/syk/miniconda3/envs/OntologyConstruction/bin/python"

# ontology_builder.py 文件路径
BUILDER_SCRIPT = "/home/syk/projects/experiment-plan-design/src/external/MOSES/test/onto_cons/ontology_builder.py"

# 输入数据路径
INPUT_PATH = "src/external/MOSES/data/processed_text/Baruwa2025 _ Mater. Res. Express _ Characteristics and properties of hot-deformed duplex stainless steel 2205 an overview.json"

# 本体文件输出目录
ONTOLOGY_DIR = Path("src/external/MOSES/data/ontology")

# 生成的本体文件名
ONTOLOGY_FILE = "chem_ontology.owl"

# 运行参数
RUN_ARGS = ["--parallel", "--extractor-type", "refined"]

# ===============================================


def log(message, level="INFO"):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def backup_ontology(model_name):
    """备份生成的本体文件"""
    source = ONTOLOGY_DIR / ONTOLOGY_FILE

    if not source.exists():
        log(f"警告: 未找到本体文件 {source}", "WARNING")
        return False

    # 生成备份文件名：模型名_时间戳.owl
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{model_name}_{timestamp}.owl"
    backup_path = ONTOLOGY_DIR / backup_name

    try:
        shutil.copy2(source, backup_path)
        log(f"✓ 本体文件已备份到: {backup_path}")

        # 获取文件大小
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        log(f"  文件大小: {size_mb:.2f} MB")

        return True
    except Exception as e:
        log(f"错误: 备份文件失败: {e}", "ERROR")
        return False


def create_empty_ontology():
    """创建空白的本体文件"""
    ontology_path = ONTOLOGY_DIR / ONTOLOGY_FILE

    try:
        # 创建一个最小的OWL文件
        empty_owl_content = """
"""
        with open(ontology_path, 'w', encoding='utf-8') as f:
            f.write(empty_owl_content)

        log(f"✓ 已创建空白本体文件: {ontology_path}")
        return True
    except Exception as e:
        log(f"错误: 创建空白本体文件失败: {e}", "ERROR")
        return False


def modify_model_in_script(model_name):
    """修改 ontology_builder.py 中的模型名称"""
    try:
        with open(BUILDER_SCRIPT, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找并替换模型名称
        # 原始行类似: lm = dspy.LM('openai/qwen3-next-80b-a3b-thinking', temperature=0, ...)
        import re
        pattern = r"(lm = dspy\.LM\('openai/)[^']+(')"
        replacement = rf"\1{model_name}\2"

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            log(f"警告: 未找到要替换的模型配置行", "WARNING")
            return False

        # 写回文件
        with open(BUILDER_SCRIPT, 'w', encoding='utf-8') as f:
            f.write(new_content)

        log(f"✓ 已将模型更改为: openai/{model_name}")
        return True

    except Exception as e:
        log(f"错误: 修改脚本失败: {e}", "ERROR")
        return False


def run_ontology_builder(model_name):
    """运行 ontology_builder.py"""
    log(f"开始使用模型 '{model_name}' 构建本体...")
    log("=" * 80)

    # 构建命令
    cmd = [
        PYTHON_PATH,
        BUILDER_SCRIPT,
        "--input-path", INPUT_PATH,
        *RUN_ARGS
    ]

    log(f"执行命令: {' '.join(cmd)}")

    start_time = time.time()

    try:
        # 运行命令并实时输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # 实时打印输出
        for line in process.stdout:
            print(line, end='')

        process.wait()

        elapsed_time = time.time() - start_time

        if process.returncode == 0:
            log(f"✓ 模型 '{model_name}' 运行成功！耗时: {elapsed_time:.1f} 秒")
            log("=" * 80)
            return True
        else:
            log(f"✗ 模型 '{model_name}' 运行失败！返回码: {process.returncode}", "ERROR")
            log("=" * 80)
            return False

    except Exception as e:
        log(f"✗ 运行出错: {e}", "ERROR")
        log("=" * 80)
        return False


def main():
    """主函数"""
    log("=" * 80)
    log("开始自动化本体构建流程")
    log(f"共需测试 {len(MODELS)} 个模型")
    log("=" * 80)

    # 确保输出目录存在
    ONTOLOGY_DIR.mkdir(parents=True, exist_ok=True)

    # 备份原始脚本
    backup_script_path = Path(BUILDER_SCRIPT).with_suffix('.py.backup')
    try:
        shutil.copy2(BUILDER_SCRIPT, backup_script_path)
        log(f"✓ 已备份原始脚本到: {backup_script_path}")
    except Exception as e:
        log(f"警告: 无法备份原始脚本: {e}", "WARNING")

    # 统计信息
    success_count = 0
    failed_models = []

    total_start_time = time.time()

    # 遍历每个模型
    for idx, model_name in enumerate(MODELS, 1):
        log("")
        log(f"{'#' * 80}")
        log(f"# 进度: [{idx}/{len(MODELS)}] 处理模型: {model_name}")
        log(f"{'#' * 80}")
        log("")

        # 步骤1: 修改脚本中的模型
        if not modify_model_in_script(model_name):
            log(f"跳过模型 '{model_name}'", "WARNING")
            failed_models.append(model_name)
            continue

        # 步骤2: 运行本体构建
        if not run_ontology_builder(model_name):
            log(f"模型 '{model_name}' 构建失败", "ERROR")
            failed_models.append(model_name)
            continue

        # 步骤3: 备份生成的本体文件
        if not backup_ontology(model_name):
            log(f"模型 '{model_name}' 备份失败", "WARNING")

        # 步骤4: 如果不是最后一个模型，创建空白本体文件
        if idx < len(MODELS):
            log("")
            log("准备下一个模型...")
            if not create_empty_ontology():
                log("警告: 创建空白本体文件失败，继续下一个模型", "WARNING")
            time.sleep(2)  # 短暂延迟

        success_count += 1
        log("")

    # 恢复原始脚本（可选）
    try:
        if backup_script_path.exists():
            shutil.copy2(backup_script_path, BUILDER_SCRIPT)
            log(f"✓ 已恢复原始脚本配置")
            backup_script_path.unlink()  # 删除备份
    except Exception as e:
        log(f"警告: 恢复原始脚本失败: {e}", "WARNING")

    # 打印总结
    total_elapsed_time = time.time() - total_start_time
    log("")
    log("=" * 80)
    log("自动化构建完成！")
    log("=" * 80)
    log(f"总耗时: {total_elapsed_time / 60:.1f} 分钟")
    log(f"成功: {success_count}/{len(MODELS)}")

    if failed_models:
        log(f"失败的模型: {', '.join(failed_models)}", "WARNING")
    else:
        log("所有模型均成功完成！✓")

    log("")
    log("生成的本体文件位于: " + str(ONTOLOGY_DIR))
    log("=" * 80)

    return 0 if success_count == len(MODELS) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n用户中断执行", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"未预期的错误: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
