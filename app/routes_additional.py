"""
ルート定義とAPIエンドポイント
"""
from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime
import uuid
from .models import Session as UserSession, KnowledgeNode, NodeConnection, ActivityLog, SECICategory
from .database import get_session
from .cache_manager import (
    get_session_id, get_user_nodes_cache, set_user_nodes_cache,
    invalidate_user_cache, get_cache
)
from .analytics import AnalyticsEngine
from functools import wraps

# ブループリント定義
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

# デコレーター: セッション確認
def require_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_key = get_session_id()
        
        # セッションの取得または作成
        db = get_session()
        user_session = db.query(UserSession).filter_by(session_key=session_key).first()
        
        if not user_session:
            user_session = UserSession(
                session_key=session_key,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            db.add(user_session)
            db.commit()
        else:
            # 最終アクティビティ時刻を更新
            user_session.last_activity = datetime.utcnow()
            db.commit()
        
        request.user_session = user_session
        return f(*args, **kwargs)
    return decorated_function


# ===== メインページ =====
@main_bp.route('/')
@require_session
def index():
    """トップページ"""
    return render_template('index.html')


@main_bp.route('/mapper')
@require_session
def mapper():
    """マッピングページ"""
    return render_template('mapper.html')


@main_bp.route('/analytics')
@require_session
def analytics():
    """分析ページ"""
    return render_template('analytics.html')


# ===== SEO対策用エンドポイント =====
@main_bp.route('/robots.txt')
def robots():
    """robots.txt"""
    return """User-agent: *
Allow: /
Disallow: /api/

Sitemap: https://seci-p6co.onrender.com/sitemap.xml
""", 200, {'Content-Type': 'text/plain'}


@main_bp.route('/sitemap.xml')
def sitemap():
    """sitemap.xml"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://seci-p6co.onrender.com/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://seci-p6co.onrender.com/mapper</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://seci-p6co.onrender.com/analytics</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>
""", 200, {'Content-Type': 'application/xml'}


# ===== API エンドポイント =====

@api_bp.route('/nodes', methods=['GET'])
@require_session
def get_nodes():
    """ノード一覧取得"""
    try:
        session_id = str(request.user_session.id)
        
        # キャッシュから取得を試みる
        #cached_nodes = get_user_nodes_cache(session_id)
        #if cached_nodes:
        #    return jsonify({
        #        'success': True,
        #        'nodes': cached_nodes,
        #        'cached': True
        #    })

        cached_data = get_user_nodes_cache(session_id)
        if cached_data:
            return jsonify({
                'success': True,
                **cached_data,
                'cached': True
                })
        
        # データベースから取得
        db = get_session()
        nodes = db.query(KnowledgeNode).filter_by(
            session_id=request.user_session.id,
            is_deleted=False
        ).all()
        
        # 接続情報も取得
        connections = db.query(NodeConnection).join(
            KnowledgeNode,
            NodeConnection.source_node_id == KnowledgeNode.id
        ).filter(
            KnowledgeNode.session_id == request.user_session.id,
            KnowledgeNode.is_deleted == False
        ).all()
        
        nodes_data = [node.to_dict() for node in nodes]
        connections_data = [conn.to_dict() for conn in connections]
        
        # キャッシュに保存
        result = {
            'nodes': nodes_data,
            'connections': connections_data
        }
        set_user_nodes_cache(session_id, result)
        
        return jsonify({
            'success': True,
            **result,
            'cached': False
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/nodes', methods=['POST'])
@require_session
def create_node():
    """ノード作成"""
    try:
        data = request.get_json()
        
        # バリデーション
        if not data.get('title'):
            return jsonify({
                'success': False,
                'error': 'タイトルは必須です'
            }), 400
        
        if not data.get('category'):
            return jsonify({
                'success': False,
                'error': 'カテゴリは必須です'
            }), 400
        
        # カテゴリの検証
        try:
            category = SECICategory(data['category'])
        except ValueError:
            return jsonify({
                'success': False,
                'error': '無効なカテゴリです'
            }), 400
        
        # ノード数制限チェック
        db = get_session()
        node_count = db.query(KnowledgeNode).filter_by(
            session_id=request.user_session.id,
            is_deleted=False
        ).count()
        
        from .config import Config
        if node_count >= Config.MAX_NODES_PER_USER:
            return jsonify({
                'success': False,
                'error': f'ノード数の上限（{Config.MAX_NODES_PER_USER}）に達しています'
            }), 400
        
        # ノード作成
        new_node = KnowledgeNode(
            session_id=request.user_session.id,
            title=data['title'],
            description=data.get('description', ''),
            #category=category,
            category=category_enum.value,
            position_x=data.get('position', {}).get('x', 0),
            position_y=data.get('position', {}).get('y', 0),
            data_metadata=data.get('metadata', {})
        )
        
        db.add(new_node)
        db.commit()
        
        # アクティビティログ
        log = ActivityLog(
            session_id=request.user_session.id,
            action_type='node_created',
            target_type='node',
            target_id=new_node.id,
            details={'title': data['title'], 'category': data['category']}
        )
        db.add(log)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'node': new_node.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/nodes/<node_id>', methods=['GET'])
@require_session
def get_node(node_id):
    """ノード詳細取得"""
    try:
        db = get_session()
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({
                'success': False,
                'error': 'ノードが見つかりません'
            }), 404
        
        return jsonify({
            'success': True,
            'node': node.to_dict(include_connections=True)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/nodes/<node_id>', methods=['PUT'])
@require_session
def update_node(node_id):
    """ノード更新"""
    try:
        data = request.get_json()
        
        db = get_session()
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({
                'success': False,
                'error': 'ノードが見つかりません'
            }), 404
        
        # 更新
        if 'title' in data:
            node.title = data['title']
        if 'description' in data:
            node.description = data['description']
        if 'category' in data:
            try:
                node.category = SECICategory(data['category'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '無効なカテゴリです'
                }), 400
            node.category = category_enum.value
        if 'position' in data:
            node.position_x = data['position'].get('x', node.position_x)
            node.position_y = data['position'].get('y', node.position_y)
        if 'metadata' in data:
            node.data_metadata = data['metadata']
        
        db.commit()
        
        # アクティビティログ
        log = ActivityLog(
            session_id=request.user_session.id,
            action_type='node_updated',
            target_type='node',
            target_id=node.id,
            details={'title': node.title}
        )
        db.add(log)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'node': node.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""
ルート定義の続き - この内容をroutes.pyの最後に追加してください
"""


@api_bp.route('/nodes/<node_id>', methods=['DELETE'])
@require_session
def delete_node(node_id):
    """ノード削除"""
    try:
        db = get_session()
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({
                'success': False,
                'error': 'ノードが見つかりません'
            }), 404
        
        # 論理削除
        node.is_deleted = True
        db.commit()
        
        # アクティビティログ
        log = ActivityLog(
            session_id=request.user_session.id,
            action_type='node_deleted',
            target_type='node',
            target_id=node.id,
            details={'title': node.title}
        )
        db.add(log)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'message': 'ノードを削除しました'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/connections', methods=['POST'])
@require_session
def create_connection():
    """接続作成"""
    try:
        data = request.get_json()
        
        # バリデーション
        if not data.get('source_id') or not data.get('target_id'):
            return jsonify({
                'success': False,
                'error': 'source_idとtarget_idは必須です'
            }), 400
        
        # ノードの存在確認
        db = get_session()
        source_node = db.query(KnowledgeNode).filter_by(
            id=data['source_id'],
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        target_node = db.query(KnowledgeNode).filter_by(
            id=data['target_id'],
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not source_node or not target_node:
            return jsonify({
                'success': False,
                'error': 'ノードが見つかりません'
            }), 404
        
        # 既存の接続チェック
        existing = db.query(NodeConnection).filter_by(
            source_node_id=data['source_id'],
            target_node_id=data['target_id']
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'この接続は既に存在します'
            }), 400
        
        # 接続作成
        connection = NodeConnection(
            source_node_id=data['source_id'],
            target_node_id=data['target_id'],
            connection_type=data.get('connection_type', 'related'),
            strength=data.get('strength', 1),
            data_metadata=data.get('metadata', {})
        )
        
        db.add(connection)
        db.commit()
        
        # アクティビティログ
        log = ActivityLog(
            session_id=request.user_session.id,
            action_type='connection_created',
            target_type='connection',
            target_id=connection.id
        )
        db.add(log)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'connection': connection.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/connections/<connection_id>', methods=['DELETE'])
@require_session
def delete_connection(connection_id):
    """接続削除"""
    try:
        db = get_session()
        
        # 接続の取得（セッション所有確認のため）
        connection = db.query(NodeConnection).join(
            KnowledgeNode,
            NodeConnection.source_node_id == KnowledgeNode.id
        ).filter(
            NodeConnection.id == connection_id,
            KnowledgeNode.session_id == request.user_session.id
        ).first()
        
        if not connection:
            return jsonify({
                'success': False,
                'error': '接続が見つかりません'
            }), 404
        
        db.delete(connection)
        db.commit()
        
        # アクティビティログ
        log = ActivityLog(
            session_id=request.user_session.id,
            action_type='connection_deleted',
            target_type='connection',
            target_id=connection_id
        )
        db.add(log)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'message': '接続を削除しました'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/search', methods=['GET'])
@require_session
def search_nodes():
    """ノード検索"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        
        db = get_session()
        
        # 基本クエリ
        node_query = db.query(KnowledgeNode).filter_by(
            session_id=request.user_session.id,
            is_deleted=False
        )
        
        # 検索条件
        if query:
            node_query = node_query.filter(
                (KnowledgeNode.title.ilike(f'%{query}%')) |
                (KnowledgeNode.description.ilike(f'%{query}%'))
            )
        
        if category:
            try:
                cat_enum = SECICategory(category)
                node_query = node_query.filter_by(category=cat_enum)
            except ValueError:
                pass
        
        nodes = node_query.all()
        
        return jsonify({
            'success': True,
            'nodes': [node.to_dict() for node in nodes],
            'count': len(nodes)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/analytics/summary', methods=['GET'])
@require_session
def get_analytics_summary():
    """分析サマリー取得"""
    try:
        db = get_session()
        
        # ノードと接続を取得
        nodes = db.query(KnowledgeNode).filter_by(
            session_id=request.user_session.id,
            is_deleted=False
        ).all()
        
        connections = db.query(NodeConnection).join(
            KnowledgeNode,
            NodeConnection.source_node_id == KnowledgeNode.id
        ).filter(
            KnowledgeNode.session_id == request.user_session.id,
            KnowledgeNode.is_deleted == False
        ).all()
        
        nodes_data = [node.to_dict() for node in nodes]
        connections_data = [conn.to_dict() for conn in connections]
        
        # 分析実行
        distribution = AnalyticsEngine.calculate_category_distribution(nodes_data)
        balance_score = AnalyticsEngine.calculate_balance_score(nodes_data)
        flow_quality = AnalyticsEngine.analyze_flow_quality(nodes_data, connections_data)
        completion_score = AnalyticsEngine.calculate_completion_score(nodes_data, connections_data)
        suggestions = AnalyticsEngine.suggest_next_steps(nodes_data, connections_data)
        insights = AnalyticsEngine.generate_insights(nodes_data, connections_data)
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_nodes': len(nodes_data),
                'total_connections': len(connections_data),
                'category_distribution': distribution,
                'balance_score': balance_score,
                'flow_quality': flow_quality,
                'completion_score': completion_score,
                'suggestions': suggestions,
                'insights': insights
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/export', methods=['GET'])
@require_session
def export_data():
    """データエクスポート"""
    try:
        format_type = request.args.get('format', 'json')
        
        db = get_session()
        
        # データ取得
        nodes = db.query(KnowledgeNode).filter_by(
            session_id=request.user_session.id,
            is_deleted=False
        ).all()
        
        connections = db.query(NodeConnection).join(
            KnowledgeNode,
            NodeConnection.source_node_id == KnowledgeNode.id
        ).filter(
            KnowledgeNode.session_id == request.user_session.id,
            KnowledgeNode.is_deleted == False
        ).all()
        
        nodes_data = [node.to_dict() for node in nodes]
        connections_data = [conn.to_dict() for conn in connections]
        
        if format_type == 'json':
            return jsonify({
                'success': True,
                'data': {
                    'nodes': nodes_data,
                    'connections': connections_data,
                    'exported_at': datetime.utcnow().isoformat()
                }
            })
        
        elif format_type == 'csv':
            import csv
            from io import StringIO
            
            # ノードCSV
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'title', 'description', 'category', 'created_at'])
            writer.writeheader()
            for node in nodes_data:
                writer.writerow({
                    'id': node['id'],
                    'title': node['title'],
                    'description': node['description'],
                    'category': node['category'],
                    'created_at': node['created_at']
                })
            
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=seci_nodes.csv'
            }
        
        else:
            return jsonify({
                'success': False,
                'error': '無効なフォーマットです'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/activity', methods=['GET'])
@require_session
def get_activity_log():
    """アクティビティログ取得"""
    try:
        limit = int(request.args.get('limit', 50))
        
        db = get_session()
        activities = db.query(ActivityLog).filter_by(
            session_id=request.user_session.id
        ).order_by(ActivityLog.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'activities': [activity.to_dict() for activity in activities]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
