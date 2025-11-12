"""
运行分析的入口脚本
"""
import sys
import os
from datetime import datetime
from contextlib import redirect_stdout
from io import StringIO

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 创建输出文件
OUTPUT_FILE = 'analysis_output.txt'

# 创建字符串缓冲区来捕获输出
output_buffer = StringIO()

# 导入分析模块
from task_analysis import *
from data_preprocessing import MusicGraphProcessor

# 运行分析的主函数
def run_analysis():
    """运行分析的主函数"""
    
    print("="*80)
    print("音乐图谱数据分析系统")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 初始化数据处理器
    processor = MusicGraphProcessor('Topic1_graph.json')
    
    # 任务1：评估音乐人表现（示例）
    print("\n" + "="*80)
    print("任务1：评估音乐人表现（示例）")
    print("="*80)
    task1 = Task1_PersonEvaluation(processor)
    
    # 评估前3个音乐人作为示例
    print("\n示例：评估前3个音乐人")
    persons = processor.get_nodes_by_type('Person')[:3]
    for person in persons:
        evaluation = task1.evaluate_person(person['id'])
        if evaluation:
            print(f"\n{evaluation['name']}:")
            print(f"  总作品数: {evaluation['total_works']}")
            print(f"  成名率: {evaluation['notable_rate']:.2%}")
            print(f"  时间跨度: {evaluation['time_span']} 年")
            print(f"  综合评分: {evaluation['score']:.2f}")

    # 新增：基于阈值的流派标签与导出矩阵
    print("\n添加基于阈值的流派标签与导出矩阵示例（阈值=0.4）...")
    sample_evals = []
    for person in persons:
        ev = task1.evaluate_person(person['id'])
        if ev:
            sample_evals.append(ev)
    labeled = task1.assign_genre_labels(sample_evals, threshold=0.4)
    out_csv = task1.export_person_genre_matrix(labeled, 'person_genre_matrix_sample.csv')
    print(f"  ✓ 已导出示例矩阵: {out_csv}")
    
    # 任务2：分析流派发展（Oceanus Folk）
    print("\n" + "="*80)
    print("任务2：分析音乐流派发展")
    print("="*80)
    task2 = Task2_GenreAnalysis(processor)
    
    print("\n分析Oceanus Folk流派发展：")
    of_analysis = task2.analyze_genre_development('Oceanus Folk')
    if of_analysis['yearly_counts']:
        print(f"  时间跨度: {min(of_analysis['yearly_counts'].keys())} - {max(of_analysis['yearly_counts'].keys())}")
        print(f"  总作品数: {sum(of_analysis['yearly_counts'].values())}")
        print(f"  翻唱关系: {of_analysis['cover_stats']['total_covers']} 个")
        print(f"  平均翻唱时间差: {of_analysis['cover_stats']['average_time_gap']:.1f} 年")
    
    # 任务3：预测Oceanus Folk超级明星
    print("\n" + "="*80)
    print("任务3：预测Oceanus Folk超级明星")
    print("="*80)
    task3 = Task3_OceanusFolkPrediction(processor)
    
    superstars = task3.predict_superstars(top_n=10)
    print(f"\n前10名候选人：")
    for i, candidate in enumerate(superstars, 1):
        print(f"\n{i}. {candidate['name']} (评分: {candidate['score']:.2f})")
        print(f"   OF作品数: {candidate['of_total']}")
        print(f"   成名作品: {candidate['of_notable_count']}")
        print(f"   最近活跃: {candidate['recent_active']}")
        print(f"   与成名音乐人合作: {candidate['collaboration_with_famous']} 次")
        print(f"   创新度: {candidate['originality_rate']:.2%}")
    
    print("\n" + "="*80)
    print("分析完成！")
    print("="*80)

# 使用 redirect_stdout 捕获输出
try:
    with redirect_stdout(output_buffer):
        run_analysis()
    
    # 获取输出内容
    output_content = output_buffer.getvalue()
    
    # 同时显示在控制台和保存到文件
    print(output_content, end='')
    
    # 保存到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"\n输出已保存到: {OUTPUT_FILE}")
    
except Exception as e:
    error_msg = f"错误: {e}\n"
    import traceback
    error_msg += traceback.format_exc()
    print(error_msg)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output_buffer.getvalue())
        f.write(error_msg)

