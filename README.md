# 情感分析实验：对比d-rag系统的效果

## 实验目的

对比在情感分析任务中，使用d-rag系统和不使用RAG的性能差异，评估d-rag对准确率和F1分数等指标的提升效果。

## 实验设计

### 实验1：不使用RAG
- 直接调用部署在远程服务器的LLM (GLM-4-9B)
- 使用prompt.txt中的标准情感分析提示词
- 对data4.csv中的每条新闻进行情感分类（积极/消极/中性）

### 实验2：使用d-rag系统
- 调用本地d-rag系统（包含RAG API和LLM服务）
- 在标准提示词基础上，增加RAG增强提示词
- 系统自动检索相关知识库内容（金融法规、政策等）
- 结合检索到的背景知识进行情感分析

## 文件说明

```
SRM/
├── prompt.txt                    # 情感分析提示词模板
├── data4.csv                     # 实验数据集（新闻文本+标签）
├── requirements.txt              # Python依赖
├── run_all_experiments.sh        # 一键运行所有实验
├── experiment_no_rag.py          # 实验1脚本
├── experiment_with_rag.py        # 实验2脚本
├── evaluate_results.py           # 评估和可视化脚本
└── README.md                     # 本文档
```

## 运行步骤

### 方法1：一键运行（推荐）

```bash
cd /home/turing/SRM
./run_all_experiments.sh
```

该脚本会自动：
1. 安装依赖
2. 运行实验1（不使用RAG）
3. 检查d-rag服务状态
4. 运行实验2（使用RAG）
5. 评估和可视化结果

### 方法2：分步运行

#### 步骤1：安装依赖
```bash
cd /home/turing/SRM
pip3 install -r requirements.txt
```

#### 步骤2：运行实验1（不使用RAG）
```bash
python3 experiment_no_rag.py
```

输出：
- `results_no_rag.csv` - 实验结果
- `experiment_no_rag.log` - 详细日志

#### 步骤3：启动d-rag服务

**终端1：启动RAG API**
```bash
cd /home/turing/d-rag
python3 rag_api.py
```

**终端2：启动LLM服务**
```bash
cd /home/turing/d-rag
python3 llm_service.py
```

#### 步骤4：运行实验2（使用RAG）
```bash
cd /home/turing/SRM
python3 experiment_with_rag.py
```

输出：
- `results_with_rag.csv` - 实验结果
- `experiment_with_rag.log` - 详细日志

#### 步骤5：评估和可视化
```bash
python3 evaluate_results.py
```

输出到 `evaluation_results/` 目录：
- `confusion_matrices.png` - 混淆矩阵对比
- `metrics_comparison.png` - 性能指标对比
- `per_class_f1.png` - 各类别F1分数对比
- `evaluation_report.txt` - 详细评估报告
- `metrics.json` - 指标数据（JSON格式）

## 评估指标

实验将评估以下指标：

1. **准确率 (Accuracy)**: 正确分类的样本比例
2. **精确率 (Precision)**: 宏平均和加权平均
3. **召回率 (Recall)**: 宏平均和加权平均
4. **F1分数 (F1 Score)**: 宏平均和加权平均
5. **各类别指标**: 积极/消极/中性的单独评估
6. **混淆矩阵**: 可视化分类错误情况

## 关键修改

### llm_service.py 修改
修改了返回格式，现在返回：
- LLM的回答
- 检索到的前3篇最匹配的知识库来源
- 每个来源包含：rank、text、score、source

### RAG增强提示词
在实验2中，添加了以下增强提示：
```
在进行情感分析时，你可以参考知识库中的相关信息。
如果知识库中有与当前新闻相关的法规、政策或背景知识，请结合这些信息进行更准确的判断。

特别注意：
1. 金融监管政策对相关企业的影响
2. 行业发展趋势对市场预期的影响
3. 法规变化对企业经营的影响
```

## 数据集说明

`data4.csv` 包含以下字段：
- `text_id`: 文本ID
- `text`: 新闻文本内容
- `label`: 真实标签（-1=消极, 0=中性, 1=积极）
- `pred_*`: 其他模型的预测结果（用于对比）

## 预期结果

实验将生成完整的对比报告，包括：
- 两个实验的准确率、F1分数等指标对比
- d-rag系统相对于直接LLM的提升幅度
- 可视化图表展示性能差异
- 详细的错误分析（通过混淆矩阵）

## 注意事项

1. **LLM API**: 确保远程LLM服务 `http://104.224.158.247:8007` 可访问
2. **d-rag服务**: 实验2需要先启动RAG API和LLM服务
3. **知识库**: d-rag系统应已加载金融相关知识库
4. **时间**: 完整实验可能需要较长时间（取决于数据集大小）
5. **中文显示**: 可视化图表需要支持中文的matplotlib字体

## 问题排查

### 问题1：LLM API连接失败
```bash
# 检查网络连接
curl http://104.224.158.247:8007/v1/models
```

### 问题2：d-rag服务未启动
```bash
# 检查RAG API
curl http://localhost:8000/health

# 检查LLM服务
curl http://localhost:8889/health
```

### 问题3：中文显示乱码
```python
# 在evaluate_results.py中修改字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
```

## 联系方式

如有问题，请查看日志文件或联系实验负责人。
