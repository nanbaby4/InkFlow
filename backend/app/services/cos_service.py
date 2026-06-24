"""腾讯云 COS 对象存储服务"""

import uuid
import io
import httpx
from datetime import datetime
from qcloud_cos import CosConfig, CosS3Client

from app.config import settings


class CosService:
    """腾讯云 COS 对象存储服务"""

    def __init__(self):
        config = CosConfig(
            Region=settings.tencent_cos_region,
            SecretId=settings.tencent_cos_secret_id,
            SecretKey=settings.tencent_cos_secret_key,
        )
        self.client = CosS3Client(config)
        self.bucket = settings.tencent_cos_bucket
        self.domain = settings.tencent_cos_domain

    def _generate_key(self, filename: str, folder: str = "article-images") -> str:
        """生成 COS 对象 Key"""
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        if "?" in ext:
            ext = ext.split("?")[0]
        if len(ext) > 5:
            ext = "jpg"
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4()).replace("-", "")[:12]
        return f"{folder}/{date_str}/{unique_id}.{ext}"

    def _get_public_url(self, key: str) -> str:
        """获取公开访问 URL"""
        if self.domain:
            domain = self.domain.rstrip("/")
            return f"{domain}/{key}"
        return f"https://{self.bucket}.cos.{settings.tencent_cos_region}.myqcloud.com/{key}"

    def upload_bytes(
        self,
        data: bytes,
        filename: str = "image.jpg",
        content_type: str = "image/jpeg",
        folder: str = "article-images",
    ) -> str:
        """上传字节数据到 COS

        Args:
            data: 图片字节数据
            filename: 文件名
            content_type: MIME 类型
            folder: COS 中的文件夹路径

        Returns:
            公开访问 URL
        """
        key = self._generate_key(filename, folder)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return self._get_public_url(key)

    async def upload_from_url(
        self,
        image_url: str,
        filename: str = "image.jpg",
        folder: str = "article-images",
    ) -> str:
        """从 URL 下载图片并上传到 COS

        Args:
            image_url: 图片来源 URL
            filename: 文件名
            folder: COS 中的文件夹路径

        Returns:
            COS 公开访问 URL
        """
        # 推断文件扩展名
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http_client:
                response = await http_client.get(image_url)
                response.raise_for_status()
                data = response.content
                content_type = response.headers.get("content-type", "image/jpeg")

                # 从 Content-Type 推断扩展名
                if "png" in content_type:
                    if not filename.endswith(".png"):
                        filename = filename.rsplit(".", 1)[0] + ".png" if "." in filename else "image.png"
                elif "svg" in content_type:
                    if not filename.endswith(".svg"):
                        filename = filename.rsplit(".", 1)[0] + ".svg" if "." in filename else "image.svg"
                elif "webp" in content_type:
                    if not filename.endswith(".webp"):
                        filename = filename.rsplit(".", 1)[0] + ".webp" if "." in filename else "image.webp"

                return self.upload_bytes(data, filename, content_type, folder)
        except Exception:
            # 如果下载失败，返回原始 URL
            return image_url

    def upload_svg_as_png(
        self,
        svg_content: str,
        filename: str = "diagram",
        folder: str = "article-images",
    ) -> str:
        """上传 SVG 内容（以 SVG 格式存储）

        Args:
            svg_content: SVG 字符串
            filename: 文件名（不含扩展名）
            folder: COS 中的文件夹路径

        Returns:
            公开访问 URL
        """
        key = self._generate_key(f"{filename}.svg", folder)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=svg_content.encode("utf-8"),
            ContentType="image/svg+xml",
        )
        return self._get_public_url(key)
