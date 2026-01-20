"""
评估和可视化两个实验的结果
对比不使用RAG vs 使用RAG的性能差异
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
import json
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 文件路径
RESULTS_NO_RAG = "results_no_rag.csv"
RESULTS_WITH_RAG = "results_with_rag.csv"
DATA_FILE = "data4.csv"
OUTPUT_DIR = "evaluation_results"

# 创建输出目录
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)


def calculate_metrics(df, experiment_name):
    """计算评估指标"""
    # 只计算成功的样本
    df_success = df[df['success'] == True].copy()

    if len(df_success) == 0:
        print(f"警告: {experiment_name} 没有成功的样本！")
        return None

    y_true = df_success['true_label'].values
    y_pred = df_success['predicted_label'].values

    # 计算各项指标
    metrics = {
        'experiment': experiment_name,
        'total_samples': len(df),
        'success_samples': len(df_success),
        'success_rate': len(df_success) / len(df),
        'accuracy': accuracy_score(y_true, y_pred),
        'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
        'precision_weighted': precision_score(y_true, y_pred, average='weighted', zero_division=0),
        'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0),
        'recall_weighted': recall_score(y_true, y_pred, average='weighted', zero_division=0),
        'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
        'f1_weighted': f1_score(y_true, y_pred, average='weighted', zero_division=0),
    }

    # 分类别的指标
    for label, name in [(-1, 'negative'), (0, 'neutral'), (1, 'positive')]:
        mask = y_true == label
        if mask.sum() > 0:
            metrics[f'precision_{name}'] = precision_score(y_true == label, y_pred == label, zero_division=0)
            metrics[f'recall_{name}'] = recall_score(y_true == label, y_pred == label, zero_division=0)
            metrics[f'f1_{name}'] = f1_score(y_true == label, y_pred == label, zero_division=0)
            metrics[f'count_{name}'] = mask.sum()

    return metrics, y_true, y_pred


def plot_confusion_matrices(y_true_no_rag, y_pred_no_rag, y_true_with_rag, y_pred_with_rag):
    """绘制混淆矩阵对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    labels = ['消极(-1)', '中性(0)', '积极(1)']

    # 不使用RAG的混淆矩阵
    cm1 = confusion_matrix(y_true_no_rag, y_pred_no_rag, labels=[-1, 0, 1])
    sns.heatmap(cm1, annot=True, fmt='d', cmap='Blues', xticklabels=labels,
                yticklabels=labels, ax=axes[0], cbar_kws={'label': '样本数'})
    axes[0].set_title('不使用RAG - 混淆矩阵', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('真实标签', fontsize=12)
    axes[0].set_xlabel('预测标签', fontsize=12)

    # 使用RAG的混淆矩阵
    cm2 = confusion_matrix(y_true_with_rag, y_pred_with_rag, labels=[-1, 0, 1])
    sns.heatmap(cm2, annot=True, fmt='d', cmap='Greens', xticklabels=labels,
                yticklabels=labels, ax=axes[1], cbar_kws={'label': '样本数'})
    axes[1].set_title('使用d-rag - 混淆矩阵', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('真实标签', fontsize=12)
    axes[1].set_xlabel('预测标签', fontsize=12)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/confusion_matrices.png', dpi=300, bbox_inches='tight')
    print(f"✓ 保存混淆矩阵: {OUTPUT_DIR}/confusion_matrices.png")
    plt.close()


def plot_metrics_comparison(metrics_no_rag, metrics_with_rag):
    """绘制指标对比图"""
    # 主要指标对比
    metric_names = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro', 'f1_weighted']
    metric_labels = ['准确率', '精确率(宏平均)', '召回率(宏平均)', 'F1分数(宏平均)', 'F1分数(加权)']

    no_rag_values = [metrics_no_rag[m] for m in metric_names]
    with_rag_values = [metrics_with_rag[m] for m in metric_names]

    x = np.arange(len(metric_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - width/2, no_rag_values, width, label='不使用RAG', color='skyblue', edgecolor='black')
    bars2 = ax.bar(x + width/2, with_rag_values, width, label='使用d-rag', color='lightgreen', edgecolor='black')

    ax.set_ylabel('分数', fontsize=12)
    ax.set_title('性能指标对比', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=11)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # 在柱子上显示数值
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}', ha='center', va='bottom', fontsize=9)

    autolabel(bars1)
    autolabel(bars2)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/metrics_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ 保存指标对比图: {OUTPUT_DIR}/metrics_comparison.png")
    plt.close()


def plot_per_class_f1(metrics_no_rag, metrics_with_rag):
    """绘制各类别F1分数对比"""
    classes = ['negative', 'neutral', 'positive']
    class_labels = ['消极', '中性', '积极']

    no_rag_f1 = [metrics_no_rag.get(f'f1_{c}', 0) for c in classes]
    with_rag_f1 = [metrics_with_rag.get(f'f1_{c}', 0) for c in classes]

    x = np.arange(len(class_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, no_rag_f1, width, label='不使用RAG', color='coral', edgecolor='black')
    bars2 = ax.bar(x + width/2, with_rag_f1, width, label='使用d-rag', color='mediumseagreen', edgecolor='black')

    ax.set_ylabel('F1分数', fontsize=12)
    ax.set_title('各情感类别F1分数对比', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(class_labels, fontsize=12)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # 显示数值和样本数
    def autolabel(bars, metrics, suffix):
        for idx, bar in enumerate(bars):
            height = bar.get_height()
            count = metrics.get(f'count_{classes[idx]}', 0)
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}\n(n={count})', ha='center', va='bottom', fontsize=9)

    autolabel(bars1, metrics_no_rag, 'no_rag')
    autolabel(bars2, metrics_with_rag, 'with_rag')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/per_class_f1.png', dpi=300, bbox_inches='tight')
    print(f"✓ 保存类别F1对比图: {OUTPUT_DIR}/per_class_f1.png")
    plt.close()


def generate_report(metrics_no_rag, metrics_with_rag):
    """生成评估报告"""
    report = []
    report.append("=" * 80)
    report.append("情感分析实验评估报告")
    report.append("=" * 80)
    report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 实验对比
    report.append("\n" + "=" * 80)
    report.append("【实验对比】")
    report.append("=" * 80)

    comparison_data = []
    for key in ['total_samples', 'success_samples', 'success_rate', 'accuracy',
                'precision_macro', 'recall_macro', 'f1_macro', 'f1_weighted']:
        no_rag_val = metrics_no_rag[key]
        with_rag_val = metrics_with_rag[key]

        if key in ['success_rate', 'accuracy', 'precision_macro', 'recall_macro', 'f1_macro', 'f1_weighted']:
            improvement = with_rag_val - no_rag_val
            improvement_pct = (improvement / no_rag_val * 100) if no_rag_val > 0 else 0
            comparison_data.append({
                '指标': key,
                '不使用RAG': f'{no_rag_val:.4f}',
                '使用d-rag': f'{with_rag_val:.4f}',
                '提升': f'{improvement:+.4f} ({improvement_pct:+.2f}%)'
            })
        else:
            comparison_data.append({
                '指标': key,
                '不使用RAG': str(no_rag_val),
                '使用d-rag': str(with_rag_val),
                '提升': str(with_rag_val - no_rag_val)
            })

    df_comparison = pd.DataFrame(comparison_data)
    report.append(df_comparison.to_string(index=False))

    # 各类别详细指标
    report.append("\n\n" + "=" * 80)
    report.append("【各情感类别详细指标】")
    report.append("=" * 80)

    for class_name, label in [('消极', 'negative'), ('中性', 'neutral'), ('积极', 'positive')]:
        report.append(f"\n{class_name}:")
        report.append(f"  不使用RAG - Precision: {metrics_no_rag.get(f'precision_{label}', 0):.4f}, "
                     f"Recall: {metrics_no_rag.get(f'recall_{label}', 0):.4f}, "
                     f"F1: {metrics_no_rag.get(f'f1_{label}', 0):.4f}")
        report.append(f"  使用d-rag  - Precision: {metrics_with_rag.get(f'precision_{label}', 0):.4f}, "
                     f"Recall: {metrics_with_rag.get(f'recall_{label}', 0):.4f}, "
                     f"F1: {metrics_with_rag.get(f'f1_{label}', 0):.4f}")

        f1_improvement = metrics_with_rag.get(f'f1_{label}', 0) - metrics_no_rag.get(f'f1_{label}', 0)
        report.append(f"  F1提升: {f1_improvement:+.4f}")

    # 结论
    report.append("\n\n" + "=" * 80)
    report.append("【结论】")
    report.append("=" * 80)

    acc_improvement = metrics_with_rag['accuracy'] - metrics_no_rag['accuracy']
    f1_improvement = metrics_with_rag['f1_weighted'] - metrics_no_rag['f1_weighted']

    report.append(f"\n1. 准确率提升: {acc_improvement:+.4f} ({acc_improvement/metrics_no_rag['accuracy']*100:+.2f}%)")
    report.append(f"2. F1分数(加权)提升: {f1_improvement:+.4f} ({f1_improvement/metrics_no_rag['f1_weighted']*100:+.2f}%)")

    if acc_improvement > 0:
        report.append(f"\n✓ d-rag系统显著提升了情感分析的准确性")
    else:
        report.append(f"\n✗ d-rag系统未能提升准确性，需要进一步优化")

    report.append("\n" + "=" * 80)

    # 保存报告
    report_text = '\n'.join(report)
    with open(f'{OUTPUT_DIR}/evaluation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)

    print("\n" + report_text)
    print(f"\n✓ 保存评估报告: {OUTPUT_DIR}/evaluation_report.txt")


def main():
    """主函数"""
    print("=" * 80)
    print("评估和可视化实验结果")
    print("=" * 80)

    # 加载结果
    print("\n加载实验结果...")
    try:
        df_no_rag = pd.read_csv(RESULTS_NO_RAG)
        print(f"✓ 加载不使用RAG结果: {len(df_no_rag)} 条")
    except FileNotFoundError:
        print(f"✗ 找不到文件: {RESULTS_NO_RAG}")
        return

    try:
        df_with_rag = pd.read_csv(RESULTS_WITH_RAG)
        print(f"✓ 加载使用RAG结果: {len(df_with_rag)} 条")
    except FileNotFoundError:
        print(f"✗ 找不到文件: {RESULTS_WITH_RAG}")
        return

    # 计算指标
    print("\n计算评估指标...")
    metrics_no_rag, y_true_no_rag, y_pred_no_rag = calculate_metrics(df_no_rag, "不使用RAG")
    metrics_with_rag, y_true_with_rag, y_pred_with_rag = calculate_metrics(df_with_rag, "使用d-rag")

    if metrics_no_rag is None or metrics_with_rag is None:
        print("错误: 无法计算指标")
        return

    # 生成可视化
    print("\n生成可视化图表...")
    plot_confusion_matrices(y_true_no_rag, y_pred_no_rag, y_true_with_rag, y_pred_with_rag)
    plot_metrics_comparison(metrics_no_rag, metrics_with_rag)
    plot_per_class_f1(metrics_no_rag, metrics_with_rag)

    # 生成报告
    print("\n生成评估报告...")
    generate_report(metrics_no_rag, metrics_with_rag)

    # 保存指标到JSON
    metrics_combined = {
        'no_rag': metrics_no_rag,
        'with_rag': metrics_with_rag,
        'timestamp': datetime.now().isoformat()
    }
    with open(f'{OUTPUT_DIR}/metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics_combined, f, ensure_ascii=False, indent=2)
    print(f"✓ 保存指标数据: {OUTPUT_DIR}/metrics.json")

    print(f"\n所有评估结果已保存到目录: {OUTPUT_DIR}/")
    print("=" * 80)


if __name__ == "__main__":
    main()
