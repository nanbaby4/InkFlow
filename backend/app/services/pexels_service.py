"""Pexels 图片搜索服务"""

import httpx
from typing import Optional

from app.config import settings


class PexelsService:
    """Pexels 图片搜索服务"""

    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self):
        self.api_key = settings.pexels_api_key

    async def search_photos(
        self,
        query: str,
        per_page: int = 5,
        orientation: str = "landscape",
        size: str = "large",
    ) -> list[dict]:
        """搜索图片

        Args:
            query: 搜索关键词（英文）
            per_page: 返回数量
            orientation: 方向 landscape/portrait/square
            size: 尺寸 small/medium/large

        Returns:
            图片信息列表，每项包含 id, url, photographer, alt 等
        """
        if not self.api_key:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "size": size,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/search",
                headers=headers,
                params=params,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            photos = data.get("photos", [])
            return [
                {
                    "id": photo["id"],
                    "url": photo["src"]["large2x"] or photo["src"]["large"] or photo["src"]["original"],
                    "medium_url": photo["src"]["large"],
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "alt": photo.get("alt", query),
                    "avg_color": photo.get("avg_color"),
                }
                for photo in photos
            ]

    async def get_photo(self, photo_id: int) -> Optional[dict]:
        """获取单张图片信息"""
        if not self.api_key:
            return None

        headers = {"Authorization": self.api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/photos/{photo_id}",
                headers=headers,
            )
            if response.status_code != 200:
                return None

            photo = response.json()
            return {
                "id": photo["id"],
                "url": photo["src"]["large2x"] or photo["src"]["large"] or photo["src"]["original"],
                "medium_url": photo["src"]["large"],
                "photographer": photo["photographer"],
                "photographer_url": photo["photographer_url"],
                "alt": photo.get("alt", ""),
                "avg_color": photo.get("avg_color"),
            }
