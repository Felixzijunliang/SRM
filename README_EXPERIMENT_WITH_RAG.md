# 带RAG的情感分析实验 - 快速开始

## 🚀 快速开始

### 一键启动（后台运行）
```bash
cd /home/turing/SRM
./run_experiment_with_rag_background.sh
```

实验将在后台运行，即使SSH断开也会继续执行。

### 查看运行状态
```bash
# 查看实时输出
tail -f experiment_with_rag_console.log

# 查看详细日志
tail -f experiment_with_rag.log

# 检查进程
ps -p $(cat experiment_with_rag.pid)
```

## ✨ 新功能特性

### 1. 断点重连 🔄
- ✅ 每10条记录自动保存进度
- ✅ 意外中断后自动恢复
- ✅ 无需担心进度丢失

### 2. 后台运行 🌙
- ✅ SSH断开后继续运行
- ✅ 优雅的进程管理
- ✅ 完整的日志记录

### 3. 智能RAG 🧠
- ✅ GLM4自主判断是否需要检索
- ✅ 根据内容复杂度智能决策
- ✅ 记录RAG使用情况

## 📋 常用命令

### 监控
```bash
# 查看当前进度
cat experiment_with_rag_checkpoint.json | jq '.processed_ids | length'

# 查看最后10行日志
tail -10 experiment_with_rag.log
```

### 控制
```bash
# 停止实验（保存进度）
kill $(cat experiment_with_rag.pid)

# 查看进程状态
ps aux | grep experiment_with_rag.py
```

### 重启/继续
```bash
# 从断点继续（自动检测）
./run_experiment_with_rag_background.sh

# 完全重新开始
rm -f experiment_with_rag_checkpoint.json
./run_experiment_with_rag_background.sh
```

## 📁 文件说明

| 文件 | 用途 |
|------|------|
| `experiment_with_rag.py` | 主程序（已升级） |
| `run_experiment_with_rag_background.sh` | 后台启动脚本 |
| `results_with_rag.csv` | 实验结果 |
| `experiment_with_rag.log` | 详细日志 |
| `experiment_with_rag_console.log` | 控制台输出 |
| `experiment_with_rag_checkpoint.json` | 进度检查点 |
| `experiment_with_rag.pid` | 进程ID |

## 📖 详细文档

- **使用指南**：`EXPERIMENT_WITH_RAG_USAGE.md` - 完整的使用说明
- **改动说明**：`CHANGES_SUMMARY.md` - 技术改进详情

## ⚠️ 前置要求

确保以下服务正在运行：
```bash
# RAG API服务
curl http://localhost:8000/health

# LLM服务
curl http://localhost:8889/health
```

如果服务未运行，请先启动：
```bash
# 启动RAG API
cd /home/turing/d-rag && python rag_api.py &

# 启动LLM服务
cd /home/turing/d-rag && python llm_service.py &
```

## 🆘 常见问题

### Q: 如何知道实验是否在运行？
```bash
ps -p $(cat experiment_with_rag.pid) && echo "运行中" || echo "已停止"
```

### Q: 如何查看已处理多少条记录？
```bash
cat experiment_with_rag_checkpoint.json | jq '.processed_ids | length'
```

### Q: 实验中断了怎么办？
直接重新运行启动脚本，会自动从断点继续：
```bash
./run_experiment_with_rag_background.sh
```

### Q: 如何停止实验？
```bash
kill $(cat experiment_with_rag.pid)
```
程序会自动保存进度后退出。

### Q: 如何查看GLM4使用RAG的情况？
```bash
# 实验完成后查看
python3 -c "import pandas as pd; df = pd.read_csv('results_with_rag.csv'); print(f'总计: {len(df)} 条, RAG使用: {df[\"used_rag\"].sum()} 次')"
```

## 💡 使用技巧

### 1. 实时监控进度
```bash
# 在一个终端查看日志
tail -f experiment_with_rag_console.log

# 在另一个终端查看进度
watch -n 5 'cat experiment_with_rag_checkpoint.json | jq ".processed_ids | length"'
```

### 2. 性能调优
编辑 `experiment_with_rag.py` 调整：
- `checkpoint_interval`：检查点保存频率（第203行）
- `time.sleep(0.5)`：请求间隔时间（第247行）

### 3. 日志分析
```bash
# 统计成功率
grep "真实:" experiment_with_rag.log | wc -l

# 查看错误
grep "error" experiment_with_rag.log

# 查看RAG使用
grep "RAG:True" experiment_with_rag.log | wc -l
```

## 🎯 最佳实践

1. **首次运行**：先小批量测试，确认服务正常
2. **长期运行**：使用后台模式，定期检查日志
3. **故障恢复**：保留检查点文件，可随时恢复
4. **结果分析**：实验完成后详细分析RAG使用情况

## 📞 技术支持

遇到问题请查看：
1. 控制台日志：`experiment_with_rag_console.log`
2. 详细日志：`experiment_with_rag.log`
3. 服务状态：检查RAG API和LLM服务是否运行
4. 磁盘空间：确保有足够空间保存检查点和日志

---

**版本**：v2.0 (支持断点重连和后台运行)
**更新时间**：2025-11-23
