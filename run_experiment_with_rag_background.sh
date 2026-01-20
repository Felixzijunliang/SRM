#!/bin/bash
# 后台运行 experiment_with_rag.py，支持断点重连和自动重启
# 使用方法: ./run_experiment_with_rag_background.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="experiment_with_rag_console.log"
PID_FILE="experiment_with_rag.pid"
RESTART_DELAY=10  # 重启前等待秒数

echo "================================================"
echo "启动带RAG的情感分析实验（后台模式+自动重启）"
echo "================================================"

# 检查是否已有进程在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "错误: 实验已在运行中 (PID: $OLD_PID)"
        echo "如需停止，请运行: kill $OLD_PID"
        exit 1
    else
        echo "清理旧的PID文件..."
        rm -f "$PID_FILE"
    fi
fi

# 自动重启循环
run_experiment() {
    while true; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动实验..."
        python3 experiment_with_rag.py 2>&1 | tee -a "$LOG_FILE"
        EXIT_CODE=$?

        # 检查是否正常完成（退出码0表示完成）
        if [ $EXIT_CODE -eq 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 实验完成!"
            break
        fi

        # 检查是否是用户手动停止（SIGTERM=143, SIGINT=130）
        if [ $EXIT_CODE -eq 143 ] || [ $EXIT_CODE -eq 130 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 用户停止实验"
            break
        fi

        # 其他退出码，等待后重启
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 实验退出(代码:$EXIT_CODE)，${RESTART_DELAY}秒后自动重启..."
        sleep $RESTART_DELAY
    done
}

# 后台启动
echo "启动实验进程（自动重启模式）..."
nohup bash -c "$(declare -f run_experiment); run_experiment" > /dev/null 2>&1 &
PID=$!

# 保存PID
echo $PID > "$PID_FILE"

echo "✓ 实验已在后台启动"
echo "  进程ID: $PID"
echo "  控制台日志: $LOG_FILE"
echo "  详细日志: experiment_with_rag.log"
echo ""
echo "监控命令:"
echo "  查看实时日志: tail -f $LOG_FILE"
echo "  查看进度: tail -f experiment_with_rag.log"
echo "  检查进程: ps -p $PID"
echo "  停止实验: kill $PID"
echo ""
echo "特性:"
echo "  - 网络错误时自动保存进度并重启"
echo "  - 从断点自动恢复继续处理"
echo "  - 使用 kill 命令可完全停止"
echo "================================================"
