# experiment_with_rag.py 改进总结

## 改动概述
对 `experiment_with_rag.py` 进行了三大改进，使其更加健壮和易用。

## 1. 断点重连功能 ✅

### 新增函数
- `save_checkpoint(processed_ids, results)` - 保存实验进度
- `load_checkpoint()` - 加载并恢复实验进度

### 关键特性
- **自动检查点保存**：每处理10条记录自动保存
- **智能恢复**：程序重启时自动检测并从断点继续
- **进度跟踪**：使用 `processed_ids` 集合跟踪已处理记录
- **数据完整性**：保存所有已处理结果，避免重复计算

### 检查点文件
- 文件名：`experiment_with_rag_checkpoint.json`
- 内容：已处理ID列表、所有结果、时间戳
- 实验完成后自动清理

## 2. 后台运行支持 ✅

### 代码改进
- **信号处理**：注册 SIGINT 和 SIGTERM 处理器
- **优雅退出**：收到中断信号时保存进度
- **统一日志**：新增 `log_message()` 函数统一输出
- **日志持久化**：所有输出同时写入文件和控制台

### 新增文件
- **启动脚本**：`run_experiment_with_rag_background.sh`
  - 使用 nohup 在后台运行
  - PID 文件管理，防止重复启动
  - 完整的监控和管理命令提示

### 全局变量
- `shutdown_flag` - 优雅退出标志
- `log_file_handle` - 日志文件句柄

## 3. GLM4智能RAG判断 ✅

### 提示词改进
修改了 `RAG_ENHANCEMENT` 提示词，现在包含：

```
【重要指令】在进行情感分析时，你需要自行判断是否需要检索知识库：
1. 如果新闻内容涉及特定的法规、政策、专业术语或需要背景知识才能准确判断情感倾向，你应该主动检索知识库获取相关信息
2. 如果新闻内容的情感倾向已经很明确，不需要额外的背景知识，可以直接进行分析
3. 请在分析过程中明确说明你是否使用了知识库检索，以及检索的原因
```

### 工作机制
- LLM 自主决定是否需要检索知识库
- 保持 `use_rag=True` 参数（工具可用）
- 通过提示词引导模型智能选择
- 结果中记录实际RAG使用情况

## 新增文件列表

1. **run_experiment_with_rag_background.sh** - 后台运行启动脚本
   - 进程管理
   - PID 文件维护
   - 完整的使用说明

2. **EXPERIMENT_WITH_RAG_USAGE.md** - 详细使用文档
   - 功能说明
   - 使用方法
   - 监控命令
   - 故障排查

3. **CHANGES_SUMMARY.md** - 本文件，改动总结

4. **experiment_with_rag_checkpoint.json** - 运行时生成
   - 实验进度检查点
   - 自动创建和清理

5. **experiment_with_rag.pid** - 运行时生成
   - 后台进程PID
   - 用于进程管理

## 修改文件

### experiment_with_rag.py
- **新增导入**：`signal`, `sys`, `os`
- **新增配置**：检查点文件、控制台日志文件
- **新增函数**：
  - `signal_handler()` - 信号处理
  - `log_message()` - 统一日志
  - `save_checkpoint()` - 保存进度
  - `load_checkpoint()` - 加载进度
- **修改函数**：
  - `check_services()` - 使用统一日志
  - `run_experiment()` - 集成断点重连和优雅退出
- **修改提示词**：`RAG_ENHANCEMENT` - 让GLM4自主判断

## 使用示例

### 启动后台实验
```bash
cd /home/turing/SRM
./run_experiment_with_rag_background.sh
```

### 查看运行状态
```bash
# 实时日志
tail -f experiment_with_rag_console.log

# 进程状态
ps -p $(cat experiment_with_rag.pid)

# 当前进度
cat experiment_with_rag_checkpoint.json | jq '.processed_ids | length'
```

### 停止实验
```bash
# 优雅停止（保存进度）
kill $(cat experiment_with_rag.pid)
```

### 断点重连
```bash
# 直接重新运行即可自动从断点继续
./run_experiment_with_rag_background.sh
```

## 技术细节

### 断点重连机制
1. 使用 `text_id` 作为唯一标识
2. `processed_ids` 集合快速查找已处理记录
3. 追加模式打开日志文件保留历史
4. tqdm 进度条支持 `initial` 参数显示正确进度

### 优雅退出机制
1. 注册 SIGINT (Ctrl+C) 和 SIGTERM 信号
2. 设置 `shutdown_flag` 标志
3. 主循环检查标志并保存检查点
4. 确保数据不丢失

### 日志系统
- **控制台日志**：实时输出，后台运行时重定向
- **详细日志**：记录每条处理结果
- **检查点日志**：记录保存进度信息
- 所有日志支持追加模式

## 兼容性

### 向后兼容
- 所有原有功能保持不变
- 可以不使用新功能，按原方式运行
- 检查点文件可选，不影响正常运行

### 依赖要求
- Python 3.6+
- 所有原有依赖包
- Linux/Unix 环境（信号处理）
- bash（运行启动脚本）

## 测试建议

### 功能测试
1. **正常运行**：完整运行实验
2. **断点重连**：中途中断后重启
3. **后台运行**：SSH 断开后继续
4. **优雅退出**：Ctrl+C 或 kill 后检查进度保存

### 压力测试
1. **大数据集**：测试长时间运行
2. **频繁中断**：多次中断和重连
3. **并发检测**：尝试启动多个实例

## 已知限制

1. **单实例运行**：同时只能运行一个实验
2. **Linux限制**：信号处理在Windows上可能不同
3. **磁盘依赖**：需要足够的磁盘空间保存检查点

## 未来改进方向

- [ ] 支持并行处理多个数据集
- [ ] 添加实验暂停/恢复命令
- [ ] Web界面实时监控
- [ ] 自动重试失败的记录
- [ ] 更细粒度的RAG控制选项
