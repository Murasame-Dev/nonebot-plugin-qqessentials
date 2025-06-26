"""
数据库操作模块
负责处理收藏消息的 SQLite 数据库操作
"""

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class CollectDatabase:
    """收藏消息数据库操作类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS collect_message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qq TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def add_collect_message(self, qq: str, message: str) -> bool:
        """
        添加收藏消息
        
        Args:
            qq: 用户QQ号
            message: 消息内容（文本内容）
            
        Returns:
            bool: 是否添加成功
        """
        try:
            timestamp = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO collect_message (qq, message, timestamp) VALUES (?, ?, ?)",
                    (qq, message, timestamp)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"添加收藏消息失败: {e}")
            return False
    
    async def get_collect_messages_by_qq(self, qq: str) -> List[Dict[str, Any]]:
        """
        根据QQ号获取收藏消息列表
        
        Args:
            qq: 用户QQ号
            
        Returns:
            List[Dict]: 收藏消息列表
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT id, message, timestamp, created_at FROM collect_message WHERE qq = ? ORDER BY timestamp DESC",
                    (qq,)
                )
                rows = await cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "message": row[1],  # 直接使用文本内容
                        "timestamp": row[2],
                        "created_at": row[3]
                    })
                return result
        except Exception as e:
            print(f"获取收藏消息失败: {e}")
            return []
    
    async def get_all_collect_messages(self) -> List[Dict[str, Any]]:
        """
        获取所有收藏消息
        
        Returns:
            List[Dict]: 所有收藏消息列表
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT id, qq, message, timestamp, created_at FROM collect_message ORDER BY timestamp DESC"
                )
                rows = await cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "qq": row[1],
                        "message": row[2],  # 直接使用文本内容
                        "timestamp": row[3],
                        "created_at": row[4]
                    })
                return result
        except Exception as e:
            print(f"获取所有收藏消息失败: {e}")
            return []
    
    async def delete_collect_message(self, message_id: int) -> bool:
        """
        删除收藏消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM collect_message WHERE id = ?", (message_id,))
                await db.commit()
            return True
        except Exception as e:
            print(f"删除收藏消息失败: {e}")
            return False
    
    async def get_collect_count_by_qq(self, qq: str) -> int:
        """
        获取用户收藏消息数量
        
        Args:
            qq: 用户QQ号
            
        Returns:
            int: 收藏消息数量
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM collect_message WHERE qq = ?", (qq,))
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            print(f"获取收藏消息数量失败: {e}")
            return 0


# 全局数据库实例
_db_instance: Optional[CollectDatabase] = None


def get_collect_db(data_path: str) -> CollectDatabase:
    """
    获取收藏数据库实例（单例模式）
    
    Args:
        data_path: 数据存储路径
        
    Returns:
        CollectDatabase: 数据库实例
    """
    global _db_instance
    if _db_instance is None:
        db_path = Path(data_path) / "collect" / "collect_message.db"
        _db_instance = CollectDatabase(str(db_path))
    return _db_instance
