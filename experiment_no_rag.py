"""
实验1：不使用RAG的情感分析实验
直接调用LLM进行情感分析
"""

import pandas as pd
import json
import re
import requests
import time
from datetime import datetime
from tqdm import tqdm
import os

# 配置
LLM_API_URL = "http://104.224.158.247:8007/v1/completions"
LLM_API_KEY = "EMPTY"
LLM_MODEL = "glm-4-9b-chat"

# 提示词文件和数据文件
PROMPT_FILE = "prompt.txt"
DATA_FILE = "data4.csv"
OUTPUT_FILE = "results_no_rag.csv"
LOG_FILE = "experiment_no_rag.log"


def load_prompt():
    """加载提示词模板"""
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    return prompt_template


def call_llm(text, prompt_template):
    """
    调用LLM进行情感分析

    Args:
        text: 新闻文本
        prompt_template: 提示词模板

    Returns:
        dict: 包含预测结果和原始响应
    """
    # 构造完整的提示词
    prompt = prompt_template.replace("{text}", text)

    # 构造请求
    full_prompt = f"[gMASK]<sop><|user|>\n{prompt}\n<|assistant|>\n"

    try:
        response = requests.post(
            LLM_API_URL,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": LLM_MODEL,
                "prompt": full_prompt,
                "max_tokens": 512,
                "temperature": 0.1,  # 低温度以获得更稳定的结果
                "stop": ["<|user|>", "<|endoftext|>"]
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            output_text = result['choices'][0]['text'].strip()

            # 解析JSON响应
            try:
                # 尝试提取JSON部分
                json_start = output_text.find('{')
                json_end = output_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = output_text[json_start:json_end]
                    # 清理所有控制字符（包括换行符、制表符等）
                    json_str = re.sub(r'[\x00-\x1f\x7f]', '', json_str)
                    parsed_result = json.loads(json_str)

                    # 映射情感标签到数字
                    sentiment_map = {
                        "积极": 1,
                        "positive": 1,
                        "消极": -1,
                        "negative": -1,
                        "中性": 0,
                        "neutral": 0
                    }

                    predicted_sentiment = parsed_result.get('predicted_sentiment', '中性')
                    predicted_label = sentiment_map.get(predicted_sentiment.lower(), 0)

                    return {
                        "success": True,
                        "predicted_label": predicted_label,
                        "predicted_sentiment": predicted_sentiment,
                        "sentiment_scores": parsed_result.get('sentiment_scores', {}),
                        "reason": parsed_result.get('reason', ''),
                        "raw_output": output_text
                    }
                else:
                    return {
                        "success": False,
                        "error": "无法找到JSON格式",
                        "raw_output": output_text,
                        "predicted_label": 0
                    }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSON解析失败: {str(e)}",
                    "raw_output": output_text,
                    "predicted_label": 0
                }
        else:
            return {
                "success": False,
                "error": f"API调用失败: {response.status_code}",
                "predicted_label": 0
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"请求异常: {str(e)}",
            "predicted_label": 0
        }


def run_experiment():
    """运行实验"""
    print("=" * 80)
    print("实验1：不使用RAG的情感分析")
    print("=" * 80)

    # 加载提示词
    print(f"\n加载提示词: {PROMPT_FILE}")
    prompt_template = load_prompt()
    print(f"提示词长度: {len(prompt_template)} 字符")

    # 加载数据
    print(f"\n加载数据集: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE)
    print(f"数据集大小: {len(df)} 条")
    print(f"标签分布:\n{df['label'].value_counts()}")

    # 检查是否有已存在的结果（断点续传）
    start_idx = 0
    results = []
    if os.path.exists(OUTPUT_FILE):
        print(f"\n发现已存在的结果文件: {OUTPUT_FILE}")
        existing_df = pd.read_csv(OUTPUT_FILE)
        results = existing_df.to_dict('records')
        start_idx = len(results)
        print(f"从第 {start_idx + 1} 条继续处理（已完成 {start_idx} 条）")

    # 记录日志
    log_mode = 'a' if os.path.exists(LOG_FILE) and start_idx > 0 else 'w'
    log_file = open(LOG_FILE, log_mode, encoding='utf-8')

    if start_idx == 0:
        log_file.write(f"实验开始时间: {datetime.now()}\n")
        log_file.write(f"数据集: {DATA_FILE}\n")
        log_file.write(f"样本数: {len(df)}\n")
        log_file.write("=" * 80 + "\n\n")
    else:
        log_file.write(f"\n继续实验时间: {datetime.now()}\n")
        log_file.write(f"从第 {start_idx + 1} 条继续\n")
        log_file.write("=" * 80 + "\n\n")

    # 逐条处理
    print(f"\n开始处理...")
    start_time = time.time()

    try:
        for idx, row in tqdm(df.iloc[start_idx:].iterrows(), total=len(df)-start_idx, desc="处理进度", initial=start_idx):
            try:
                text_id = row['text_id']
                text = row['text']
                true_label = row['label']

                # 调用LLM
                result = call_llm(text, prompt_template)

                # 记录结果
                result_record = {
                    'text_id': text_id,
                    'text': text,
                    'true_label': true_label,
                    'predicted_label': result['predicted_label'],
                    'success': result['success'],
                    'predicted_sentiment': result.get('predicted_sentiment', ''),
                    'reason': result.get('reason', ''),
                    'error': result.get('error', '')
                }

                results.append(result_record)

                # 写入日志
                log_file.write(f"[{idx+1}/{len(df)}] {text_id}\n")
                log_file.write(f"文本: {text[:100]}...\n")
                log_file.write(f"真实标签: {true_label}, 预测标签: {result['predicted_label']}\n")
                if result['success']:
                    log_file.write(f"情感: {result.get('predicted_sentiment')}\n")
                    log_file.write(f"理由: {result.get('reason', '')[:200]}...\n")
                else:
                    log_file.write(f"错误: {result.get('error')}\n")
                log_file.write("-" * 80 + "\n\n")
                log_file.flush()

                # 每处理100条保存一次结果（防止数据丢失）
                if (idx + 1) % 100 == 0:
                    temp_df = pd.DataFrame(results)
                    temp_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
                    print(f"\n进度已保存 ({idx+1}/{len(df)})")

                # 稍微延迟避免API限流
                time.sleep(0.5)

            except Exception as e:
                # 单条记录处理失败，记录错误但继续处理
                error_msg = f"处理第 {idx+1} 条数据时出错: {str(e)}"
                print(f"\n{error_msg}")
                log_file.write(f"错误: {error_msg}\n")
                log_file.write("-" * 80 + "\n\n")
                log_file.flush()

                # 记录失败的记录
                result_record = {
                    'text_id': row.get('text_id', ''),
                    'text': row.get('text', ''),
                    'true_label': row.get('label', 0),
                    'predicted_label': 0,
                    'success': False,
                    'predicted_sentiment': '',
                    'reason': '',
                    'error': error_msg
                }
                results.append(result_record)
                continue

    except KeyboardInterrupt:
        print("\n\n实验被用户中断！正在保存当前进度...")
        log_file.write(f"\n实验被中断: {datetime.now()}\n")
    except Exception as e:
        print(f"\n\n实验出现严重错误: {str(e)}")
        log_file.write(f"\n严重错误: {str(e)}\n")
    finally:
        # 确保保存结果
        if results:
            results_df = pd.DataFrame(results)
            results_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            print(f"结果已保存到: {OUTPUT_FILE}")

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\n实验完成！")
    print(f"总耗时: {elapsed_time:.2f} 秒")
    print(f"处理条数: {len(results)}")
    if len(results) > 0:
        print(f"平均每条: {elapsed_time/len(results):.2f} 秒")

    print(f"结果已保存到: {OUTPUT_FILE}")
    print(f"日志已保存到: {LOG_FILE}")

    # 计算初步统计
    if results:
        results_df = pd.DataFrame(results)
        success_count = results_df['success'].sum()
        if success_count > 0:
            accuracy = (results_df[results_df['success']]['predicted_label'] ==
                        results_df[results_df['success']]['true_label']).mean()

            print(f"\n初步统计:")
            print(f"成功处理: {success_count}/{len(results)} ({success_count/len(results)*100:.2f}%)")
            print(f"准确率: {accuracy*100:.2f}%")

            log_file.write(f"\n实验结束时间: {datetime.now()}\n")
            log_file.write(f"总耗时: {elapsed_time:.2f} 秒\n")
            log_file.write(f"成功率: {success_count/len(results)*100:.2f}%\n")
            log_file.write(f"准确率: {accuracy*100:.2f}%\n")

    log_file.close()


if __name__ == "__main__":
    run_experiment()
