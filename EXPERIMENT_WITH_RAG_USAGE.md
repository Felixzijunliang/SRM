# experiment_with_rag.py 使用说明

## 新增功能

### 1. 断点重连功能
- **自动保存进度**：每处理10条记录自动保存检查点
- **自动恢复**：程序重启后自动从上次中断处继续
- **检查点文件**：`experiment_with_rag_checkpoint.json`

### 2. 后台运行支持
- **SSH断开保护**：使用nohup确保SSH断开后程序继续运行
- **优雅退出**：收到SIGINT/SIGTERM信号时自动保存进度
- **进程管理**：自动PID文件管理，防止重复启动

### 3. GLM4自主判断RAG
- **智能决策**：GLM4根据内容复杂度自行决定是否检索知识库
- **提示词优化**：明确指导模型何时应该使用知识库
- **透明记录**：记录每次分析是否使用了RAG

## 使用方法

### 方式1：后台运行（推荐）

```bash
cd /home/turing/SRM
./run_experiment_with_rag_background.sh
```

启动后可安全断开SSH连接，实验会继续运行。

### 方式2：前台运行

```bash
cd /home/turing/SRM
python3 experiment_with_rag.py
```

适合调试或需要实时观察输出的情况。

## 监控与管理

### 查看实时日志
```bash
# 查看控制台输出
tail -f experiment_with_rag_console.log

# 查看详细日志
tail -f experiment_with_rag.log
```

### 检查进程状态
```bash
# 查看PID文件
cat experiment_with_rag.pid

# 检查进程是否运行
ps -p $(cat experiment_with_rag.pid)

# 查看进程详情
ps aux | grep experiment_with_rag.py
```

### 停止实验
```bash
# 优雅停止（推荐，会保存进度）
kill $(cat experiment_with_rag.pid)

# 强制停止（不推荐，可能丢失未保存的进度）
kill -9 $(cat experiment_with_rag.pid)
```

### 查看检查点
```bash
# 查看当前进度
cat experiment_with_rag_checkpoint.json | jq '.processed_ids | length'

# 查看检查点时间
cat experiment_with_rag_checkpoint.json | jq '.timestamp'
```

## 断点重连说明

### 工作原理
1. 程序每处理10条记录保存一次检查点
2. 检查点包含已处理记录的ID和所有结果
3. 程序启动时自动检测并加载检查点
4. 跳过已处理的记录，从中断处继续

### 手动触发断点重连
如果实验被中断（如SSH断开、系统重启等）：

```bash
# 直接重新运行脚本即可
./run_experiment_with_rag_background.sh

# 或前台运行
python3 experiment_with_rag.py
```

程序会自动检测检查点并继续执行。

### 重新开始实验
如需从头开始新的实验：

```bash
# 删除检查点文件
rm -f experiment_with_rag_checkpoint.json

# 可选：删除旧的结果文件
rm -f results_with_rag.csv experiment_with_rag.log experiment_with_rag_console.log

# 重新运行
./run_experiment_with_rag_background.sh
```

## GLM4智能RAG使用

### 提示词改进
新的提示词指导GLM4：
1. 自行判断内容是否需要背景知识
2. 对于涉及法规、政策的内容主动检索
3. 对于情感明确的内容可直接分析
4. 在结果中说明是否使用了检索

### 查看RAG使用情况
```bash
# 统计RAG使用次数（实验完成后）
python3 -c "import pandas as pd; df = pd.read_csv('results_with_rag.csv'); print(f'RAG使用: {df[\"used_rag\"].sum()}/{len(df)}')"
```

## 输出文件说明

| 文件名 | 说明 |
|--------|------|
| `results_with_rag.csv` | 最终结果文件，包含所有预测和RAG使用情况 |
| `experiment_with_rag.log` | 详细日志，记录每条记录的处理过程 |
| `experiment_with_rag_console.log` | 控制台输出日志（后台运行时） |
| `experiment_with_rag_checkpoint.json` | 检查点文件，记录已处理记录 |
| `experiment_with_rag.pid` | 进程ID文件（后台运行时） |

## 注意事项

1. **服务依赖**：确保RAG API和LLM服务都在运行
2. **磁盘空间**：检查点和日志会占用磁盘空间
3. **网络连接**：虽然支持断点重连，但仍需确保API服务可访问
4. **并发运行**：脚本会检测并防止同时运行多个实例

## 故障排查

### 实验无法启动
```bash
# 检查服务状态
curl http://localhost:8000/health
curl http://localhost:8889/health

# 查看错误日志
tail -50 experiment_with_rag_console.log
```

### 进度未保存
- 检查是否有写入权限
- 确认磁盘空间充足
- 查看日志中的错误信息

### 检查点损坏
```bash
# 验证JSON格式
python3 -c "import json; json.load(open('experiment_with_rag_checkpoint.json'))"

# 如果损坏，删除重新开始
rm experiment_with_rag_checkpoint.json
```
