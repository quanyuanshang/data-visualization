"""
保存分析结果到JSON文件
"""
import json
import sys
import os
from data_preprocessing import MusicGraphProcessor
from task_analysis import Task1_PersonEvaluation, Task2_GenreAnalysis, Task3_OceanusFolkPrediction

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

def save_results():
    """保存所有分析结果"""
    print("="*80)
    print("保存分析结果")
    print("="*80)
    
    # 初始化
    processor = MusicGraphProcessor('Topic1_graph.json')
    
    # 任务1：评估音乐人（评估全部音乐人）
    print("\n任务1：评估音乐人表现（全部音乐人）...")
    task1 = Task1_PersonEvaluation(processor)
    persons = processor.get_nodes_by_type('Person')
    evaluations = []
    for i, person in enumerate(persons):
        if (i + 1) % 500 == 0:
            print(f"    已处理 {i+1}/{len(persons)}...")
        evaluation = task1.evaluate_person(person['id'])
        if evaluation:
            evaluations.append(evaluation)
    
    # 按评分排序
    evaluations.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"  完成！共评估 {len(evaluations)} 个音乐人")
    

    # 新增：基于阈值的多标签与矩阵导出
    print("  基于阈值(0.4)为音乐人打流派标签，并导出占比矩阵...")
    labeled_evaluations = task1.assign_genre_labels(evaluations, threshold=0.4)
    with open('person_evaluations_labeled.json', 'w', encoding='utf-8') as f:
        json.dump(labeled_evaluations, f, ensure_ascii=False, indent=2)
    print("  ✓ 已保存到 person_evaluations_labeled.json")

    matrix_csv = task1.export_person_genre_matrix(labeled_evaluations, 'person_genre_matrix.csv')
    print(f"  ✓ 已导出 {matrix_csv}")
    
    # 任务2：分析流派发展
    print("\n任务2：分析音乐流派发展...")
    task2 = Task2_GenreAnalysis(processor)
    
    # 分析所有流派
    all_genres = task2.get_all_genres()
    print(f"  找到 {len(all_genres)} 个流派")
    
    genre_analyses = {}
    for i, genre in enumerate(all_genres):
        print(f"  分析 {genre} ({i+1}/{len(all_genres)})...")
        analysis = task2.analyze_genre_development(genre)
        # 只保存关键信息
        genre_analyses[genre] = {
            'timeline': [(year, {
                'total': data['total'],
                'notable': data['notable'],
                'notable_rate': data['notable'] / data['total'] if data['total'] > 0 else 0
            }) for year, data in analysis['timeline']],
            'yearly_counts': analysis['yearly_counts'],
            'yearly_notable_rate': analysis['yearly_notable_rate'],
            'cover_stats': {
                'total_covers': analysis['cover_stats']['total_covers'],
                'average_time_gap': analysis['cover_stats']['average_time_gap']
            }
        }
    
    with open('genre_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(genre_analyses, f, ensure_ascii=False, indent=2)
    print("  ✓ 已保存到 genre_analysis.json")
    
    # 任务3：预测Oceanus Folk超级明星
    print("\n任务3：预测Oceanus Folk超级明星...")
    task3 = Task3_OceanusFolkPrediction(processor)
    
    candidates = task3.predict_superstars(top_n=50)
    print(f"  找到 {len(candidates)} 个候选人")
    
    # 保存详细特征
    with open('oceanus_folk_candidates.json', 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    print("  ✓ 已保存到 oceanus_folk_candidates.json")
    
    # 生成摘要报告
    print("\n生成摘要报告...")
    summary = {
        'task1': {
            'total_evaluated': len(evaluations),
            'top_10': [{
                'name': e['name'],
                'score': e['score'],
                'total_works': e['total_works'],
                'notable_rate': e['notable_rate']
            } for e in evaluations[:10]]
        },
        'task2': {
            'total_genres': len(all_genres),
            'genres': all_genres
        },
        'task3': {
            'total_candidates': len(candidates),
            'top_10': [{
                'name': c['name'],
                'score': c['score'],
                'of_total': c['of_total'],
                'of_notable_count': c['of_notable_count'],
                'recent_active': c['recent_active']
            } for c in candidates[:10]]
        }
    }
    
    with open('analysis_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("  ✓ 已保存到 analysis_summary.json")
    
    print("\n" + "="*80)
    print("所有结果已保存！")
    print("="*80)
    print("\n生成的文件：")
    print("  - person_evaluations.json: 音乐人评估结果")
    print("  - genre_analysis.json: 流派分析结果")
    print("  - oceanus_folk_candidates.json: Oceanus Folk候选人")
    print("  - analysis_summary.json: 分析摘要")

if __name__ == '__main__':
    save_results()

