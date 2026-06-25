"""文章 DB 操作服务"""

import json
from datetime import datetime
from typing import Optional

from databases import Database
from sqlalchemy import and_, func, select

from app.models.article import Article
from app.models.enums import ArticleStatusEnum


class ArticleService:
    """文章 DB CRUD 服务"""

    def __init__(self, db: Database):
        self.db = db

    async def create_article(
        self,
        task_id: str,
        user_id: int,
        topic: str,
    ) -> None:
        """创建文章记录（PENDING 状态）"""
        query = """
            INSERT INTO article (taskId, userId, topic, status)
            VALUES (:taskId, :userId, :topic, :status)
        """
        await self.db.execute(
            query=query,
            values={
                "taskId": task_id,
                "userId": user_id,
                "topic": topic,
                "status": ArticleStatusEnum.PENDING.value,
            },
        )

    async def mark_processing(self, task_id: str) -> None:
        """标记为处理中"""
        query = "UPDATE article SET status = :status WHERE taskId = :taskId"
        await self.db.execute(
            query=query,
            values={
                "taskId": task_id,
                "status": ArticleStatusEnum.PROCESSING.value,
            },
        )

    async def save_result(
        self,
        task_id: str,
        *,
        main_title: Optional[str] = None,
        sub_title: Optional[str] = None,
        outline: Optional[str] = None,
        content: Optional[str] = None,
        full_content: Optional[str] = None,
        cover_image: Optional[str] = None,
        images: Optional[str] = None,
    ) -> None:
        """保存生成结果，标记为 COMPLETED"""
        query = """
            UPDATE article SET
                status = :status,
                mainTitle = :mainTitle,
                subTitle = :subTitle,
                outline = :outline,
                content = :content,
                fullContent = :fullContent,
                coverImage = :coverImage,
                images = :images,
                completedTime = :completedTime,
                updateTime = NOW()
            WHERE taskId = :taskId
        """
        await self.db.execute(
            query=query,
            values={
                "taskId": task_id,
                "status": ArticleStatusEnum.COMPLETED.value,
                "mainTitle": main_title,
                "subTitle": sub_title,
                "outline": outline,
                "content": content,
                "fullContent": full_content,
                "coverImage": cover_image,
                "images": images,
                "completedTime": datetime.now(),
            },
        )

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        """标记为失败"""
        query = """
            UPDATE article SET
                status = :status,
                errorMessage = :errorMessage,
                updateTime = NOW()
            WHERE taskId = :taskId
        """
        await self.db.execute(
            query=query,
            values={
                "taskId": task_id,
                "status": ArticleStatusEnum.FAILED.value,
                "errorMessage": error_message,
            },
        )

    async def get_by_task_id(self, task_id: str) -> Optional[dict]:
        """根据 taskId 查询文章"""
        query = select(Article).where(Article.task_id == task_id)
        row = await self.db.fetch_one(query)
        return dict(row) if row else None

    async def list_by_user(
        self, user_id: int, current: int = 1, page_size: int = 10
    ) -> tuple[list[dict], int]:
        """分页查询用户的文章列表"""
        conditions = [
            Article.user_id == user_id,
            Article.is_delete == 0,
        ]

        count_query = select(func.count(Article.id)).where(and_(*conditions))
        total = await self.db.fetch_val(count_query)

        offset = (current - 1) * page_size
        query = (
            select(Article)
            .where(and_(*conditions))
            .order_by(Article.create_time.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = await self.db.fetch_all(query)

        return [dict(row) for row in rows], total

    async def soft_delete(self, article_id: int, user_id: int) -> bool:
        """软删除文章（仅允许作者本人删除）"""
        query = select(Article).where(
            and_(
                Article.id == article_id,
                Article.user_id == user_id,
                Article.is_delete == 0,
            )
        )
        article = await self.db.fetch_one(query)
        if not article:
            return False

        update_query = "UPDATE article SET isDelete = 1 WHERE id = :id"
        await self.db.execute(query=update_query, values={"id": article_id})
        return True
