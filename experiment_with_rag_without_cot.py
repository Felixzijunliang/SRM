"""
实验2变体：使用d-rag系统的情感分析实验（无CoT版本）
用于消融实验：仅使用RAG，不使用Chain-of-Thought推理
"""

import pandas as pd
import json
import requests
import time
import signal
import sys
import os
from datetime import datetime
from tqdm import tqdm

# 配置
LLM_SERVICE_URL = "http://localhost:8889/chat"
RAG_API_URL = "http://localhost:8000"

# 提示词文件和数据文件
PROMPT_FILE = "prompt.txt"
DATA_FILE = "data4.csv"
OUTPUT_FILE = "results_with_rag_without_cot.csv"
LOG_FILE = "experiment_with_rag_without_cot.log"
CHECKPOINT_FILE = "experiment_with_rag_without_cot_checkpoint.json"
CONSOLE_LOG_FILE = "experiment_with_rag_without_cot_console.log"

# ============ 断点续传配置 ============
START_INDEX = 0
SAVE_INTERVAL = 10
CONSECUTIVE_ZERO_THRESHOLD = 5
CONSECUTIVE_ERROR_THRESHOLD = 3
# ============ API重试配置 ============
API_RETRY_INTERVAL = 30
API_MAX_WAIT_TIME = 180

# RAG增强提示词 - 无CoT版本：去掉分析过程要求
RAG_ENHANCEMENT = """
### 【核心指令】RAG 知识库辅助原则
你是一个专业的金融情感分析师。你拥有调用知识库检索背景信息的能力。在使用检索内容时，必须严格遵守以下 **"新闻主体优先"** 逻辑：

1. **绝对优先级原则 (News First)**：
   - 情感判断必须以**【当前新闻文本】**所述的最新事实为唯一核心依据。
   - 检索到的 RAG 信息仅作为**辅助参考**（用于解释术语、确认实体）。
   - **红线**：严禁因为检索到了该公司的"历史负面记录"或"通用行业风险"，而否定当前新闻中明确的"利好事实"（如营收增长、中标、获批）。

2. **"泼冷水"防御机制 (Positive Protection)**：
   当新闻倾向为 **Positive**，但检索内容包含负面信息时，执行以下**冲突仲裁**：
   - **情形 A (忽略)**：如果检索内容是**过往历史**（如 3 年前的违规）、**通用风险提示**（如"股市有风险"）、或**与当前事件无关的诉讼**，请**完全忽略**该检索信息，保持 Positive 判断。
   - **情形 B (采纳)**：只有当检索内容**直接证伪**了当前新闻（例如：新闻说"获批"，检索说"官方刚刚辟谣已驳回"），才允许转为 Negative。
   - **情形 C (中性陷阱)**：不要因为"背景复杂"就安全地选择"中性"。如果新闻本身是好消息，且无实质性反转证据，必须坚定判为 Positive。

3. **按需检索与噪声过滤**：
   - 如果新闻本身情感色彩强烈且事实清晰（如"净利润翻倍"），**请勿依赖检索内容进行二次解读**。
   - 检索到的法律法规若未直接指控当前行为违规，视为**背景噪声**，不计入情感打分。

### 输出要求
请严格按照主prompt要求的JSON格式输出，简要说明判断依据即可，无需展开详细的逐步推理分析。
"""

# 全局变量用于优雅退出
shutdown_flag = False
log_file_handle = None


def signal_handler(signum, frame):
    """信号处理函数，用于优雅退出"""
    global shutdown_flag
    print(f"\n接收到信号 {signum}，正在保存进度并退出...")
    log_message(f"\n接收到信号 {signum}，正在保存进度并退出...")
    shutdown_flag = True


def log_message(message):
    """同时输出到控制台和日志文件"""
    print(message)
    if log_file_handle:
        log_file_handle.write(message + "\n")
        log_file_handle.flush()


class NumpyEncoder(json.JSONEncoder):
    """处理numpy类型的JSON编码器"""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            if np.isnan(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif obj != obj:  # NaN check
            return None
        return super().default(obj)


def save_checkpoint(processed_ids, results):
    """保存检查点"""
    checkpoint_data = {
        'processed_ids': list(processed_ids),
        'results': results,
        'timestamp': datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
    log_message(f"检查点已保存: {len(processed_ids)} 条记录")


def load_checkpoint():
    """加载检查点"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            log_message(f"发现检查点文件，已处理 {len(checkpoint_data['processed_ids'])} 条记录")
            log_message(f"检查点时间: {checkpoint_data['timestamp']}")
            return set(checkpoint_data['processed_ids']), checkpoint_data['results']
        except Exception as e:
            log_message(f"加载检查点失败: {e}，从头开始")
            return set(), []
    return set(), []


def fix_json_string(text):
    """修复LLM返回的JSON格式错误"""
    import re
    if not text:
        return text

    # 替换中文标点
    text = text.replace('，', ',').replace('：', ':')
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    # 修复缺少逗号的情况
    text = re.sub(r'("\s*)\n(\s*")', r'\1,\n\2', text)
    text = re.sub(r'(\d+\.?\d*|true|false|null)\s*\n(\s*")', r'\1,\n\2', text)
    text = re.sub(r'(\})\s*\n(\s*")', r'\1,\n\2', text)

    # 移除多余的尾部逗号
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    return text


MAX_TEXT_LENGTH = 4000  # 文本最大长度限制

def call_llm_with_rag(text, prompt_template):
    """调用LLM服务（带RAG，无CoT）进行情感分析"""
    # 截断过长文本
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "..."

    # 构造查询 - 结合RAG增强（无CoT）
    query = f"""{prompt_template.replace('{text}', text)}

{RAG_ENHANCEMENT}"""

    try:
        response = requests.post(
            LLM_SERVICE_URL,
            json={
                "query": query,
                "use_rag": True,
                "top_k": 2,
                "score_threshold": 0.7,
                "max_tokens_round1": 200,
                "max_tokens_round2": 300,
                "temperature_round1": 0.0,
                "temperature_round2": 0.0
            },
            timeout=180
        )

        if response.status_code == 200:
            result = response.json()
            if not result.get('success'):
                return {"success": False, "error": "LLM服务返回失败", "predicted_label": 0}

            answer = result.get('answer', '')
            used_tool = result.get('used_tool', False)
            top_sources = result.get('top_sources', [])
            retrieved_count = result.get('retrieved_count', 0)

            # 解析JSON响应
            json_start = answer.find('{')
            json_end = answer.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = answer[json_start:json_end]

                # 尝试解析，失败则修复后重试
                try:
                    parsed_result = json.loads(json_str)
                except json.JSONDecodeError:
                    # 尝试修复JSON
                    fixed_json = fix_json_string(json_str)
                    try:
                        parsed_result = json.loads(fixed_json)
                        log_message(f"JSON修复成功")
                    except json.JSONDecodeError as e:
                        # JSON解析失败，标记为解析错误（不重试）
                        return {"success": False, "error": f"JSON解析失败: {str(e)}", "raw_output": answer, "predicted_label": 0}

                sentiment_map = {"积极": 1, "positive": 1, "消极": -1, "negative": -1, "中性": 0, "neutral": 0}
                predicted_sentiment = parsed_result.get('predicted_sentiment', '中性')
                predicted_label = sentiment_map.get(predicted_sentiment.lower(), 0)

                return {
                    "success": True,
                    "predicted_label": predicted_label,
                    "predicted_sentiment": predicted_sentiment,
                    "sentiment_scores": parsed_result.get('sentiment_scores', {}),
                    "reason": parsed_result.get('reason', ''),
                    "raw_output": answer,
                    "used_rag": used_tool,
                    "retrieved_count": retrieved_count,
                    "top_sources": top_sources
                }
            else:
                return {"success": False, "error": "无法找到JSON格式", "raw_output": answer, "predicted_label": 0}
        else:
            return {"success": False, "error": f"API调用失败: {response.status_code}", "predicted_label": 0}

    except requests.exceptions.RequestException as e:
        # 网络/连接错误，可以重试
        return {"success": False, "error": f"网络异常: {str(e)}", "predicted_label": 0}
    except Exception as e:
        # 其他错误，不重试
        return {"success": False, "error": f"处理异常: {str(e)}", "predicted_label": 0}


def check_services():
    """检查服务是否正常运行"""
    log_message("检查服务状态...")
    try:
        response = requests.get(f"{RAG_API_URL}/health", timeout=5)
        log_message(f"✓ RAG API 正常运行" if response.status_code == 200 else f"✗ RAG API 状态异常")
    except:
        log_message(f"✗ RAG API 无法连接，请启动: cd /home/turing/d-rag && python rag_api.py")
        return False

    try:
        response = requests.get("http://localhost:8889/health", timeout=5)
        log_message(f"✓ LLM服务 正常运行" if response.status_code == 200 else f"✗ LLM服务 状态异常")
    except:
        log_message(f"✗ LLM服务 无法连接，请启动: cd /home/turing/d-rag && python llm_service.py")
        return False
    return True


def wait_for_api_recovery():
    """等待API恢复，返回True表示恢复成功，False表示超时"""
    log_message(f"\nAPI调用失败，等待恢复中... (最长等待{API_MAX_WAIT_TIME}秒)")
    wait_start = time.time()

    while time.time() - wait_start < API_MAX_WAIT_TIME:
        # 检查是否需要退出
        if shutdown_flag:
            return False

        time.sleep(API_RETRY_INTERVAL)
        elapsed = int(time.time() - wait_start)
        log_message(f"已等待 {elapsed}秒，检查API状态...")

        try:
            response = requests.get("http://localhost:8889/health", timeout=5)
            if response.status_code == 200:
                log_message("✓ API已恢复，继续处理...")
                return True
        except:
            log_message(f"API仍不可用，继续等待...")

    log_message(f"等待超时({API_MAX_WAIT_TIME}秒)，API未恢复")
    return False


def run_experiment():
    """运行实验（支持断点重连、定期保存、断连检测）"""
    global log_file_handle, shutdown_flag

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log_message("=" * 80)
    log_message("实验2变体：使用d-rag系统的情感分析（无CoT版本 - 消融实验）")
    log_message("=" * 80)

    if not check_services():
        return

    # 加载提示词和数据
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    df = pd.read_csv(DATA_FILE)
    log_message(f"\n数据集大小: {len(df)} 条")
    log_message(f"标签分布:\n{df['label'].value_counts()}")

    # 加载已有结果（如果存在）- 自动从断点恢复
    existing_results = []
    processed_ids = set()

    # 优先从检查点恢复
    if os.path.exists(CHECKPOINT_FILE):
        processed_ids, existing_results = load_checkpoint()
    # 否则从results文件恢复
    elif os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            # 转换numpy类型为Python原生类型
            for col in existing_df.columns:
                if existing_df[col].dtype == 'int64':
                    existing_df[col] = existing_df[col].astype(object).where(existing_df[col].notna(), None)
                elif existing_df[col].dtype == 'float64':
                    existing_df[col] = existing_df[col].astype(object).where(existing_df[col].notna(), None)
            existing_results = existing_df.to_dict('records')
            # 确保所有值都是Python原生类型
            for r in existing_results:
                for k, v in list(r.items()):
                    if hasattr(v, 'item'):
                        r[k] = v.item()
                    elif v != v:  # NaN
                        r[k] = None
            processed_ids = set(r['text_id'] for r in existing_results)
            log_message(f"\n从结果文件恢复: {len(existing_results)} 条已处理")
        except Exception as e:
            log_message(f"读取结果文件失败: {e}，从头开始")

    results = existing_results.copy()
    if not processed_ids:
        processed_ids = set(r['text_id'] for r in results)

    # 打开日志文件（追加模式）
    log_file_handle = open(LOG_FILE, 'a', encoding='utf-8')
    log_file_handle.write(f"\n{'='*80}\n")
    log_file_handle.write(f"继续实验（无CoT版本）: {datetime.now()}\n")
    log_file_handle.write(f"从索引 {START_INDEX} 开始处理\n")
    log_file_handle.write(f"{'='*80}\n\n")

    start_time = time.time()
    processed_count = 0
    consecutive_zeros = 0  # 连续预测为0的计数
    consecutive_errors = 0  # 连续API错误计数
    glm4_disconnected = False  # GLM4断连标志

    # 从START_INDEX开始处理
    total_to_process = len(df) - START_INDEX
    log_message(f"\n从索引 {START_INDEX} 开始，共需处理 {total_to_process} 条")

    for idx in tqdm(range(START_INDEX, len(df)), desc="处理进度", initial=0, total=total_to_process):
        # 检查是否需要退出
        if shutdown_flag:
            log_message("\n接收到退出信号，正在保存结果...")
            break

        # 检查GLM4是否断连
        if glm4_disconnected:
            log_message("\n检测到GLM4断连，停止处理并保存结果...")
            break

        row = df.iloc[idx]

        # 跳过已处理的记录
        if row['text_id'] in processed_ids:
            continue

        # 调用API，失败时重试
        result = call_llm_with_rag(row['text'], prompt_template)
        retry_count = 0
        max_retries = 3

        # 重试逻辑
        while not result['success'] and retry_count < max_retries:
            error_msg = result.get('error', '')
            retry_count += 1

            if 'JSON解析失败' in error_msg or '无法找到JSON' in error_msg:
                # JSON格式错误，直接重试
                log_message(f"\n[{idx+1}] JSON格式错误，重试 {retry_count}/{max_retries}...")
                time.sleep(1)
                result = call_llm_with_rag(row['text'], prompt_template)
            elif '网络异常' in error_msg or 'API调用失败' in error_msg:
                # 网络错误，保存进度并退出
                log_message(f"\n[{idx+1}] 网络错误: {error_msg}")
                log_message(f"保存进度并退出，下次从第 {idx+1} 条继续...")
                save_results(results)
                save_checkpoint(processed_ids, results)
                log_file_handle.close()
                sys.exit(1)
            else:
                break

        # 如果因等待超时而断连，跳出主循环
        if glm4_disconnected:
            break

        result_record = {
            'text_id': row['text_id'],
            'text': row['text'],
            'true_label': row['label'],
            'predicted_label': result['predicted_label'],
            'success': result['success'],
            'predicted_sentiment': result.get('predicted_sentiment', ''),
            'reason': result.get('reason', ''),
            'used_rag': result.get('used_rag', False),
            'retrieved_count': result.get('retrieved_count', 0),
            'top_sources': json.dumps(result.get('top_sources', []), ensure_ascii=False),
            'error': result.get('error', '')
        }
        results.append(result_record)
        processed_ids.add(row['text_id'])
        processed_count += 1

        # 日志
        log_file_handle.write(f"[{idx+1}] {row['text_id']} | 真实:{row['label']} 预测:{result['predicted_label']}\n")
        if result['success']:
            log_file_handle.write(f"RAG:{result.get('used_rag')} 检索:{result.get('retrieved_count', 0)}篇\n")
        else:
            log_file_handle.write(f"错误:{result.get('error', 'unknown')}\n")
        log_file_handle.write("-"*80 + "\n")
        log_file_handle.flush()

        # ============ 断连检测逻辑 ============
        # 检测API错误
        if not result['success'] and 'API调用失败' in result.get('error', ''):
            consecutive_errors += 1
            log_message(f"\n警告: API错误 ({consecutive_errors}/{CONSECUTIVE_ERROR_THRESHOLD})")
            if consecutive_errors >= CONSECUTIVE_ERROR_THRESHOLD:
                log_message(f"\n严重: 连续{CONSECUTIVE_ERROR_THRESHOLD}次API错误，判断GLM4断连!")
                glm4_disconnected = True
        else:
            consecutive_errors = 0

        # 检测连续预测为0（可能是模型异常）
        if result['predicted_label'] == 0 and row['label'] != 0:
            consecutive_zeros += 1
            if consecutive_zeros >= CONSECUTIVE_ZERO_THRESHOLD:
                log_message(f"\n警告: 连续{consecutive_zeros}条非中性样本预测为0，可能GLM4异常")
        else:
            consecutive_zeros = 0

        # ============ 定期保存结果 ============
        if processed_count % SAVE_INTERVAL == 0:
            save_results(results)
            log_message(f"已保存 {len(results)} 条结果 (本次处理 {processed_count} 条)")

        time.sleep(0.5)

    elapsed_time = time.time() - start_time

    # 保存最终结果
    save_results(results)

    # 统计
    results_df = pd.DataFrame(results)
    success_count = results_df['success'].sum()
    rag_used = results_df['used_rag'].sum() if 'used_rag' in results_df.columns else 0

    success_df = results_df[results_df['success']]
    if len(success_df) > 0:
        accuracy = (success_df['predicted_label'] == success_df['true_label']).mean()
    else:
        accuracy = 0

    log_message(f"\n{'='*80}")
    log_message(f"实验{'中断' if (shutdown_flag or glm4_disconnected) else '完成'}！耗时: {elapsed_time:.2f}秒")
    log_message(f"本次处理: {processed_count} 条")
    log_message(f"总结果数: {len(results)} 条")
    log_message(f"成功: {success_count}/{len(results)} | RAG使用: {rag_used}/{len(results)} | 准确率: {accuracy*100:.2f}%")
    log_message(f"结果已保存: {OUTPUT_FILE}")

    if glm4_disconnected:
        log_message(f"\n!!! GLM4断连，下次运行请设置 START_INDEX = {len(results)} !!!")

    log_file_handle.write(f"\n{'='*80}\n")
    log_file_handle.write(f"完成: {datetime.now()}\n耗时:{elapsed_time:.2f}s\n准确率:{accuracy*100:.2f}%\n")
    log_file_handle.write(f"总结果数: {len(results)}\n")
    log_file_handle.close()


def save_results(results):
    """保存结果到CSV文件"""
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')


if __name__ == "__main__":
    run_experiment()
