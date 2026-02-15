"""
ルート定義とAPIエンドポイント
"""
from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime
import uuid
from .models import (
        Session as UserSession,
        KnowledgeNode,
        NodeConnection,
        ActivityLog,
        SECICategory,
        Tag,
        NodeTag,
        NodeVersion,
        NodeReaction,
        NodeComment,
        )
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

Sitemap: https://localhost/sitemap.xml
""", 200, {'Content-Type': 'text/plain'}


@main_bp.route('/sitemap.xml')
def sitemap():
    """sitemap.xml"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://localhost/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://localhost/mapper</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://localhost/analytics</loc>
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
        cached = get_user_nodes_cache(session_id)
        if cached:
            return jsonify({
                'success': True,
                'nodes': cached.get('nodes', []),
                'connections': cached.get('connections', []),
                'cached': True,
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
            #category = SECICategory(data['category'])
            category_enum = SECICategory(data['category'])
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
            #details={'title': data['title'], 'category': data['category']}
            details={'title': data['title'], 'category': category_enum.value}
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
                category_enum = SECICategory(data['category'])
                # node.category = SECICategory(data['category'])
                node.category = category_enum.value
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '無効なカテゴリです'
                }), 400
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
                # node_query = node_query.filter_by(category=cat_enum)
                node_query = node_query.filter_by(category=cat_enum.value)
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

# routes.pyに以下のエンドポイントを追加

# ===== タグ関連 =====

@api_bp.route('/tags', methods=['GET'])
@require_session
def get_tags():
    """タグ一覧取得"""
    try:
        db = get_session()
        tags = db.query(Tag).all()
        
        return jsonify({
            'success': True,
            'tags': [tag.to_dict() for tag in tags]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/tags', methods=['POST'])
@require_session
def create_tag():
    """タグ作成"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'タグ名は必須です'}), 400
        
        db = get_session()
        
        # 既存タグチェック
        existing_tag = db.query(Tag).filter_by(name=data['name']).first()
        if existing_tag:
            return jsonify({'success': True, 'tag': existing_tag.to_dict()})
        
        # 新規作成
        new_tag = Tag(
            name=data['name'],
            color=data.get('color', '#6C757D')
        )
        
        db.add(new_tag)
        db.commit()
        
        return jsonify({
            'success': True,
            'tag': new_tag.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/nodes/<node_id>/tags', methods=['POST'])
@require_session
def add_tag_to_node(node_id):
    """ノードにタグを追加"""
    try:
        data = request.get_json()
        tag_id = data.get('tag_id')
        
        if not tag_id:
            return jsonify({'success': False, 'error': 'tag_idは必須です'}), 400
        
        db = get_session()
        
        # ノードの所有確認
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404
        
        # タグの存在確認
        tag = db.query(Tag).filter_by(id=tag_id).first()
        if not tag:
            return jsonify({'success': False, 'error': 'タグが見つかりません'}), 404
        
        # 既存の関連チェック
        existing = db.query(NodeTag).filter_by(
            node_id=node_id,
            tag_id=tag_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'このタグは既に追加されています'}), 400
        
        # 関連作成
        node_tag = NodeTag(node_id=node_id, tag_id=tag_id)
        db.add(node_tag)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({
            'success': True,
            'node_tag': node_tag.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/nodes/<node_id>/tags/<tag_id>', methods=['DELETE'])
@require_session
def remove_tag_from_node(node_id, tag_id):
    """ノードからタグを削除"""
    try:
        db = get_session()
        
        # ノードの所有確認
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404
        
        # 関連削除
        node_tag = db.query(NodeTag).filter_by(
            node_id=node_id,
            tag_id=tag_id
        ).first()
        
        if not node_tag:
            return jsonify({'success': False, 'error': 'タグの関連が見つかりません'}), 404
        
        db.delete(node_tag)
        db.commit()
        
        # キャッシュ無効化
        invalidate_user_cache(str(request.user_session.id))
        
        return jsonify({'success': True, 'message': 'タグを削除しました'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== バージョン履歴 =====

@api_bp.route('/nodes/<node_id>/versions', methods=['GET'])
@require_session
def get_node_versions(node_id):
    """ノードのバージョン履歴取得"""
    try:
        db = get_session()
        
        # ノードの所有確認
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404
        
        versions = db.query(NodeVersion).filter_by(
            node_id=node_id
        ).order_by(NodeVersion.version_number.desc()).all()
        
        return jsonify({
            'success': True,
            'versions': [v.to_dict() for v in versions]
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def create_node_version(db, node, change_description=''):
    """ノードのバージョンを作成（内部関数）"""
    # 最新のバージョン番号を取得
    latest_version = db.query(NodeVersion).filter_by(
        node_id=node.id
    ).order_by(NodeVersion.version_number.desc()).first()
    
    version_number = (latest_version.version_number + 1) if latest_version else 1
    
    if isinstance(node.category, str):
        category_enum = SECICategory(node.category)
    else:
        category_enum = node.category
    
    # バージョン作成
    version = NodeVersion(
        node_id=node.id,
        title=node.title,
        description=node.description,
        category=category_enum,
        data_metadata=node.data_metadata,
        version_number=version_number,
        change_description=change_description
    )
    
    db.add(version)
    return version


# ===== リアクション =====

@api_bp.route('/nodes/<node_id>/reactions', methods=['POST'])
@require_session
def add_reaction(node_id):
    """リアクション追加"""
    try:
        data = request.get_json()
        reaction_type = data.get('type')
        
        if reaction_type not in ['like', 'star', 'bookmark']:
            return jsonify({'success': False, 'error': '無効なリアクションタイプです'}), 400
        
        db = get_session()
        
        # ノードの存在確認
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            is_deleted=False
        ).first()
        
        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404
        
        # 既存のリアクションチェック
        existing = db.query(NodeReaction).filter_by(
            node_id=node_id,
            session_id=request.user_session.id,
            reaction_type=reaction_type
        ).first()
        
        if existing:
            # 既にリアクション済みなら削除（トグル）
            db.delete(existing)
            db.commit()
            return jsonify({'success': True, 'action': 'removed'})
        
        # リアクション追加
        reaction = NodeReaction(
            node_id=node_id,
            session_id=request.user_session.id,
            reaction_type=reaction_type
        )
        
        db.add(reaction)
        db.commit()
        
        return jsonify({
            'success': True,
            'action': 'added',
            'reaction': reaction.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/nodes/<node_id>/reactions', methods=['GET'])
@require_session
def get_node_reactions(node_id):
    """ノードのリアクション取得"""
    try:
        db = get_session()
        
        reactions = db.query(NodeReaction).filter_by(node_id=node_id).all()
        
        # リアクションタイプ別にカウント
        reaction_counts = {
            'likes': 0,
            'stars': 0,
            'bookmarks': 0
        }
        
        user_reactions = []
        
        for reaction in reactions:
            if reaction.reaction_type == 'like':
                reaction_counts['likes'] += 1
            elif reaction.reaction_type == 'star':
                reaction_counts['stars'] += 1
            elif reaction.reaction_type == 'bookmark':
                reaction_counts['bookmarks'] += 1
            
            # 自分のリアクション
            if reaction.session_id == request.user_session.id:
                user_reactions.append(reaction.reaction_type)
        
        return jsonify({
            'success': True,
            'counts': reaction_counts,
            'user_reactions': user_reactions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== コメント =====
# ===== コメント =====

@api_bp.route('/nodes/<node_id>/comments', methods=['GET'])
@require_session
def get_node_comments(node_id):
    """ノードのコメント取得"""
    try:
        db = get_session()

        # ノードの存在確認（自分のセッションのノードのみ）
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()

        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404

        # トップレベルコメントのみ取得（返信は `replies` としてネスト）
        comments = db.query(NodeComment).filter_by(
            node_id=node_id,
            parent_comment_id=None,
            is_deleted=False
        ).order_by(NodeComment.created_at.desc()).all()

        return jsonify({
            'success': True,
            'comments': [c.to_dict(include_replies=True) for c in comments]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/nodes/<node_id>/comments', methods=['POST'])
@require_session
def add_comment(node_id):
    """コメント追加"""
    try:
        data = request.get_json() or {}

        if not data.get('comment_text'):
            return jsonify({'success': False, 'error': 'コメント本文は必須です'}), 400

        db = get_session()

        # ノードの存在確認（自分のセッションのノードのみ）
        node = db.query(KnowledgeNode).filter_by(
            id=node_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()

        if not node:
            return jsonify({'success': False, 'error': 'ノードが見つかりません'}), 404

        parent_comment_id = data.get('parent_comment_id') or None

        # コメント作成
        comment = NodeComment(
            node_id=node_id,
            session_id=request.user_session.id,
            comment_text=data['comment_text'],
            parent_comment_id=parent_comment_id
        )

        db.add(comment)
        db.commit()

        return jsonify({'success': True, 'comment': comment.to_dict()}), 201

    except Exception as e:
        # ここで例外メッセージをそのまま返しているので、
        # "NodeComment object has no attribute 'title'" というエラーは
        # この try ブロック内のどこかで `comment.title` などを触っているサインです。
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/comments/<comment_id>', methods=['DELETE'])
@require_session
def delete_comment(comment_id):
    """コメント削除（論理削除）"""
    try:
        db = get_session()

        comment = db.query(NodeComment).filter_by(
            id=comment_id,
            session_id=request.user_session.id,
            is_deleted=False
        ).first()

        if not comment:
            return jsonify({'success': False, 'error': 'コメントが見つかりません'}), 404

        comment.is_deleted = True
        db.commit()

        return jsonify({'success': True, 'message': 'コメントを削除しました'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 既存のupdate_nodeエンドポイントを修正してバージョン履歴を作成
# update_node関数内のdb.commit()の前に以下を追加：

        # バージョン履歴の作成
        if any(key in data for key in ['title', 'description', 'category']):
            create_node_version(db, node, change_description='ノードを更新')

