"""文章路由 — SSE 流式生成 + CRUD"""

import asyncio
import json
import uuid

from databases import Database
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_db
from app.deps import require_login
from app.models.enums import SseMessageTypeEnum
from app.schemas.article import ArticleState
from app.schemas.common import BaseResponse, DeleteRequest
from app.schemas.user import LoginUserVO
from app.services.article_agent_service import ArticleAgentService
from app.services.article_service import ArticleService

router = APIRouter(prefix="/article", tags=["articleManage"])


# ── 请求模型 ──────────────────────────────────────────────────

class ArticleGenerateRequest(BaseModel):
    """文章生成请求"""
    topic: str = Field(..., min_length=1, max_length=500, description="选题")
    style: str = Field(default="", description="文章风格: tech/emotional/educational/humorous")
    user_description: str = Field(default="", alias="userDescription", max_length=1000, description="用户补充描述")

    class Config:
        populate_by_name = True


class ArticlePageRequest(BaseModel):
    """文章分页查询"""
    current: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50, alias="pageSize")

    class Config:
        populate_by_name = True


# ── SSE 工具函数 ──────────────────────────────────────────────

def _sse_frame(event: str, data: str = "") -> str:
    """
    构造一条 SSE 消息帧，要求每一条消息必须长这样：
    event: 事件名字
    data: 消息内容
    (这里必须有一个空行表示这条消息结束了)
    """
    # data 中的换行需逐行加前缀
    if data:
        lines = data.split("\n")
        framed = "".join(f"data: {line}\n" for line in lines)
        return f"event: {event}\n{framed}\n"
    return f"event: {event}\ndata: \n\n"


# ── 单例（模块级复用，避免每次请求重新初始化）────────────────

_agent_service: ArticleAgentService | None = None


def _get_agent_service() -> ArticleAgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = ArticleAgentService()
    return _agent_service


# ══════════════════════════════════════════════════════════════
#  端点
# ══════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_article(
    req: ArticleGenerateRequest,
    current_user: LoginUserVO = Depends(require_login),
    db: Database = Depends(get_db),
):
    """
    SSE 流式生成文章。

    事件类型（event 字段）：
    - AGENT1_COMPLETE       标题方案生成完毕
    - AGENT2_STREAMING      大纲逐 chunk 推送
    - AGENT2_COMPLETE       大纲生成完毕
    - AGENT3_STREAMING      正文逐 chunk 推送
    - AGENT3_COMPLETE       正文生成完毕
    - AGENT4_COMPLETE       配图需求分析完毕
    - IMAGE_COMPLETE        单张配图完成（data 为 JSON）
    - AGENT5_COMPLETE       全部配图完成
    - MERGE_COMPLETE        图文合成完毕
    - ALL_COMPLETE          全流程结束
    - ERROR                 异常（data 为错误信息）
    """
    article_service = ArticleService(db)
    agent_service = _get_agent_service()
    task_id = str(uuid.uuid4())

    # 1. 创建 DB 记录
    await article_service.create_article(
        task_id=task_id,
        user_id=current_user.id,
        topic=req.topic,
    )

    # 2. 构建初始状态
    state = ArticleState()
    state.task_id = task_id
    state.topic = req.topic
    state.style = req.style
    state.user_description = req.user_description

    # 3. Queue 桥接：回调 → 异步生成器
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    async def sse_handler(raw: str) -> None:
        """stream_handler 回调：拆解事件类型和数据"""
        if ":" in raw:
            # 流式消息：AGENT2_STREAMING:{" → event=AGENT2_STREAMING, data={
            # 非流式JSON：IMAGE_COMPLETE{"position":1,...}
            first_colon = raw.index(":")
            event_type = raw[:first_colon]
            payload = raw[first_colon + 1:]
        else:
            event_type = raw
            payload = ""
        await queue.put((event_type, payload))

    async def event_generator():
        """SSE 异步生成器"""
        # 发一条 START，携带 taskId
        yield _sse_frame("START", json.dumps({"taskId": task_id}))

        # 后台执行生成
        task = asyncio.create_task(
            agent_service.execute_article_generation(state, sse_handler)
        )
        await article_service.mark_processing(task_id)

        # 从 queue 消费事件，转发为 SSE 帧
        while True:
            try:
                event_type, payload = await asyncio.wait_for(
                    queue.get(), timeout=0.2
                )
                yield _sse_frame(event_type, payload)
            except asyncio.TimeoutError:
                if task.done():
                    break

        # 检查生成结果
        try:
            await task    #等task完成
        except Exception as e:
            await article_service.mark_failed(task_id, str(e))
            yield _sse_frame(SseMessageTypeEnum.ERROR.value, str(e))
            return

        # 4. 持久化结果
        try:
            await article_service.save_result(
                task_id=task_id,
                main_title=state.title.main_title if state.title else None,
                sub_title=state.title.sub_title if state.title else None,
                outline=json.dumps(
                    state.outline.model_dump() if state.outline else None,
                    ensure_ascii=False,
                ),
                content=state.content,
                full_content=state.full_content,
                cover_image=state.cover_image,
                images=json.dumps(
                    [img.model_dump(by_alias=True) for img in state.images]
                    if state.images else None,
                    ensure_ascii=False,
                ),
            )
        except Exception as e:
            yield _sse_frame(SseMessageTypeEnum.ERROR.value, f"保存失败: {str(e)}")
            return

        yield _sse_frame(SseMessageTypeEnum.ALL_COMPLETE.value)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "X-Task-Id": task_id,       # 前端可从响应头拿到 taskId
        },
    )


@router.get("/detail")
async def get_article_detail(
    task_id: str = Query(..., alias="taskId"),
    db: Database = Depends(get_db),
):
    """根据 taskId 获取文章详情"""
    service = ArticleService(db)
    article = await service.get_by_task_id(task_id)
    if not article:
        return BaseResponse.error(40400, "文章不存在")
    return BaseResponse.success(data=article)


@router.post("/list/page")
async def list_articles(
    req: ArticlePageRequest,
    current_user: LoginUserVO = Depends(require_login),
    db: Database = Depends(get_db),
):
    """分页查询当前用户的文章列表"""
    service = ArticleService(db)
    articles, total = await service.list_by_user(
        user_id=current_user.id,
        current=req.current,
        page_size=req.page_size,
    )
    return BaseResponse.success(
        data={
            "records": articles,
            "total": total,
            "current": req.current,
            "pageSize": req.page_size,
        }
    )


@router.post("/delete")
async def delete_article(
    req: DeleteRequest,
    current_user: LoginUserVO = Depends(require_login),
    db: Database = Depends(get_db),
):
    """软删除文章（仅作者本人）"""
    service = ArticleService(db)
    ok = await service.soft_delete(req.id, current_user.id)
    if not ok:
        return BaseResponse.error(40400, "文章不存在或无权限")
    return BaseResponse.success(message="删除成功")
