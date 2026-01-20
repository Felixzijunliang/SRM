# 快速启动指南

## 🚀 一键运行（推荐）

```bash
cd /home/turing/SRM
./run_all_experiments.sh
```

## 📋 分步运行

### 1️⃣ 准备环境
```bash
cd /home/turing/SRM
pip3 install -r requirements.txt
```

### 2️⃣ 实验1：不使用RAG（约10-20分钟）
```bash
python3 experiment_no_rag.py
```
✅ 生成文件：`results_no_rag.csv`, `experiment_no_rag.log`

### 3️⃣ 启动d-rag服务

**打开新终端1 - 启动RAG API：**
```bash
cd /home/turing/d-rag
python3 rag_api.py
```

**打开新终端2 - 启动LLM服务：**
```bash
cd /home/turing/d-rag
python3 llm_service.py
```

**验证服务运行：**
```bash
# 检查RAG API
curl http://localhost:8000/health

# 检查LLM服务
curl http://localhost:8889/health
```

### 4️⃣ 实验2：使用d-rag（约15-30分钟）
```bash
python3 experiment_with_rag.py
```
✅ 生成文件：`results_with_rag.csv`, `experiment_with_rag.log`

### 5️⃣ 评估和可视化
```bash
python3 evaluate_results.py
```
✅ 生成目录：`evaluation_results/`
- 📊 混淆矩阵对比图
- 📊 性能指标对比图
- 📊 各类别F1分数对比图
- 📄 详细评估报告

## 📊 查看结果

```bash
# 查看评估报告
cat evaluation_results/evaluation_report.txt

# 查看图表（需要图形界面）
ls evaluation_results/*.png

# 查看指标数据
cat evaluation_results/metrics.json
```

## 🔍 实验对比内容

| 维度 | 实验1 | 实验2 |
|------|-------|-------|
| **方法** | 直接调用LLM | 使用d-rag系统 |
| **提示词** | 标准情感分析prompt | 标准prompt + RAG增强 |
| **知识库** | ❌ 不使用 | ✅ 金融法规知识库 |
| **返回信息** | LLM回答 | LLM回答 + Top3知识源 |

## 📈 评估指标

- ✅ 准确率 (Accuracy)
- ✅ 精确率 (Precision - 宏平均/加权)
- ✅ 召回率 (Recall - 宏平均/加权)
- ✅ F1分数 (F1 Score - 宏平均/加权)
- ✅ 各类别详细指标（积极/消极/中性）
- ✅ 混淆矩阵可视化

## ⚠️ 注意事项

1. **远程LLM服务**必须可访问：`http://104.224.158.247:8007`
2. **d-rag服务**必须在实验2前启动
3. 完整实验耗时约**30-50分钟**（取决于数据集大小）
4. 确保有足够磁盘空间存储日志和结果

## 🐛 常见问题

### Q1: 如何检查LLM API连接？
```bash
curl http://104.224.158.247:8007/v1/models
```

### Q2: d-rag服务启动失败？
```bash
# 检查端口占用
netstat -tuln | grep 8000
netstat -tuln | grep 8889

# 查看d-rag日志
cd /home/turing/d-rag
tail -f logs/*.log
```

### Q3: 中文图表显示乱码？
安装中文字体：
```bash
sudo apt-get install fonts-wqy-zenhei
```

## 📁 文件说明

```
SRM/
├── 📄 prompt.txt                 - 情感分析提示词
├── 📊 data4.csv                  - 实验数据集（20条样本）
├── 🐍 experiment_no_rag.py       - 实验1脚本
├── 🐍 experiment_with_rag.py     - 实验2脚本
├── 📊 evaluate_results.py        - 评估可视化脚本
├── 📦 requirements.txt           - Python依赖
├── 🚀 run_all_experiments.sh     - 一键运行脚本
├── 📖 README.md                  - 详细说明文档
└── 📖 QUICKSTART.md              - 本快速指南
```

## 🎯 预期输出

运行成功后，你将得到：

1. **CSV结果文件**
   - `results_no_rag.csv` - 实验1的预测结果
   - `results_with_rag.csv` - 实验2的预测结果（含RAG信息）

2. **日志文件**
   - `experiment_no_rag.log` - 实验1的详细日志
   - `experiment_with_rag.log` - 实验2的详细日志

3. **评估结果** (`evaluation_results/`)
   - `confusion_matrices.png` - 混淆矩阵可视化
   - `metrics_comparison.png` - 指标对比柱状图
   - `per_class_f1.png` - 各类别F1对比
   - `evaluation_report.txt` - 完整评估报告
   - `metrics.json` - 指标数据（JSON格式）

## 💡 下一步

完成实验后，你可以：

1. 📊 分析 `evaluation_report.txt` 查看d-rag的提升效果
2. 🔍 检查 `experiment_with_rag.log` 查看RAG检索的知识源
3. 📈 对比两个实验的混淆矩阵，分析错误类型
4. 🎨 自定义可视化参数，生成更多图表
5. 📝 根据结果撰写实验报告

Good luck! 🎉
