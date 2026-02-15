"""
データ自動クリーンアップサービス
180日間無操作のデータを自動削除
"""
import os
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupService:
    """データクリーンアップサービス"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.redis_url = os.getenv('REDIS_URL')
        self.retention_days = int(os.getenv('DATA_RETENTION_DAYS', 180))
        self.cleanup_interval = int(os.getenv('CLEANUP_INTERVAL', 86400))  # デフォルト24時間
        
        # データベース接続
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Redis接続
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
    
    def cleanup_old_sessions(self):
        """古いセッションデータの削除"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        session = self.Session()
        try:
            # 削除対象のセッション数を取得
            count_query = text("""
                SELECT COUNT(*) FROM sessions
                WHERE last_activity < :cutoff_date
            """)
            result = session.execute(count_query, {'cutoff_date': cutoff_date})
            count = result.scalar()
            
            if count > 0:
                logger.info(f"削除対象セッション: {count}件")
                
                # セッション削除（カスケード削除で関連データも削除）
                delete_query = text("""
                    DELETE FROM sessions
                    WHERE last_activity < :cutoff_date
                """)
                session.execute(delete_query, {'cutoff_date': cutoff_date})
                session.commit()
                
                logger.info(f"セッション削除完了: {count}件")
            else:
                logger.info("削除対象のセッションはありません")
        
        except Exception as e:
            logger.error(f"セッション削除エラー: {str(e)}")
            session.rollback()
        finally:
            session.close()
    
    def cleanup_redis_cache(self):
        """古いRedisキャッシュの削除"""
        try:
            # セッション関連のキャッシュをスキャン
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match='session:*',
                    count=100
                )
                
                for key in keys:
                    ttl = self.redis_client.ttl(key)
                    # TTLが設定されていないか、有効期限切れのキーを削除
                    if ttl == -1 or ttl == -2:
                        self.redis_client.delete(key)
                        deleted_count += 1
                
                if cursor == 0:
                    break
            
            if deleted_count > 0:
                logger.info(f"Redisキャッシュ削除: {deleted_count}件")
            else:
                logger.info("削除対象のRedisキャッシュはありません")
        
        except Exception as e:
            logger.error(f"Redisキャッシュ削除エラー: {str(e)}")
    
    def cleanup_old_activity_logs(self):
        """古いアクティビティログの削除（90日以上）"""
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        session = self.Session()
        try:
            delete_query = text("""
                DELETE FROM activity_logs
                WHERE created_at < :cutoff_date
            """)
            result = session.execute(delete_query, {'cutoff_date': cutoff_date})
            session.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"アクティビティログ削除: {deleted_count}件")
        
        except Exception as e:
            logger.error(f"アクティビティログ削除エラー: {str(e)}")
            session.rollback()
        finally:
            session.close()
    
    def cleanup_orphaned_analytics(self):
        """孤立した分析メトリクスの削除"""
        session = self.Session()
        try:
            delete_query = text("""
                DELETE FROM analytics_metrics
                WHERE session_id NOT IN (SELECT id FROM sessions)
            """)
            result = session.execute(delete_query)
            session.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"孤立分析メトリクス削除: {deleted_count}件")
        
        except Exception as e:
            logger.error(f"孤立分析メトリクス削除エラー: {str(e)}")
            session.rollback()
        finally:
            session.close()
    
    def run_cleanup(self):
        """クリーンアップ実行"""
        logger.info("=" * 50)
        logger.info("データクリーンアップ開始")
        logger.info(f"保持期間: {self.retention_days}日")
        logger.info("=" * 50)
        
        # 各クリーンアップ処理を実行
        self.cleanup_old_sessions()
        self.cleanup_redis_cache()
        self.cleanup_old_activity_logs()
        self.cleanup_orphaned_analytics()
        
        logger.info("=" * 50)
        logger.info("データクリーンアップ完了")
        logger.info("=" * 50)
    
    def run(self):
        """サービス起動"""
        logger.info(f"クリーンアップサービス起動")
        logger.info(f"実行間隔: {self.cleanup_interval}秒")
        logger.info(f"データ保持期間: {self.retention_days}日")
        
        while True:
            try:
                self.run_cleanup()
                logger.info(f"次回実行まで {self.cleanup_interval}秒待機")
                time.sleep(self.cleanup_interval)
            except KeyboardInterrupt:
                logger.info("クリーンアップサービス停止")
                break
            except Exception as e:
                logger.error(f"予期しないエラー: {str(e)}")
                time.sleep(60)  # エラー時は1分待機


if __name__ == '__main__':
    service = CleanupService()
    service.run()
