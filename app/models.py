"""
データベースモデル定義
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text
import uuid
import enum

Base = declarative_base()


class SECICategory(enum.Enum):
    """SECIモデルのカテゴリ"""
    SOCIALIZATION = 'socialization'  # 共同化
    # socialization ='socialization'  # 共同化
    EXTERNALIZATION = 'externalization'  # 表出化
    COMBINATION = 'combination'  # 連結化
    INTERNALIZATION = 'internalization'  # 内面化


class Session(Base):
    """セッション管理テーブル"""
    __tablename__ = 'sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    user_agent = Column(Text)
    ip_address = Column(INET)
    
    # リレーションシップ
    knowledge_nodes = relationship('KnowledgeNode', back_populates='session', cascade='all, delete-orphan')
    analytics = relationship('AnalyticsMetric', back_populates='session', cascade='all, delete-orphan')
    activities = relationship('ActivityLog', back_populates='session', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'session_key': self.session_key,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }


class KnowledgeNode(Base):
    """知識ノードテーブル"""
    __tablename__ = 'knowledge_nodes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    # category = Column(Enum(SECICategory), nullable=False, index=True)
    category = Column(
            Enum(
                'socialization',
                'externalization',
                'combination',
                'internalization',
                name = 'seci_category',
            ),
            nullable=False,
            index=True,
         )
    data_metadata = Column('metadata', JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    # リレーションシップ
    session = relationship('Session', back_populates='knowledge_nodes')
    outgoing_connections = relationship(
        'NodeConnection',
        foreign_keys='NodeConnection.source_node_id',
        back_populates='source_node',
        cascade='all, delete-orphan'
    )
    incoming_connections = relationship(
        'NodeConnection',
        foreign_keys='NodeConnection.target_node_id',
        back_populates='target_node',
        cascade='all, delete-orphan'
    )

    node_tags = relationship('NodeTag', back_populates='node', cascade='all, delete-orphan')
    versions = relationship(
            'NodeVersion',
            back_populates='node',
            cascade='all, delete-orphan',
            order_by='NodeVersion.version_number.desc()',
            )
    reactions = relationship('NodeReaction', back_populates='node', cascade='all, delete-orphan')
    comments = relationship('NodeComment', back_populates='node', cascade='all, delete-orphan')
    
    def to_dict(self, include_connections=False):
        data = {
            'id': str(self.id),
            'session_id': str(self.session_id),
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'metadata': self.data_metadata,
            'position': {
                'x': self.position_x,
                'y': self.position_y
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_connections:
            data['connections'] = {
                'outgoing': [conn.to_dict() for conn in self.outgoing_connections],
                'incoming': [conn.to_dict() for conn in self.incoming_connections]
            }
        
        return data


class NodeConnection(Base):
    """ノード間接続テーブル"""
    __tablename__ = 'node_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_type = Column(String(50), default='related')
    strength = Column(Integer, default=1)
    data_metadata = Column('metadata', JSONB, server_default=text("'{}'::jsonb"), nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    source_node = relationship('KnowledgeNode', foreign_keys=[source_node_id], back_populates='outgoing_connections')
    target_node = relationship('KnowledgeNode', foreign_keys=[target_node_id], back_populates='incoming_connections')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'source_id': str(self.source_node_id),
            'target_id': str(self.target_node_id),
            'connection_type': self.connection_type,
            'strength': self.strength,
            'metadata': self.data_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AnalyticsMetric(Base):
    """分析メトリクステーブル"""
    __tablename__ = 'analytics_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(JSONB, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    session = relationship('Session', back_populates='analytics')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'session_id': str(self.session_id),
            'metric_type': self.metric_type,
            'metric_value': self.metric_value,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


class ActivityLog(Base):
    """アクティビティログテーブル"""
    __tablename__ = 'activity_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    target_type = Column(String(100))
    target_id = Column(UUID(as_uuid=True))
    details = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # リレーションシップ
    session = relationship('Session', back_populates='activities')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'session_id': str(self.session_id),
            'action_type': self.action_type,
            'target_type': self.target_type,
            'target_id': str(self.target_id) if self.target_id else None,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 既存のmodels.pyに以下のクラスを追加

class Tag(Base):
    """タグマスター"""
    __tablename__ = 'tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default='#6C757D')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    node_tags = relationship('NodeTag', back_populates='tag', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NodeTag(Base):
    """ノード-タグ関連"""
    __tablename__ = 'node_tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    node = relationship('KnowledgeNode', back_populates='node_tags')
    tag = relationship('Tag', back_populates='node_tags')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'node_id': str(self.node_id),
            'tag_id': str(self.tag_id),
            'tag': self.tag.to_dict() if self.tag else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NodeVersion(Base):
    """ノードのバージョン履歴"""
    __tablename__ = 'node_versions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(
            Enum(
                'socialization',
                'externalization',
                'combinataion',
                'internalization',
                name='seci_category',
                ), 
            nullable=False,
            )
    data_metadata = Column(
            'metadata',
            JSONB,
            server_default=text("'{}'::jsonb"),
            nullable=False,
            )

    version_number = Column(Integer, nullable=False)
    changed_by = Column(String(100))
    change_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # リレーションシップ
    node = relationship('KnowledgeNode', back_populates='versions')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'node_id': str(self.node_id),
            'title': self.title,
            'description': self.description,
            'category': self.category.value,
            'metadata': self.metadata,
            'version_number': self.version_number,
            'changed_by': self.changed_by,
            'change_description': self.change_description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NodeReaction(Base):
    """いいね・スター・ブックマーク"""
    __tablename__ = 'node_reactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    reaction_type = Column(String(20), nullable=False)  # 'like', 'star', 'bookmark'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    node = relationship('KnowledgeNode', back_populates='reactions')
    session = relationship('Session')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'node_id': str(self.node_id),
            'session_id': str(self.session_id),
            'reaction_type': self.reaction_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NodeComment(Base):
    """ノードへのコメント"""
    __tablename__ = 'node_comments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    comment_text = Column(Text, nullable=False)
    parent_comment_id = Column(
            UUID(as_uuid=True),
            ForeignKey('node_comments.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        )
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    node = relationship('KnowledgeNode', back_populates='comments')
    session = relationship('Session')
    parent_comment = relationship('NodeComment', remote_side=[id], backref='replies')
    
    def to_dict(self, include_replies=False):
        data = {
            'id': str(self.id),
            'node_id': str(self.node_id),
            'session_id': str(self.session_id),
            'comment_text': self.comment_text,
            'parent_comment_id': str(self.parent_comment_id) if self.parent_comment_id else None,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_replies:
            data['replies'] = [reply.to_dict() for reply in self.replies if not reply.is_deleted]
        
        return data
