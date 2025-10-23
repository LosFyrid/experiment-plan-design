#!/bin/bash
# 快速启动：在后台运行本体构建

echo "=========================================="
echo "🚀 启动自动化本体构建（后台模式）"
echo "=========================================="
echo ""

cd /home/syk/projects/experiment-plan-design

# 检查是否已经有进程在运行
if pgrep -f "run_multiple_models.py" > /dev/null; then
    echo "⚠️  警告: 检测到已有构建进程在运行"
    echo "   进程信息:"
    ps aux | grep "run_multiple_models.py" | grep -v grep
    echo ""
    read -p "是否继续启动新进程？(y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
fi

# 创建日志文件名（带时间戳）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="ontology_build_${TIMESTAMP}.log"

echo "📝 日志文件: $LOG_FILE"
echo ""

# 后台运行
nohup conda run -n OntologyConstruction python src/external/MOSES/test/onto_cons/run_multiple_models.py > "$LOG_FILE" 2>&1 &

PID=$!

echo "✓ 进程已启动！"
echo "  PID: $PID"
echo "  日志: $LOG_FILE"
echo ""
echo "📊 查看实时日志:"
echo "   tail -f $LOG_FILE"
echo ""
echo "🔍 查看进程状态:"
echo "   ps aux | grep run_multiple_models"
echo ""
echo "⏹️  终止进程:"
echo "   kill $PID"
echo ""
echo "=========================================="
echo "您现在可以安全地离开电脑了！"
echo "=========================================="
