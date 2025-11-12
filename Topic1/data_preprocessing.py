"""
数据预处理脚本
构建所有必要的索引和映射，为后续分析做准备
"""
import json
import sys
from collections import defaultdict
from datetime import datetime

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class MusicGraphProcessor:
    """音乐图谱数据处理器"""
    
    def __init__(self, json_file):
        """初始化，加载数据"""
        print("正在加载JSON数据...")
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print("数据加载完成！")
        self._build_indices()
    
    def _build_indices(self):
        """构建所有索引"""
        print("\n正在构建索引...")
        
        # 节点索引
        self.nodes_by_id = {}
        self.nodes_by_type = defaultdict(list)
        
        # 边索引
        self.edges_by_source = defaultdict(list)  # source -> [(edge_type, target)]
        self.edges_by_target = defaultdict(list)  # target -> [(edge_type, source)]
        self.edges_by_type = defaultdict(list)    # edge_type -> [(source, target)]
        
        # 构建节点索引
        for node in self.data['nodes']:
            node_id = node['id']
            node_type = node.get('Node Type')
            
            self.nodes_by_id[node_id] = node
            self.nodes_by_type[node_type].append(node)
        
        # 构建边索引
        for edge in self.data['links']:
            source = edge['source']
            target = edge['target']
            edge_type = edge['Edge Type']
            
            self.edges_by_source[source].append((edge_type, target))
            self.edges_by_target[target].append((edge_type, source))
            self.edges_by_type[edge_type].append((source, target))
        
        print(f"  节点总数: {len(self.nodes_by_id)}")
        print(f"  边总数: {len(self.data['links'])}")
        print(f"  节点类型: {list(self.nodes_by_type.keys())}")
        print(f"  边类型: {list(self.edges_by_type.keys())}")
    
    def get_node(self, node_id):
        """根据ID获取节点"""
        return self.nodes_by_id.get(node_id)
    
    def get_nodes_by_type(self, node_type):
        """根据类型获取所有节点"""
        return self.nodes_by_type.get(node_type, [])
    
    def get_edges_from(self, source_id):
        """获取从某个节点出发的所有边"""
        return self.edges_by_source.get(source_id, [])
    
    def get_edges_to(self, target_id):
        """获取指向某个节点的所有边"""
        return self.edges_by_target.get(target_id, [])
    
    def get_edges_by_type(self, edge_type):
        """获取特定类型的所有边"""
        return self.edges_by_type.get(edge_type, [])
    
    def extract_date(self, node, priority=['release_date', 'written_date', 'notoriety_date']):
        """提取节点日期，按优先级"""
        for field in priority:
            date_str = node.get(field)
            if date_str and isinstance(date_str, str) and date_str.isdigit():
                return int(date_str)
        return None
    
    def get_person_works(self, person_id):
        """获取某个音乐人的所有作品（按角色分类）"""
        works = defaultdict(list)  # role -> [work_nodes]
        
        for edge_type, target_id in self.get_edges_from(person_id):
            if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                target_node = self.get_node(target_id)
                if target_node and target_node.get('Node Type') in ['Song', 'Album']:
                    works[edge_type].append(target_node)
        
        return works
    
    def get_person_albums(self, person_id):
        """获取音乐人参与的专辑（通过共享Person推断）"""
        # 获取该音乐人的所有Album
        person_albums = []
        for edge_type, target_id in self.get_edges_from(person_id):
            if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                target_node = self.get_node(target_id)
                if target_node and target_node.get('Node Type') == 'Album':
                    person_albums.append((edge_type, target_node))
        
        return person_albums
    
    def get_album_songs(self, album_id, person_id=None):
        """推断专辑包含的歌曲
        策略：找到同一Person在同一时间段创作的Song
        """
        album = self.get_node(album_id)
        if not album or album.get('Node Type') != 'Album':
            return []
        
        album_date = self.extract_date(album)
        album_genre = album.get('genre')
        
        # 如果指定了person_id，只找该音乐人的歌曲
        if person_id:
            person_songs = []
            for edge_type, target_id in self.get_edges_from(person_id):
                if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                    target_node = self.get_node(target_id)
                    if target_node and target_node.get('Node Type') == 'Song':
                        song_date = self.extract_date(target_node)
                        song_genre = target_node.get('genre')
                        
                        # 判断是否属于该专辑：时间相近且流派相同
                        if song_date and album_date:
                            if abs(song_date - album_date) <= 2 and song_genre == album_genre:
                                person_songs.append(target_node)
            return person_songs
        
        # 否则，找到参与该专辑的所有Person，然后找他们的Song
        all_songs = []
        album_persons = []
        for edge_type, source_id in self.get_edges_to(album_id):
            if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                album_persons.append(source_id)
        
        for person_id in album_persons:
            for edge_type, target_id in self.get_edges_from(person_id):
                if edge_type in ['PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf']:
                    target_node = self.get_node(target_id)
                    if target_node and target_node.get('Node Type') == 'Song':
                        song_date = self.extract_date(target_node)
                        song_genre = target_node.get('genre')
                        
                        if song_date and album_date:
                            if abs(song_date - album_date) <= 2 and song_genre == album_genre:
                                all_songs.append(target_node)
        
        return all_songs


if __name__ == '__main__':
    # 测试数据预处理
    processor = MusicGraphProcessor('Topic1_graph.json')
    
    # 测试获取节点
    print("\n测试：获取第一个Person节点")
    persons = processor.get_nodes_by_type('Person')
    if persons:
        person = persons[0]
        print(f"  姓名: {person.get('name')}")
        print(f"  ID: {person['id']}")
        
        # 获取该音乐人的作品
        works = processor.get_person_works(person['id'])
        print(f"  作品数: {sum(len(w) for w in works.values())}")
        for role, work_list in works.items():
            print(f"    {role}: {len(work_list)} 个作品")


















