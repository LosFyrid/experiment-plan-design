#!/bin/bash
# 简化的启动脚本

cd /home/syk/projects/experiment-plan-design

echo "========================================"
echo "开始自动化本体构建"
echo "========================================"
echo ""
echo "注意: 这个过程可能需要较长时间"
echo "建议使用 nohup 或 screen 在后台运行"
echo ""

# 激活 conda 环境并运行
conda run -n OntologyConstruction python src/external/MOSES/test/onto_cons/run_multiple_models.py

echo ""
echo "========================================"
echo "构建完成！"
echo "========================================"
