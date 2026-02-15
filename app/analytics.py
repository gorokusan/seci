"""
分析エンジン - メトリクス分析と自動フロー提案
"""
from collections import defaultdict, Counter
from datetime import datetime
import math


class AnalyticsEngine:
    """知識創造プロセス分析エンジン"""
    
    # SECIモデルの理想的な遷移パターン
    SECI_FLOW_PATTERNS = {
        'socialization': ['externalization'],  # 共同化 → 表出化
        'externalization': ['combination'],     # 表出化 → 連結化
        'combination': ['internalization'],     # 連結化 → 内面化
        'internalization': ['socialization']    # 内面化 → 共同化
    }
    
    # カテゴリの日本語名
    CATEGORY_NAMES = {
        'socialization': '共同化',
        'externalization': '表出化',
        'combination': '連結化',
        'internalization': '内面化'
    }
    
    # カテゴリの色
    CATEGORY_COLORS = {
        'socialization': '#4A90E2',      # 青
        'externalization': '#7ED321',    # 緑
        'combination': '#F5A623',        # オレンジ
        'internalization': '#BD10E0'     # 紫
    }
    
    @staticmethod
    def calculate_category_distribution(nodes):
        """カテゴリ分布の計算"""
        if not nodes:
            return {}
        
        distribution = Counter([node['category'] for node in nodes])
        total = len(nodes)
        
        return {
            category: {
                'count': count,
                'percentage': round((count / total) * 100, 1),
                'name': AnalyticsEngine.CATEGORY_NAMES.get(category, category),
                'color': AnalyticsEngine.CATEGORY_COLORS.get(category, '#999999')
            }
            for category, count in distribution.items()
        }
    
    @staticmethod
    def calculate_balance_score(nodes):
        """知識創造プロセスのバランススコア計算"""
        if not nodes:
            return 0
        
        distribution = Counter([node['category'] for node in nodes])
        total = len(nodes)
        
        # 理想的な分布は25%ずつ
        ideal_percentage = 25.0
        
        # 各カテゴリの偏差を計算
        deviations = []
        for category in ['socialization', 'externalization', 'combination', 'internalization']:
            actual_percentage = (distribution.get(category, 0) / total) * 100
            deviation = abs(actual_percentage - ideal_percentage)
            deviations.append(deviation)
        
        # 平均偏差からスコアを計算（0-100）
        avg_deviation = sum(deviations) / len(deviations)
        balance_score = max(0, 100 - (avg_deviation * 2))
        
        return round(balance_score, 1)
    
    @staticmethod
    def analyze_flow_quality(nodes, connections):
        """フロー品質の分析"""
        if not nodes or not connections:
            return {
                'score': 0,
                'ideal_flows': 0,
                'total_flows': 0,
                'quality_percentage': 0
            }
        
        # ノードIDからカテゴリへのマッピング
        node_categories = {node['id']: node['category'] for node in nodes}
        
        ideal_flow_count = 0
        total_connections = len(connections)
        
        for conn in connections:
            source_category = node_categories.get(conn['source_id'])
            target_category = node_categories.get(conn['target_id'])
            
            if source_category and target_category:
                # 理想的な遷移パターンに合致するか確認
                expected_targets = AnalyticsEngine.SECI_FLOW_PATTERNS.get(source_category, [])
                if target_category in expected_targets:
                    ideal_flow_count += 1
        
        quality_percentage = (ideal_flow_count / total_connections * 100) if total_connections > 0 else 0
        
        return {
            'score': round(quality_percentage, 1),
            'ideal_flows': ideal_flow_count,
            'total_flows': total_connections,
            'quality_percentage': round(quality_percentage, 1)
        }
    
    @staticmethod
    def suggest_next_steps(nodes, connections):
        """次のステップの提案"""
        if not nodes:
            return [{
                'category': 'socialization',
                'title': '共同化から始めましょう',
                'description': '暗黙知の共有から知識創造を開始します。チームでの対話や経験の共有を記録してください。',
                'priority': 'high'
            }]
        
        # 現在のカテゴリ分布を取得
        distribution = Counter([node['category'] for node in nodes])
        total = len(nodes)
        
        # ノードIDからカテゴリへのマッピング
        node_categories = {node['id']: node['category'] for node in nodes}
        
        # 各カテゴリの接続状況を分析
        outgoing_connections = defaultdict(int)
        for conn in connections:
            source_category = node_categories.get(conn['source_id'])
            if source_category:
                outgoing_connections[source_category] += 1
        
        suggestions = []
        
        # 1. 不足しているカテゴリの提案
        for category in ['socialization', 'externalization', 'combination', 'internalization']:
            count = distribution.get(category, 0)
            percentage = (count / total) * 100
            
            if percentage < 20:  # 20%未満
                suggestions.append({
                    'category': category,
                    'title': f'{AnalyticsEngine.CATEGORY_NAMES[category]}の強化',
                    'description': f'現在{count}個（{percentage:.1f}%）です。バランスを取るために{AnalyticsEngine.CATEGORY_NAMES[category]}を追加してください。',
                    'priority': 'high' if percentage < 10 else 'medium'
                })
        
        # 2. フロー改善の提案
        for category, expected_targets in AnalyticsEngine.SECI_FLOW_PATTERNS.items():
            if category in distribution and distribution[category] > 0:
                # このカテゴリから期待される遷移先への接続があるか確認
                has_expected_flow = False
                for conn in connections:
                    source_cat = node_categories.get(conn['source_id'])
                    target_cat = node_categories.get(conn['target_id'])
                    if source_cat == category and target_cat in expected_targets:
                        has_expected_flow = True
                        break
                
                if not has_expected_flow:
                    for target_category in expected_targets:
                        suggestions.append({
                            'category': target_category,
                            'title': f'{AnalyticsEngine.CATEGORY_NAMES[category]}から{AnalyticsEngine.CATEGORY_NAMES[target_category]}への遷移',
                            'description': f'SECIモデルに従い、{AnalyticsEngine.CATEGORY_NAMES[category]}の知識を{AnalyticsEngine.CATEGORY_NAMES[target_category]}に発展させましょう。',
                            'priority': 'medium'
                        })
        
        # 3. 孤立ノードの接続提案
        connected_nodes = set()
        for conn in connections:
            connected_nodes.add(conn['source_id'])
            connected_nodes.add(conn['target_id'])
        
        isolated_count = len(nodes) - len(connected_nodes)
        if isolated_count > 0:
            suggestions.append({
                'category': None,
                'title': '孤立したノードの接続',
                'description': f'{isolated_count}個の孤立したノードがあります。他のノードと関連付けて知識の流れを作りましょう。',
                'priority': 'low'
            })
        
        # 優先度順にソート
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        suggestions.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return suggestions[:5]  # 上位5件のみ返す
    
    @staticmethod
    def calculate_completion_score(nodes, connections):
        """知識創造プロセスの完成度スコア"""
        if not nodes:
            return 0
        
        scores = []
        
        # 1. ノード数スコア（最大30点）
        node_count_score = min(30, (len(nodes) / 20) * 30)
        scores.append(node_count_score)
        
        # 2. バランススコア（最大30点）
        balance_score = AnalyticsEngine.calculate_balance_score(nodes)
        scores.append(balance_score * 0.3)
        
        # 3. フロー品質スコア（最大25点）
        flow_quality = AnalyticsEngine.analyze_flow_quality(nodes, connections)
        scores.append(flow_quality['score'] * 0.25)
        
        # 4. 接続密度スコア（最大15点）
        if len(nodes) > 1:
            max_possible_connections = len(nodes) * (len(nodes) - 1) / 2
            connection_density = (len(connections) / max_possible_connections) * 100
            density_score = min(15, connection_density * 0.15)
            scores.append(density_score)
        else:
            scores.append(0)
        
        total_score = sum(scores)
        return round(min(100, total_score), 1)
    
    @staticmethod
    def generate_insights(nodes, connections):
        """インサイト生成"""
        insights = []
        
        if not nodes:
            insights.append({
                'type': 'info',
                'message': '知識マッピングを始めましょう！まずは共同化から。'
            })
            return insights
        
        # カテゴリ分布の分析
        distribution = AnalyticsEngine.calculate_category_distribution(nodes)
        
        # バランスチェック
        balance_score = AnalyticsEngine.calculate_balance_score(nodes)
        if balance_score > 80:
            insights.append({
                'type': 'success',
                'message': f'素晴らしい！知識のバランスが取れています（スコア: {balance_score}）'
            })
        elif balance_score < 50:
            insights.append({
                'type': 'warning',
                'message': f'知識のバランスを改善しましょう（スコア: {balance_score}）'
            })
        
        # フロー品質チェック
        flow_quality = AnalyticsEngine.analyze_flow_quality(nodes, connections)
        if flow_quality['score'] > 70:
            insights.append({
                'type': 'success',
                'message': f'知識の流れが理想的です！（{flow_quality["ideal_flows"]}/{flow_quality["total_flows"]}が理想的な遷移）'
            })
        elif flow_quality['score'] < 40 and flow_quality['total_flows'] > 0:
            insights.append({
                'type': 'info',
                'message': 'SECIモデルの循環を意識した接続を増やしましょう'
            })
        
        # ノード数チェック
        if len(nodes) >= 50:
            insights.append({
                'type': 'success',
                'message': f'{len(nodes)}個のノードを作成しました！素晴らしい知識の蓄積です。'
            })
        elif len(nodes) < 5:
            insights.append({
                'type': 'info',
                'message': 'より多くの知識を追加して、全体像を充実させましょう'
            })
        
        return insights
