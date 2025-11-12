"""
三个任务的分析脚本
1. 评估音乐人的表现
2. 分析音乐流派发展
3. 预测Oceanus Folk超级明星
"""
import json
import sys
from collections import defaultdict, Counter
from datetime import datetime
import re
from data_preprocessing import MusicGraphProcessor

# 设置输出编码
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass


class Task1_PersonEvaluation:
    """任务1：评估音乐人的表现"""
    
    def __init__(self, processor):
        self.processor = processor
        # 统一的26个流派列表（从数据中动态抽取，稳定排序）
        genres = set()
        for node in self.processor.get_nodes_by_type('Song') + self.processor.get_nodes_by_type('Album'):
            g = node.get('genre')
            if g:
                genres.add(g)
        self.all_genres = sorted(list(genres))
    
    def evaluate_person(self, person_id):
        """评估单个音乐人的表现"""
        person = self.processor.get_node(person_id)
        if not person or person.get('Node Type') != 'Person':
            return None
        
        # 获取所有作品
        works = self.processor.get_person_works(person_id)
        all_works = []
        for role_works in works.values():
            all_works.extend(role_works)
        
        # 去重（同一作品可能有多重角色）
        unique_works = {w['id']: w for w in all_works}.values()
        
        # 统计基本信息
        total_works = len(unique_works)
        songs = [w for w in unique_works if w.get('Node Type') == 'Song']
        albums = [w for w in unique_works if w.get('Node Type') == 'Album']
        
        # 统计成名作品
        notable_works = [w for w in unique_works if w.get('notable') == True]
        notable_rate = len(notable_works) / total_works if total_works > 0 else 0
        
        # 统计时间跨度
        dates = []
        for work in unique_works:
            date = self.processor.extract_date(work)
            if date:
                dates.append(date)
        
        time_span = max(dates) - min(dates) if dates else 0
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None
        
        # 统计角色多样性
        roles = set(works.keys())
        role_count = len(roles)
        
        # 统计流派分布
        genre_distribution = Counter()
        for work in unique_works:
            genre = work.get('genre')
            if genre:
                genre_distribution[genre] += 1

        # 计算26流派占比（仅歌曲Song计入占比，Album不计）
        song_genre_counts = Counter()
        total_songs_for_share = 0
        for w in unique_works:
            if w.get('Node Type') == 'Song':
                g = w.get('genre')
                if g:
                    song_genre_counts[g] += 1
                    total_songs_for_share += 1
        genre_share = {g: (song_genre_counts.get(g, 0) / total_songs_for_share if total_songs_for_share > 0 else 0.0)
                       for g in self.all_genres}
        
        # 统计影响力（被翻唱、采样等）
        influence_score = 0
        for work in unique_works:
            work_id = work['id']
            # 被翻唱
            covers = [e for e in self.processor.get_edges_to(work_id) if e[0] == 'CoverOf']
            # 被采样
            samples = [e for e in self.processor.get_edges_to(work_id) if e[0] == 'DirectlySamples']
            # 被引用
            references = [e for e in self.processor.get_edges_to(work_id) if e[0] in ['InterpolatesFrom', 'LyricalReferenceTo']]
            # 被模仿
            imitations = [e for e in self.processor.get_edges_to(work_id) if e[0] == 'InStyleOf']
            
            influence_score += len(covers) * 3 + len(samples) * 2 + len(references) + len(imitations)
        
        # 合作网络
        collaborators = set()
        for work in unique_works:
            work_id = work['id']
            for edge_type, source_id in self.processor.get_edges_to(work_id):
                if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                    source_node = self.processor.get_node(source_id)
                    if source_node and source_node.get('Node Type') == 'Person' and source_id != person_id:
                        collaborators.add(source_id)
        
        # 唱片公司
        record_labels = set()
        for work in unique_works:
            work_id = work['id']
            for edge_type, label_id in self.processor.get_edges_to(work_id):
                if edge_type in ['RecordedBy', 'DistributedBy']:
                    record_labels.add(label_id)
        
        # 计算综合评分
        score = (
            total_works * 0.15 +
            notable_rate * 100 * 0.25 +
            time_span * 0.1 +
            role_count * 5 * 0.1 +
            influence_score * 0.2 +
            len(collaborators) * 0.1 +
            len(record_labels) * 0.1
        )
        
        return {
            'person_id': person_id,
            'name': person.get('name', 'Unknown'),
            'stage_name': person.get('stage_name'),
            'total_works': total_works,
            'songs': len(songs),
            'albums': len(albums),
            'notable_works': len(notable_works),
            'notable_rate': notable_rate,
            'time_span': time_span,
            'min_date': min_date,
            'max_date': max_date,
            'roles': list(roles),
            'role_count': role_count,
            'genre_distribution': dict(genre_distribution),
            'genre_share': genre_share,  # 各流派占比（仅Song）
            'influence_score': influence_score,
            'collaborators_count': len(collaborators),
            'record_labels_count': len(record_labels),
            'score': score,
            'works_by_role': {role: len(works[role]) for role in roles}
        }
    
    def evaluate_all_persons(self):
        """评估所有音乐人"""
        print("\n正在评估所有音乐人...")
        persons = self.processor.get_nodes_by_type('Person')
        results = []
        
        for i, person in enumerate(persons):
            if (i + 1) % 1000 == 0:
                print(f"  已处理 {i+1}/{len(persons)} 个音乐人...")
            
            evaluation = self.evaluate_person(person['id'])
            if evaluation:
                results.append(evaluation)
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def assign_genre_labels(self, evaluations, threshold: float = 0.4):
        """基于占比阈值为音乐人打流派标签（可多标签）。返回新列表副本。
        threshold: 占比阈值（0-1），如0.4表示>=40%则归为该流派。
        """
        labeled = []
        for ev in evaluations:
            shares = ev.get('genre_share', {})
            labels = [g for g, p in shares.items() if p >= threshold]
            # 若没有达到阈值，取占比最高的1个流派作为主标签（可选逻辑）
            if not labels and shares:
                top = max(shares.items(), key=lambda x: x[1])
                if top[1] > 0:
                    labels = [top[0]]
            item = dict(ev)
            item['genre_labels'] = labels
            labeled.append(item)
        return labeled

    def export_person_genre_matrix(self, evaluations, out_csv_path: str):
        """导出人员×流派占比矩阵为CSV，第一列为person_id与name，后续26列为占比。"""
        import csv
        header = ['person_id', 'name'] + self.all_genres
        with open(out_csv_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            for ev in evaluations:
                shares = ev.get('genre_share', {})
                row = [ev.get('person_id'), ev.get('name')]
                row.extend([shares.get(g, 0.0) for g in self.all_genres])
                w.writerow(row)
        return out_csv_path
    
    def get_person_works_grouped(self, person_id):
        """获取音乐人的作品，按专辑分组"""
        works = self.processor.get_person_works(person_id)
        
        # 获取所有作品
        all_works = []
        for role_works in works.values():
            all_works.extend(role_works)
        
        # 按专辑分组
        albums = {}
        songs = []
        
        for work in all_works:
            if work.get('Node Type') == 'Album':
                albums[work['id']] = {
                    'album': work,
                    'songs': []
                }
            elif work.get('Node Type') == 'Song':
                songs.append(work)
        
        # 为每个专辑找到相关的歌曲
        for album_id, album_data in albums.items():
            album_songs = self.processor.get_album_songs(album_id, person_id)
            album_data['songs'] = album_songs
        
        # 未分组的歌曲
        ungrouped_songs = []
        for song in songs:
            song_id = song['id']
            # 检查是否已经分配给某个专辑
            found = False
            for album_data in albums.values():
                if any(s['id'] == song_id for s in album_data['songs']):
                    found = True
                    break
            if not found:
                ungrouped_songs.append(song)
        
        return {
            'albums': albums,
            'ungrouped_songs': ungrouped_songs
        }


class Task2_GenreAnalysis:
    """任务2：分析音乐流派发展"""
    
    def __init__(self, processor):
        self.processor = processor
    
    def get_genre_timeline(self, genre=None):
        """获取流派的时间线（按年份统计作品数）"""
        genre_timeline = defaultdict(lambda: {'total': 0, 'notable': 0, 'songs': [], 'albums': []})
        
        # 获取所有Song和Album节点
        songs = self.processor.get_nodes_by_type('Song')
        albums = self.processor.get_nodes_by_type('Album')
        
        for work in songs + albums:
            work_genre = work.get('genre')
            if not work_genre:
                continue
            
            if genre and work_genre != genre:
                continue
            
            date = self.processor.extract_date(work, ['release_date'])
            if not date:
                continue
            
            genre_timeline[date]['total'] += 1
            if work.get('notable'):
                genre_timeline[date]['notable'] += 1
            
            if work.get('Node Type') == 'Song':
                genre_timeline[date]['songs'].append(work)
            else:
                genre_timeline[date]['albums'].append(work)
        
        # 转换为排序的列表
        timeline = sorted([(year, data) for year, data in genre_timeline.items()])
        return timeline
    
    def get_cover_relationships(self, genre=None):
        """获取翻唱关系（按时间排序）"""
        cover_edges = self.processor.get_edges_by_type('CoverOf')
        covers = []
        
        for source_id, target_id in cover_edges:
            source = self.processor.get_node(source_id)
            target = self.processor.get_node(target_id)
            
            if not source or not target:
                continue
            
            source_type = source.get('Node Type')
            target_type = target.get('Node Type')
            
            if source_type not in ['Song', 'Album'] or target_type not in ['Song', 'Album']:
                continue
            
            if genre:
                if source.get('genre') != genre and target.get('genre') != genre:
                    continue
            
            source_date = self.processor.extract_date(source, ['release_date'])
            target_date = self.processor.extract_date(target, ['release_date'])
            
            if source_date and target_date:
                covers.append({
                    'source': source,
                    'target': target,
                    'source_date': source_date,
                    'target_date': target_date,
                    'time_diff': source_date - target_date  # 翻唱时间 - 原唱时间
                })
        
        # 按翻唱时间排序
        covers.sort(key=lambda x: x['source_date'])
        return covers
    
    def analyze_genre_development(self, genre):
        """分析特定流派的发展"""
        timeline = self.get_genre_timeline(genre)
        covers = self.get_cover_relationships(genre)
        
        # 统计每年作品数
        yearly_counts = {year: data['total'] for year, data in timeline}
        
        # 统计成名率
        yearly_notable_rate = {}
        for year, data in timeline:
            if data['total'] > 0:
                yearly_notable_rate[year] = data['notable'] / data['total']
        
        # 翻唱模式分析
        cover_stats = {
            'total_covers': len(covers),
            'average_time_gap': sum(c['time_diff'] for c in covers) / len(covers) if covers else 0,
            'covers_by_year': Counter(c['source_date'] for c in covers)
        }
        
        return {
            'genre': genre,
            'timeline': timeline,
            'yearly_counts': yearly_counts,
            'yearly_notable_rate': yearly_notable_rate,
            'cover_stats': cover_stats,
            'covers': covers
        }
    
    def get_all_genres(self):
        """获取所有流派列表"""
        genres = set()
        for node in self.processor.get_nodes_by_type('Song') + self.processor.get_nodes_by_type('Album'):
            genre = node.get('genre')
            if genre:
                genres.add(genre)
        return sorted(list(genres))


class Task3_OceanusFolkPrediction:
    """任务3：预测Oceanus Folk超级明星"""
    
    def __init__(self, processor):
        self.processor = processor
        self.target_genre = 'Oceanus Folk'
    
    def extract_person_features(self, person_id):
        """提取音乐人的特征"""
        person = self.processor.get_node(person_id)
        if not person:
            return None
        
        # 获取所有作品
        works = self.processor.get_person_works(person_id)
        all_works = []
        for role_works in works.values():
            all_works.extend(role_works)
        unique_works = {w['id']: w for w in all_works}.values()
        
        # 筛选Oceanus Folk作品
        of_works = [w for w in unique_works if w.get('genre') == self.target_genre]
        
        if not of_works:
            return None
        
        # 特征1：当前表现
        of_total = len(of_works)
        of_notable = [w for w in of_works if w.get('notable')]
        of_notable_count = len(of_notable)
        of_notable_rate = of_notable_count / of_total if of_total > 0 else 0
        
        # 特征2：上升趋势（最近5年：2024-2029）
        recent_works = []
        of_dates = []
        for w in of_works:
            date = self.processor.extract_date(w, ['release_date'])
            if date:
                of_dates.append(date)
                if 2024 <= date <= 2029:
                    recent_works.append(w)
        
        recent_count = len(recent_works)
        recent_notable = len([w for w in recent_works if w.get('notable')])
        
        # 增长率（如果有足够的历史数据）
        if len(of_dates) >= 2:
            sorted_dates = sorted(of_dates)
            first_half = [d for d in sorted_dates[:len(sorted_dates)//2]]
            second_half = [d for d in sorted_dates[len(sorted_dates)//2:]]
            growth_rate = len(second_half) / len(first_half) if first_half else 0
        else:
            growth_rate = 0
        
        # 首次OF作品时间
        first_of_date = min(of_dates) if of_dates else None
        
        # 特征3：创新性
        original_count = 0
        for work in of_works:
            work_id = work['id']
            # 检查是否是翻唱或采样
            is_cover = any(e[0] == 'CoverOf' for e in self.processor.get_edges_from(work_id))
            is_sample = any(e[0] == 'DirectlySamples' for e in self.processor.get_edges_from(work_id))
            if not is_cover and not is_sample:
                original_count += 1
        
        originality_rate = original_count / of_total if of_total > 0 else 0
        
        # 被引用/模仿次数
        cited_count = 0
        for work in of_works:
            work_id = work['id']
            cited = len([e for e in self.processor.get_edges_to(work_id) 
                        if e[0] in ['InterpolatesFrom', 'LyricalReferenceTo', 'InStyleOf']])
            cited_count += cited
        
        # 特征4：合作网络
        # 找到已成名的OF音乐人
        all_of_persons = set()
        for work in self.processor.get_nodes_by_type('Song') + self.processor.get_nodes_by_type('Album'):
            if work.get('genre') == self.target_genre and work.get('notable'):
                for edge_type, source_id in self.processor.get_edges_to(work['id']):
                    if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                        source_node = self.processor.get_node(source_id)
                        if source_node and source_node.get('Node Type') == 'Person':
                            all_of_persons.add(source_id)
        
        # 与该候选人的合作
        collaborators = set()
        for work in of_works:
            work_id = work['id']
            for edge_type, source_id in self.processor.get_edges_to(work_id):
                if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                    if source_id != person_id:
                        collaborators.add(source_id)
        
        # 与成名OF音乐人的合作
        famous_collaborators = collaborators & all_of_persons
        collaboration_with_famous = len(famous_collaborators)
        
        # 特征5：唱片公司支持
        record_labels = set()
        for work in of_works:
            work_id = work['id']
            for edge_type, label_id in self.processor.get_edges_to(work_id):
                if edge_type in ['RecordedBy', 'DistributedBy']:
                    record_labels.add(label_id)
        
        # 特征6：角色多样性
        of_roles = set()
        for edge_type, target_id in self.processor.get_edges_from(person_id):
            if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                target = self.processor.get_node(target_id)
                if target and target.get('genre') == self.target_genre:
                    of_roles.add(edge_type)
        
        role_count = len(of_roles)
        
        # 特征7：时间因素
        # 活跃时长（但不要太长，新星更可能）
        active_span = max(of_dates) - min(of_dates) if len(of_dates) >= 2 else 0
        recent_active = max(of_dates) if of_dates else None
        is_recent = recent_active and recent_active >= 2024
        
        return {
            'person_id': person_id,
            'name': person.get('name', 'Unknown'),
            # 当前表现
            'of_total': of_total,
            'of_notable_count': of_notable_count,
            'of_notable_rate': of_notable_rate,
            # 上升趋势
            'recent_count': recent_count,
            'recent_notable': recent_notable,
            'growth_rate': growth_rate,
            'first_of_date': first_of_date,
            # 创新性
            'originality_rate': originality_rate,
            'cited_count': cited_count,
            # 合作网络
            'collaborators_count': len(collaborators),
            'collaboration_with_famous': collaboration_with_famous,
            # 支持度
            'record_labels_count': len(record_labels),
            # 角色多样性
            'role_count': role_count,
            # 时间因素
            'active_span': active_span,
            'recent_active': recent_active,
            'is_recent': is_recent,
            # 综合评分
            'score': self._calculate_score({
                'of_total': of_total,
                'of_notable_rate': of_notable_rate,
                'recent_count': recent_count,
                'recent_notable': recent_notable,
                'growth_rate': growth_rate,
                'originality_rate': originality_rate,
                'cited_count': cited_count,
                'collaboration_with_famous': collaboration_with_famous,
                'record_labels_count': len(record_labels),
                'role_count': role_count,
                'is_recent': is_recent
            })
        }
    
    def _calculate_score(self, features):
        """计算综合评分"""
        score = (
            min(features['of_total'] / 10, 1.0) * 0.15 +  # 当前表现
            features['of_notable_rate'] * 0.15 +
            min(features['recent_count'] / 5, 1.0) * 0.20 +  # 上升趋势
            min(features['recent_notable'] / 3, 1.0) * 0.15 +
            min(features['growth_rate'] / 2, 1.0) * 0.10 +
            features['originality_rate'] * 0.10 +  # 创新性
            min(features['cited_count'] / 10, 1.0) * 0.05 +
            min(features['collaboration_with_famous'] / 5, 1.0) * 0.05 +  # 合作
            min(features['record_labels_count'] / 3, 1.0) * 0.03 +  # 支持度
            min(features['role_count'] / 4, 1.0) * 0.02 +
            (1.0 if features['is_recent'] else 0.0) * 0.05  # 时间因素
        )
        return score * 100
    
    def predict_superstars(self, top_n=20):
        """预测超级明星候选人"""
        print(f"\n正在分析Oceanus Folk音乐人...")
        
        # 找到所有有OF作品的人
        of_persons = set()
        for work in self.processor.get_nodes_by_type('Song') + self.processor.get_nodes_by_type('Album'):
            if work.get('genre') == self.target_genre:
                for edge_type, source_id in self.processor.get_edges_to(work['id']):
                    if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                        source_node = self.processor.get_node(source_id)
                        if source_node and source_node.get('Node Type') == 'Person':
                            of_persons.add(source_id)
        
        print(f"  找到 {len(of_persons)} 个有Oceanus Folk作品的音乐人")
        
        # 提取特征
        candidates = []
        for person_id in of_persons:
            features = self.extract_person_features(person_id)
            if features:
                candidates.append(features)
        
        # 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates[:top_n]


if __name__ == '__main__':
    print("="*80)
    print("音乐图谱数据分析系统")
    print("="*80)
    
    # 初始化数据处理器
    processor = MusicGraphProcessor('Topic1_graph.json')
    
    # 任务1：评估音乐人表现
    print("\n" + "="*80)
    print("任务1：评估音乐人表现")
    print("="*80)
    task1 = Task1_PersonEvaluation(processor)
    
    # 评估前5个音乐人作为示例
    print("\n示例：评估前5个音乐人")
    persons = processor.get_nodes_by_type('Person')[:5]
    for person in persons:
        evaluation = task1.evaluate_person(person['id'])
        if evaluation:
            print(f"\n{evaluation['name']}:")
            print(f"  总作品数: {evaluation['total_works']}")
            print(f"  成名率: {evaluation['notable_rate']:.2%}")
            print(f"  时间跨度: {evaluation['time_span']} 年")
            print(f"  综合评分: {evaluation['score']:.2f}")
    
    # 任务2：分析流派发展
    print("\n" + "="*80)
    print("任务2：分析音乐流派发展")
    print("="*80)
    task2 = Task2_GenreAnalysis(processor)
    
    # 分析Oceanus Folk
    print("\n分析Oceanus Folk流派发展：")
    of_analysis = task2.analyze_genre_development('Oceanus Folk')
    print(f"  时间跨度: {min(of_analysis['yearly_counts'].keys())} - {max(of_analysis['yearly_counts'].keys())}")
    print(f"  总作品数: {sum(of_analysis['yearly_counts'].values())}")
    print(f"  翻唱关系: {of_analysis['cover_stats']['total_covers']} 个")
    
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

