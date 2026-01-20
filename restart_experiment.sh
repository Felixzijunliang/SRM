#!/bin/bash
cd /home/turing/SRM

# 停止旧进程
if [ -f experiment_with_rag.pid ]; then
    OLD_PID=$(cat experiment_with_rag.pid)
    kill $OLD_PID 2>/dev/null
    echo "已停止进程: $OLD_PID"
fi

# 备份日志
cp experiment_with_rag.log experiment_with_rag.log.bak_$(date +%Y%m%d_%H%M%S)

# 重新运行
nohup python experiment_with_rag.py > experiment_with_rag_console.log 2>&1 &
echo $! > experiment_with_rag.pid
echo "实验已重启，PID: $(cat experiment_with_rag.pid)"
echo "监控命令: tail -f /home/turing/SRM/experiment_with_rag.log"
