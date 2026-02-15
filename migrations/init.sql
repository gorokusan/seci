-- SECIモデル知識マッピングツール データベース初期化スクリプト

-- 拡張機能の有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文検索用

-- セッションテーブル
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET
);

-- SECIカテゴリ定義
CREATE TYPE seci_category AS ENUM ('socialization', 'externalization', 'combination', 'internalization');

-- 知識ノードテーブル
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category seci_category NOT NULL,
    metadata JSONB DEFAULT '{}',
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- ノード間の接続テーブル
CREATE TABLE IF NOT EXISTS node_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    connection_type VARCHAR(50) DEFAULT 'related',
    strength INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_node_id, target_node_id)
);

-- 分析メトリクステーブル
CREATE TABLE IF NOT EXISTS analytics_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL,
    metric_value JSONB NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- アクティビティログテーブル
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(100),
    target_id UUID,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- タグテーブル
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#6C757D',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ノード-タグの関連テーブル
CREATE TABLE IF NOT EXISTS node_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, tag_id)
);

-- ノードのバージョン履歴テーブル
CREATE TABLE IF NOT EXISTS node_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category seci_category NOT NULL,
    metadata JSONB DEFAULT '{}',
    version_number INTEGER NOT NULL,
    changed_by VARCHAR(100),
    change_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- いいね・スターテーブル
CREATE TABLE IF NOT EXISTS node_reactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    reaction_type VARCHAR(20) NOT NULL, -- 'like', 'star', 'bookmark'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, session_id, reaction_type)
);

-- コメントテーブル
CREATE TABLE IF NOT EXISTS node_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    parent_comment_id UUID REFERENCES node_comments(id) ON DELETE CASCADE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 接続メタデータの拡張（双方向リンク情報）
ALTER TABLE node_connections
    ADD COLUMN IF NOT EXISTS is_bidirectional BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS relationship_label VARCHAR(100);

-- ビュー: ノード統計
CREATE OR REPLACE VIEW node_statistics AS
SELECT
    kn.id as node_id,
    kn.title,
    kn.category,
    COUNT(DISTINCT nt.tag_id) as tag_count,
    COUNT(DISTINCT nr.id) FILTER (WHERE nr.reaction_type = 'like') as like_count,
    COUNT(DISTINCT nr2.id) FILTER (WHERE nr2.reaction_type = 'star') as star_count,
    COUNT(DISTINCT nr3.id) FILTER (WHERE nr3.reaction_type = 'bookmark') as bookmark_count,
    COUNT(DISTINCT nc.id) FILTER (WHERE nc.is_deleted = FALSE) as comment_count,
    COUNT(DISTINCT nv.id) as version_count
FROM knowledge_nodes kn
LEFT JOIN node_tags nt ON kn.id = nt.node_id
LEFT JOIN node_reactions nr ON kn.id = nr.node_id AND nr.reaction_type = 'like'
LEFT JOIN node_reactions nr2 ON kn.id = nr2.node_id AND nr2.reaction_type = 'star'
LEFT JOIN node_reactions nr3 ON kn.id = nr3.node_id AND nr3.reaction_type = 'bookmark'
LEFT JOIN node_comments nc ON kn.id = nc.node_id
LEFT JOIN node_versions nv ON kn.id = nv.node_id
WHERE kn.is_deleted = FALSE
GROUP BY kn.id, kn.title, kn.category;

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_sessions_key ON sessions(session_key);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_session ON knowledge_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_category ON knowledge_nodes(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_created ON knowledge_nodes(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_search ON knowledge_nodes USING gin(to_tsvector('simple', title || ' ' || COALESCE(description, '')));
CREATE INDEX IF NOT EXISTS idx_node_connections_source ON node_connections(source_node_id);
CREATE INDEX IF NOT EXISTS idx_node_connections_target ON node_connections(target_node_id);
CREATE INDEX IF NOT EXISTS idx_analytics_session ON analytics_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_session ON activity_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);

-- インデックスの追加
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_node_tags_node ON node_tags(node_id);
CREATE INDEX IF NOT EXISTS idx_node_tags_tag ON node_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_node_versions_node ON node_versions(node_id);
CREATE INDEX IF NOT EXISTS idx_node_versions_created ON node_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_node_reactions_node ON node_reactions(node_id);
CREATE INDEX IF NOT EXISTS idx_node_reactions_session ON node_reactions(session_id);
CREATE INDEX IF NOT EXISTS idx_node_comments_node ON node_comments(node_id);
CREATE INDEX IF NOT EXISTS idx_node_comments_created ON node_comments(created_at);


-- トリガー関数: updated_atの自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガーの作成
DROP TRIGGER IF EXISTS update_knowledge_nodes_updated_at ON knowledge_nodes;
CREATE TRIGGER update_knowledge_nodes_updated_at
    BEFORE UPDATE ON knowledge_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ビュー: セッション統計
CREATE OR REPLACE VIEW session_statistics AS
SELECT 
    s.id as session_id,
    s.session_key,
    COUNT(DISTINCT kn.id) as total_nodes,
    COUNT(DISTINCT CASE WHEN kn.category = 'socialization' THEN kn.id END) as socialization_count,
    COUNT(DISTINCT CASE WHEN kn.category = 'externalization' THEN kn.id END) as externalization_count,
    COUNT(DISTINCT CASE WHEN kn.category = 'combination' THEN kn.id END) as combination_count,
    COUNT(DISTINCT CASE WHEN kn.category = 'internalization' THEN kn.id END) as internalization_count,
    COUNT(DISTINCT nc.id) as total_connections,
    s.created_at,
    s.last_activity
FROM sessions s
LEFT JOIN knowledge_nodes kn ON s.id = kn.session_id AND kn.is_deleted = FALSE
LEFT JOIN node_connections nc ON kn.id = nc.source_node_id
GROUP BY s.id, s.session_key, s.created_at, s.last_activity;

-- ビュー: ノード統計
CREATE OR REPLACE VIEW node_statistics AS
SELECT 
    kn.id as node_id,
    kn.title,
    kn.category,
    COUNT(DISTINCT nt.tag_id) as tag_count,
    COUNT(DISTINCT nr.id) FILTER (WHERE nr.reaction_type = 'like') as like_count,
    COUNT(DISTINCT nr2.id) FILTER (WHERE nr2.reaction_type = 'star') as star_count,
    COUNT(DISTINCT nr3.id) FILTER (WHERE nr3.reaction_type = 'bookmark') as bookmark_count,
    COUNT(DISTINCT nc.id) FILTER (WHERE nc.is_deleted = FALSE) as comment_count,
    COUNT(DISTINCT nv.id) as version_count
FROM knowledge_nodes kn
LEFT JOIN node_tags nt ON kn.id = nt.node_id
LEFT JOIN node_reactions nr ON kn.id = nr.node_id AND nr.reaction_type = 'like'
LEFT JOIN node_reactions nr2 ON kn.id = nr2.node_id AND nr2.reaction_type = 'star'
LEFT JOIN node_reactions nr3 ON kn.id = nr3.node_id AND nr3.reaction_type = 'bookmark'
LEFT JOIN node_comments nc ON kn.id = nc.node_id
LEFT JOIN node_versions nv ON kn.id = nv.node_id
WHERE kn.is_deleted = FALSE
GROUP BY kn.id, kn.title, kn.category;

-- トリガー: コメント更新時刻の自動更新
DROP TRIGGER IF EXISTS update_node_comments_updated_at ON node_comments;
CREATE TRIGGER update_node_comments_updated_at
    BEFORE UPDATE ON node_comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- コメント
COMMENT ON TABLE sessions IS 'ユーザーセッション管理テーブル';
COMMENT ON TABLE knowledge_nodes IS 'SECIモデルの知識ノード';
COMMENT ON TABLE node_connections IS 'ノード間の関連性';
COMMENT ON TABLE analytics_metrics IS '分析メトリクス';
COMMENT ON TABLE activity_logs IS 'ユーザーアクティビティログ';

-- 初期データの挿入（オプション）
-- サンプルデータを追加する場合はここに記述

COMMIT;
