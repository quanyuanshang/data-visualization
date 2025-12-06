"""
提取时间线关系数据
从原始图数据中提取流派间的关系（翻唱、采样、引用、风格模仿等）
"""

import json
from collections import defaultdict
from pathlib import Path

def load_work_influence(base_dir: Path):
    """
    从预计算文件读取歌曲影响力分数。
    优先顺序：
    1) data/song_influence.json（calc_song_influence.py 产出，nodes[].influence）
    2) data/person_tracks.json
    3) genre-visualization/public/data/person_tracks.json
    返回 {work_id: influence_score}
    """
    influence_map = {}
    candidates = [
        base_dir / "data" / "song_influence.json",
        base_dir / "data" / "person_tracks.json",
        base_dir / "genre-visualization" / "public" / "data" / "person_tracks.json",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # song_influence.json 也是 nodes 结构
            nodes = data.get("nodes", [])
            for n in nodes:
                work_id = n.get("id") or n.get("song_id")
                if work_id is None:
                    continue
                inf = n.get("influence") or n.get("influence_score") or n.get("score")
                if inf is None:
                    continue
                # 同时存数字和字符串键，便于匹配
                influence_map[work_id] = inf
                influence_map[str(work_id)] = inf
            print(f"[INFO] 读取影响力: {len(influence_map)//2} 首歌曲，来源: {p.name}")
            return influence_map
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 读取 {p} 失败: {exc}")
    print("[WARN] 未找到 person_tracks.json，影响力将默认为 0")
    return influence_map


def extract_timeline_relations(graph_file, timeline_file, output_file):
    """
    从图数据中提取关系，并添加到时间线数据中
    
    关系类型：
    - CoverOf: 翻唱
    - DirectlySamples: 采样
    - InterpolatesFrom: 插值引用
    - LyricalReferenceTo: 歌词引用
    - InStyleOf: 风格模仿
    """
    
    # 加载图数据
    print(f"加载图数据: {graph_file}")
    with open(graph_file, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # 加载时间线数据
    print(f"加载时间线数据: {timeline_file}")
    with open(timeline_file, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)

    known_genres = set(timeline_data.get('genres', []))
    viz_data_path = Path(timeline_file).with_name('visualization_data.json')
    if viz_data_path.exists():
        try:
            with viz_data_path.open('r', encoding='utf-8') as f:
                viz_data = json.load(f)
            known_genres.update(viz_data.get('genres', []))
        except json.JSONDecodeError as exc:
            print(f"[WARN] 无法解析 {viz_data_path}: {exc}")
    
    # 创建节点ID到节点信息的映射
    nodes_map = {}
    for node in graph_data.get('nodes', []):
        nodes_map[node['id']] = node
    
    # 预加载歌曲影响力
    base_dir = Path(graph_file).resolve().parent.parent  # 兼容被放在 data/ 下
    work_influence = load_work_influence(base_dir)

    # 关系类型映射
    relation_types = {
        'CoverOf': 'CoverOf',
        'DirectlySamples': 'DirectlySamples',
        'InterpolatesFrom': 'InterpolatesFrom',
        'LyricalReferenceTo': 'LyricalReferenceTo',
        'InStyleOf': 'InStyleOf'
    }
    
    # 提取关系
    relations = []
    # 图数据中使用的是 'links' 而不是 'edges'
    edges = graph_data.get('links', [])
    
    print(f"处理 {len(edges)} 条边...")
    
    processed = 0
    skipped_no_type = 0
    skipped_wrong_type = 0
    skipped_no_nodes = 0
    skipped_not_works = 0
    skipped_no_genre = 0
    skipped_no_date = 0
    skipped_year_out_of_range = 0
    same_genre_count = 0  # 统计同流派关系数量
    
    for edge in edges:
        processed += 1
        if processed % 10000 == 0:
            print(f"  已处理 {processed} 条边...")
        
        edge_type = edge.get('Edge Type', '')
        
        # 只处理我们关心的关系类型
        if not edge_type:
            skipped_no_type += 1
            continue
        if edge_type not in relation_types:
            skipped_wrong_type += 1
            continue
        
        source_id = edge.get('source')
        target_id = edge.get('target')
        
        if source_id not in nodes_map or target_id not in nodes_map:
            skipped_no_nodes += 1
            continue
        
        source_node = nodes_map[source_id]
        target_node = nodes_map[target_id]
        
        # 只处理Song和Album之间的关系
        if source_node.get('Node Type') not in ['Song', 'Album']:
            skipped_not_works += 1
            continue
        if target_node.get('Node Type') not in ['Song', 'Album']:
            skipped_not_works += 1
            continue
        
        source_genre = source_node.get('genre')
        target_genre = target_node.get('genre')
        
        if not source_genre or not target_genre:
            skipped_no_genre += 1
            continue
        
        # 现在包含同一流派内部的关系（自引用关系）
        # 移除同流派过滤，允许处理同一流派内部的关系
        
        # 提取年份
        source_date = source_node.get('release_date')
        target_date = target_node.get('release_date')
        
        if not source_date or not target_date:
            skipped_no_date += 1
            continue
        
        # 提取年份（假设日期格式为 "YYYY" 或 "YYYY-MM-DD"）
        try:
            source_year = int(str(source_date).split('-')[0])
            target_year = int(str(target_date).split('-')[0])
        except (ValueError, AttributeError):
            skipped_no_date += 1
            continue
        
        # 检查年份是否在时间范围内
        time_range = timeline_data.get('time_range', {})
        all_years = time_range.get('all_years', [])
        
        if source_year not in all_years or target_year not in all_years:
            skipped_year_out_of_range += 1
            continue
        
        # 提取歌曲标题与影响力（name 字段 + influence 字段）
        source_title = source_node.get('name', '')
        target_title = target_node.get('name', '')
        # 影响力：优先用 person_tracks 的预计算分数，其次节点自带字段
        source_influence = (
            work_influence.get(source_id)
            or source_node.get('influence')
            or source_node.get('influence_score')
            or source_node.get('score')
            or 0
        )
        target_influence = (
            work_influence.get(target_id)
            or target_node.get('influence')
            or target_node.get('influence_score')
            or target_node.get('score')
            or 0
        )
        
        known_genres.update([source_genre, target_genre])
        
        # 统计同流派关系
        if source_genre == target_genre:
            same_genre_count += 1

        relations.append({
            'source_genre': source_genre,
            'target_genre': target_genre,
            'source_year': source_year,
            'target_year': target_year,
            'relation_type': edge_type,
            'source_work_id': source_id,
            'target_work_id': target_id,
            'source_title': source_title,        # 源歌曲标题
            'target_title': target_title,        # 目标歌曲标题
            'source_influence': source_influence, # 源歌曲影响力
            'target_influence': target_influence  # 目标歌曲影响力
        })
    
    print(f"\n处理完成！")
    print(f"  总边数: {processed}")
    print(f"  提取到: {len(relations)} 条关系")
    print(f"\n跳过统计:")
    print(f"  无类型: {skipped_no_type}")
    print(f"  错误类型: {skipped_wrong_type}")
    print(f"  节点不存在: {skipped_no_nodes}")
    print(f"  非作品节点: {skipped_not_works}")
    print(f"  无流派: {skipped_no_genre}")
    print(f"  无日期: {skipped_no_date}")
    print(f"  年份超出范围: {skipped_year_out_of_range}")
    print(f"\n同流派内部关系: {same_genre_count} 条（已包含在总关系数中）")
    
    # 添加到时间线数据
    timeline_data['relations'] = relations

    # 确保 genre_timelines 中包含所有已知流派
    genre_timelines = timeline_data.setdefault('genre_timelines', {})
    for genre in sorted(known_genres):
        genre_timelines.setdefault(genre, {"timeline": []})
    timeline_data['genres'] = sorted(known_genres)
    
    # 统计关系类型
    relation_counts = defaultdict(int)
    for rel in relations:
        relation_counts[rel['relation_type']] += 1
    
    print("\n关系类型统计:")
    for rel_type, count in relation_counts.items():
        print(f"  {rel_type}: {count}")
    
    # 保存更新后的时间线数据
    print(f"\n保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=2)
    
    print("完成！")

if __name__ == '__main__':
    import sys
    import os
    
    # 设置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    graph_file = os.path.join(base_dir, 'data', 'Topic1_graph.json')
    timeline_file = os.path.join(base_dir, 'genre-visualization', 'public', 'data', 'genre_timeline_data.json')
    output_file = timeline_file  # 直接更新原文件
    
    if not os.path.exists(graph_file):
        print(f"错误: 图数据文件不存在: {graph_file}")
        sys.exit(1)
    
    if not os.path.exists(timeline_file):
        print(f"错误: 时间线数据文件不存在: {timeline_file}")
        sys.exit(1)
    
    extract_timeline_relations(graph_file, timeline_file, output_file)

