#!/bin/bash

echo "=========================================="
echo "情感分析实验 - 对比RAG效果"
echo "=========================================="

# 检查Python环境
echo -e "\n检查Python环境..."
python3 --version

# 安装依赖
echo -e "\n安装依赖..."
pip3 install -r requirements.txt -q

# 实验1：不使用RAG
echo -e "\n=========================================="
echo "实验1：不使用RAG的情感分析"
echo "=========================================="
python3 experiment_no_rag.py

# 等待一下
sleep 5

# 检查d-rag服务是否运行
echo -e "\n检查d-rag服务状态..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "警告: RAG API未运行，请先启动:"
    echo "  cd /home/turing/d-rag && python3 rag_api.py &"
    echo ""
    echo "等待RAG API启动..."
    echo "请在另一个终端运行上述命令后按任意键继续..."
    read -n 1
fi

if ! curl -s http://localhost:8889/health > /dev/null; then
    echo "警告: LLM服务未运行，请先启动:"
    echo "  cd /home/turing/d-rag && python3 llm_service.py &"
    echo ""
    echo "等待LLM服务启动..."
    echo "请在另一个终端运行上述命令后按任意键继续..."
    read -n 1
fi

# 实验2：使用RAG
echo -e "\n=========================================="
echo "实验2：使用d-rag系统的情感分析"
echo "=========================================="
python3 experiment_with_rag.py

# 评估和可视化
echo -e "\n=========================================="
echo "评估和可视化结果"
echo "=========================================="
python3 evaluate_results.py

echo -e "\n=========================================="
echo "所有实验完成！"
echo "=========================================="
echo "查看结果:"
echo "  - 不使用RAG: results_no_rag.csv"
echo "  - 使用RAG: results_with_rag.csv"
echo "  - 评估报告: evaluation_results/"
echo "=========================================="
