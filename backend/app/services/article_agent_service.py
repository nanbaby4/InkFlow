"""文章智能体编排服务 — LangGraph 驱动的 6 节点流水线"""

import base64
import json
import operator
import re
import zlib
from typing import Annotated, Callable, Optional
from typing_extensions import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from openai import AsyncOpenAI

from app.config import settings
from app.constants.prompt import PromptConstant
from app.models.enums import ImageMethodEnum, SseMessageTypeEnum
from app.schemas.article import (
    ArticleState,
    ImageRequirement,
    ImageResult,
    OutlineResult,
    OutlineSection,
    TitleResult,
)
from app.services.cos_service import CosService
from app.services.pexels_service import PexelsService


# ── 配图方式常量 ──────────────────────────────────────────────
IMAGE_SOURCE_PEXELS = "PEXELS"
IMAGE_SOURCE_NANO_BANANA = "NANO_BANANA"
IMAGE_SOURCE_MERMAID = "MERMAID"
IMAGE_SOURCE_ICONIFY = "ICONIFY"
IMAGE_SOURCE_EMOJI_PACK = "EMOJI_PACK"
IMAGE_SOURCE_SVG_DIAGRAM = "SVG_DIAGRAM"

STYLE_PROMPT_MAP = {
    "tech": PromptConstant.STYLE_TECH_PROMPT,
    "emotional": PromptConstant.STYLE_EMOTIONAL_PROMPT,
    "educational": PromptConstant.STYLE_EDUCATIONAL_PROMPT,
    "humorous": PromptConstant.STYLE_HUMOROUS_PROMPT,
}

IMAGE_PLACEHOLDER_RE = re.compile(r"\{\{IMAGE_PLACEHOLDER_(\d+)\}\}")
ICON_PLACEHOLDER_RE = re.compile(r"\{\{ICON_PLACEHOLDER_(\d+)\}\}")


# ── LangGraph 状态定义 ────────────────────────────────────────

class GraphState(TypedDict, total=False):
    """
    使用了 GraphState 来维护上下文
    整个生成过程中的数据（标题、正文、图片 URL）都存在这个全局 State 里
    """

    task_id: Optional[str]
    topic: Optional[str]
    user_description: Optional[str]
    style: Optional[str]

    # Agent 1 输出
    title_options: Optional[list[dict]]
    title: Optional[dict]  # TitleResult.model_dump(by_alias=True)

    # Agent 2 输出
    outline: Optional[dict]  # OutlineResult.model_dump()

    # Agent 3 输出
    content: Optional[str]

    # Agent 4 输出
    image_requirements: Optional[list[dict]]

    # Agent 5 输出（reducer：并行结果自动合并）
    images: Annotated[list[dict], operator.add]

    # Merge 输出
    cover_image: Optional[str]
    full_content: Optional[str]

    # 并行任务注入字段（由 Send 注入）
    image_index: int


# ── 主服务类 ──────────────────────────────────────────────────

class ArticleAgentService:
    """文章智能体编排服务 — LangGraph StateGraph 驱动"""

    # ── 初始化 ─────────────────────────────────────────────────
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = settings.dashscope_model
        self.pexels_service = PexelsService()
        self.cos_service = CosService()
        self.graph = self._build_graph()

    # ── 图构建 ─────────────────────────────────────────────────
    def _build_graph(self):
        """编译 LangGraph 状态图"""
        builder = StateGraph(GraphState)

        # 注册节点
        builder.add_node("node_title", self.node_title)
        builder.add_node("node_outline", self.node_outline)
        builder.add_node("node_content", self.node_content)
        builder.add_node("node_analyze_images", self.node_analyze_images)
        builder.add_node("node_generate_single_image", self.node_generate_single_image)
        builder.add_node("node_merge", self.node_merge)

        # 连线
        builder.add_edge(START, "node_title")
        builder.add_edge("node_title", "node_outline")
        builder.add_edge("node_outline", "node_content")
        builder.add_edge("node_content", "node_analyze_images")
        builder.add_conditional_edges(
            "node_analyze_images",
            self._route_to_images,
            {
                "node_generate_single_image": "node_generate_single_image",
                "node_merge": "node_merge",
            },
        )
        builder.add_edge("node_generate_single_image", "node_merge")
        builder.add_edge("node_merge", END)

        return builder.compile()

    # ── 公共入口 ────────────────────────────────────────────────
    async def execute_article_generation(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """执行完整的文章生成流程"""
        try:
            initial = self._state_to_dict(state)
            config: RunnableConfig = {
                "configurable": {"stream_handler": stream_handler}
            }
            result = await self.graph.ainvoke(initial, config)
            self._dict_to_state(result, state)
        except Exception as e:
            raise RuntimeError(f"文章生成失败: {str(e)}")

    # ── 条件路由：配图分发 ──────────────────────────────────────
    @staticmethod
    def _route_to_images(state: GraphState):
        """无配图需求直接到 merge，有则 Send 并行分发

        Send 只传递显式指定的字段，不会自动合并父状态，
        所以需要同时传入 image_requirements 供目标节点使用。
        """
        requirements = state.get("image_requirements") or []
        if not requirements:
            return ["node_merge"]
        return [
            Send("node_generate_single_image", {
                "image_index": i,
                "image_requirements": requirements,
            })
            for i in range(len(requirements))
        ]

    # ── 状态转换辅助 ────────────────────────────────────────────
    @staticmethod
    def _state_to_dict(s: ArticleState) -> dict:
        """ArticleState（plain class）→ GraphState 兼容 dict"""
        result: dict = {}
        result["task_id"] = s.task_id
        result["topic"] = s.topic
        result["user_description"] = s.user_description
        result["style"] = s.style

        if s.title is not None:
            result["title"] = s.title.model_dump(by_alias=True)
        if s.title_options is not None:
            result["title_options"] = [t.model_dump(by_alias=True) for t in s.title_options]
        if s.outline is not None:
            result["outline"] = s.outline.model_dump()
        if s.content is not None:
            result["content"] = s.content
        if s.image_requirements is not None:
            result["image_requirements"] = [r.model_dump(by_alias=True) for r in s.image_requirements]
        if s.images is not None:
            result["images"] = [i.model_dump(by_alias=True) for i in s.images]
        if s.cover_image is not None:
            result["cover_image"] = s.cover_image
        if s.full_content is not None:
            result["full_content"] = s.full_content

        return result

    @staticmethod
    def _dict_to_state(d: dict, s: ArticleState) -> None:
        """GraphState dict → 回写 ArticleState"""
        if d.get("task_id") is not None:
            s.task_id = d["task_id"]
        if d.get("topic") is not None:
            s.topic = d["topic"]
        if d.get("user_description") is not None:
            s.user_description = d["user_description"]
        if d.get("style") is not None:
            s.style = d["style"]
        if d.get("title") is not None:
            s.title = TitleResult(**d["title"])
        if d.get("title_options") is not None:
            s.title_options = [TitleResult(**t) for t in d["title_options"]]
        if d.get("outline") is not None:
            s.outline = OutlineResult(**d["outline"])
        if d.get("content") is not None:
            s.content = d["content"]
        if d.get("image_requirements") is not None:
            s.image_requirements = [ImageRequirement(**r) for r in d["image_requirements"]]
        if d.get("images") is not None:
            s.images = [ImageResult(**i) for i in d["images"]]
        if d.get("cover_image") is not None:
            s.cover_image = d["cover_image"]
        if d.get("full_content") is not None:
            s.full_content = d["full_content"]

    # ── 辅助：从 config 提取 stream_handler ──────────────────────
    @staticmethod
    def _get_handler(config: RunnableConfig) -> Callable[[str], None]:
        """提取 stream_handler，若未提供则返回 async no-op"""
        handler = config.get("configurable", {}).get("stream_handler")
        if handler is not None:
            return handler
        # 返回一个 async no-op
        async def _noop(_s: str) -> None:
            pass
        return _noop

    # ══════════════════════════════════════════════════════════════
    # 图节点
    # ══════════════════════════════════════════════════════════════

    # ── Node 1：生成标题 ─────────────────────────────────────────
    async def node_title(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """调用 LLM 生成 3-5 个爆款标题方案"""
        handler = self._get_handler(config)

        prompt = PromptConstant.AGENT1_TITLE_PROMPT.format(
            topic=state.get("topic", "")
        )

        raw = await self._call_llm(prompt)
        titles_data = self._parse_json(raw)

        if not isinstance(titles_data, list) or len(titles_data) == 0:
            raise RuntimeError("标题生成返回为空")

        title_options = []
        for item in titles_data:
            title_options.append(
                TitleResult(
                    main_title=item.get("mainTitle", ""),
                    sub_title=item.get("subTitle", ""),
                ).model_dump(by_alias=True)
            )

        # 自动选中第一个标题
        existing_title = state.get("title")
        if existing_title is None:
            existing_title = title_options[0]

        await handler(SseMessageTypeEnum.AGENT1_COMPLETE.value)

        return {
            "title_options": title_options,
            "title": existing_title,
        }

    # ── Node 2：生成大纲（流式）───────────────────────────────────
    async def node_outline(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """调用 LLM 流式生成大纲"""
        handler = self._get_handler(config)

        title_dict = state.get("title")
        if not title_dict:
            raise RuntimeError("尚未选定标题，无法生成大纲")

        title = TitleResult(**title_dict)

        description_section = ""
        if state.get("user_description"):
            description_section = PromptConstant.AGENT2_DESCRIPTION_SECTION.format(
                userDescription=state["user_description"]
            )

        prompt = PromptConstant.AGENT2_OUTLINE_PROMPT.format(
            mainTitle=title.main_title,
            subTitle=title.sub_title,
            descriptionSection=description_section,
        )
        prompt = self._append_style(prompt, state.get("style"))

        accumulated = ""
        async for chunk in self._call_llm_stream(prompt):
            accumulated += chunk
            await handler(
                SseMessageTypeEnum.AGENT2_STREAMING.get_streaming_prefix() + chunk
            )

        data = self._parse_json(accumulated)
        sections_raw = data.get("sections", [])
        sections = [
            OutlineSection(
                section=s.get("section", i + 1),
                title=s.get("title", ""),
                points=s.get("points", []),
            )
            for i, s in enumerate(sections_raw)
        ]
        outline = OutlineResult(sections=sections)

        await handler(SseMessageTypeEnum.AGENT2_COMPLETE.value)

        return {"outline": outline.model_dump()}

    # ── Node 3：生成正文（流式）───────────────────────────────────
    async def node_content(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """调用 LLM 流式生成正文"""
        handler = self._get_handler(config)

        outline_dict = state.get("outline")
        title_dict = state.get("title")
        if not outline_dict or not title_dict:
            raise RuntimeError("尚未生成大纲，无法生成正文")

        outline = OutlineResult(**outline_dict)
        title = TitleResult(**title_dict)

        outline_json = json.dumps(
            [s.model_dump(by_alias=True) for s in outline.sections],
            ensure_ascii=False,
        )

        prompt = PromptConstant.AGENT3_CONTENT_PROMPT.format(
            mainTitle=title.main_title,
            subTitle=title.sub_title,
            outline=outline_json,
        )
        prompt = self._append_style(prompt, state.get("style"))

        accumulated = ""
        async for chunk in self._call_llm_stream(prompt):
            accumulated += chunk
            await handler(
                SseMessageTypeEnum.AGENT3_STREAMING.get_streaming_prefix() + chunk
            )

        await handler(SseMessageTypeEnum.AGENT3_COMPLETE.value)

        return {"content": accumulated.strip()}

    # ── Node 4：分析配图需求 ─────────────────────────────────────
    async def node_analyze_images(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """调用 LLM 分析正文，返回占位符正文 + 配图需求列表"""
        handler = self._get_handler(config)

        content = state.get("content")
        title_dict = state.get("title")
        if not content or not title_dict:
            raise RuntimeError("尚未生成正文，无法分析配图需求")

        title = TitleResult(**title_dict)

        available_methods = "\n".join([
            "- PEXELS: 真实照片搜索",
            "- NANO_BANANA: AI 创意插画生成",
            "- MERMAID: 流程图/架构图渲染",
            "- ICONIFY: 图标获取",
            "- EMOJI_PACK: 表情包搜索",
            "- SVG_DIAGRAM: 概念示意图生成",
        ])

        prompt = PromptConstant.AGENT4_IMAGE_REQUIREMENTS_PROMPT.format(
            mainTitle=title.main_title,
            content=content,
            availableMethods=available_methods,
            methodUsageGuide="",
        )

        raw = await self._call_llm(prompt)
        data = self._parse_json(raw)

        # 更新正文（带占位符的版本）
        content_with_placeholders = data.get("contentWithPlaceholders", "")
        if not content_with_placeholders:
            # LLM 未返回占位符版本，保留原内容
            content_with_placeholders = content

        # 解析配图需求
        requirements_raw = data.get("imageRequirements", [])
        image_requirements = []
        for req in requirements_raw:
            image_requirements.append(
                ImageRequirement(
                    position=req.get("position", 0),
                    type=req.get("type", "section"),
                    section_title=req.get("sectionTitle", ""),
                    image_source=req.get("imageSource", IMAGE_SOURCE_PEXELS),
                    keywords=req.get("keywords", ""),
                    prompt=req.get("prompt", ""),
                    placeholder_id=req.get("placeholderId", ""),
                ).model_dump(by_alias=True)
            )

        await handler(SseMessageTypeEnum.AGENT4_COMPLETE.value)

        return {
            "content": content_with_placeholders,
            "image_requirements": image_requirements,
        }

    # ── Node 5：生成单张配图（Send 并行目标）───────────────────────
    async def node_generate_single_image(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """并行执行单元：根据 image_index 取对应需求，生成一张配图"""
        handler = self._get_handler(config)

        index = state["image_index"]
        requirements = state.get("image_requirements") or []

        if index >= len(requirements):
            return {"images": []}

        req_dict = requirements[index]
        req = ImageRequirement(**req_dict)

        try:
            result = await self._generate_single_image(req)
            await handler(
                SseMessageTypeEnum.IMAGE_COMPLETE.value
                + json.dumps(result.model_dump(by_alias=True), ensure_ascii=False)
            )
            return {"images": [result.model_dump(by_alias=True)]}
        except Exception as e:
            # 单张失败不阻塞整体流程
            placeholder = ImageResult(
                position=req.position,
                url="",
                method=req.image_source,
                keywords=req.keywords,
                section_title=req.section_title,
                description=f"生成失败: {str(e)}",
            )
            return {"images": [placeholder.model_dump(by_alias=True)]}

    # ── Node 6：图文合成 ─────────────────────────────────────────
    async def node_merge(
        self, state: GraphState, config: RunnableConfig
    ) -> dict:
        """将占位符替换为实际图片 Markdown 语法"""
        handler = self._get_handler(config)

        content = state.get("content") or ""
        images = state.get("images") or []

        # 1. 找封面图（position=1）
        cover_image = None
        for img_dict in images:
            if img_dict.get("position") == 1 and img_dict.get("url"):
                cover_image = img_dict["url"]
                break

        # 2. 构建 placeholder → ImageResult 映射
        placeholder_map: dict[str, ImageResult] = {}

        # 精确映射：从 image_requirements 中获取
        requirements = state.get("image_requirements") or []
        for req_dict in requirements:
            placeholder_id = req_dict.get("placeholderId", "")
            if not placeholder_id:
                continue
            req_position = req_dict.get("position")
            for img_dict in images:
                if img_dict.get("position") == req_position and img_dict.get("url"):
                    placeholder_map[placeholder_id] = ImageResult(**img_dict)
                    break

        # 兜底映射：基于 position 构造占位符
        for img_dict in images:
            img = ImageResult(**img_dict)
            if img.position > 1 and img.url:
                placeholder_map[f"{{{{IMAGE_PLACEHOLDER_{img.position - 1}}}}}"] = img
                placeholder_map[f"{{{{ICON_PLACEHOLDER_{img.position - 1}}}}}"] = img

        # 3. 替换占位符
        def _replace_placeholder(match: re.Match) -> str:
            placeholder = match.group(0)
            img = placeholder_map.get(placeholder)
            if not img:
                return ""
            if "ICON" in placeholder:
                return f"![]({img.url})"
            alt = img.section_title or img.keywords or "配图"
            return f"\n\n![{alt}]({img.url})\n\n"

        full_content = IMAGE_PLACEHOLDER_RE.sub(_replace_placeholder, content)
        full_content = ICON_PLACEHOLDER_RE.sub(_replace_placeholder, full_content)

        await handler(SseMessageTypeEnum.AGENT5_COMPLETE.value)
        await handler(SseMessageTypeEnum.MERGE_COMPLETE.value)

        return {
            "full_content": full_content,
            "cover_image": cover_image,
        }

    # ══════════════════════════════════════════════════════════════
    # 配图生成方法（不变）
    # ══════════════════════════════════════════════════════════════

    async def _generate_single_image(self, req: ImageRequirement) -> ImageResult:
        """根据 image_source 分发到不同的生成方法"""
        source = req.image_source.upper()

        if source == IMAGE_SOURCE_PEXELS:
            return await self._generate_pexels_image(req)
        elif source == IMAGE_SOURCE_NANO_BANANA:
            return await self._generate_nano_banana_image(req)
        elif source == IMAGE_SOURCE_MERMAID:
            return await self._generate_mermaid_image(req)
        elif source == IMAGE_SOURCE_ICONIFY:
            return await self._generate_iconify_image(req)
        elif source == IMAGE_SOURCE_EMOJI_PACK:
            return await self._generate_emoji_pack_image(req)
        elif source == IMAGE_SOURCE_SVG_DIAGRAM:
            return await self._generate_svg_diagram_image(req)
        else:
            return await self._generate_pexels_image(req)

    async def _generate_pexels_image(self, req: ImageRequirement) -> ImageResult:
        """通过 Pexels 搜索图片并上传到 COS"""
        photos = await self.pexels_service.search_photos(
            query=req.keywords or req.section_title,
            per_page=1,
        )
        if not photos:
            return ImageResult(
                position=req.position,
                url="",
                method=ImageMethodEnum.PEXELS.value,
                keywords=req.keywords,
                section_title=req.section_title,
                description="Pexels 未搜索到匹配图片",
            )

        photo_url = photos[0]["url"]
        cos_url = await self.cos_service.upload_from_url(
            photo_url,
            filename=f"pexels-{photos[0]['id']}.jpg",
        )

        return ImageResult(
            position=req.position,
            url=cos_url or photo_url,
            method=ImageMethodEnum.PEXELS.value,
            keywords=req.keywords,
            section_title=req.section_title,
            description=f"Photo by {photos[0]['photographer']} on Pexels",
        )

    async def _generate_nano_banana_image(self, req: ImageRequirement) -> ImageResult:
        """通过 DashScope 多模态模型生成图片，失败降级到 Pexels"""
        prompt = req.prompt or req.keywords

        try:
            response = await self.client.images.generate(
                model="wan2.1-t2i-plus",
                prompt=prompt,
                n=1,
                size="1664*928",
            )
            image_url = response.data[0].url if response.data else ""

            if image_url:
                cos_url = await self.cos_service.upload_from_url(
                    image_url,
                    filename=f"ai-generated-{req.position}.png",
                )
                return ImageResult(
                    position=req.position,
                    url=cos_url or image_url,
                    method=IMAGE_SOURCE_NANO_BANANA,
                    keywords=req.keywords,
                    section_title=req.section_title,
                    description="AI 生成图片",
                )
        except Exception:
            pass

        # 降级到 Pexels
        return await self._generate_pexels_image(req)

    async def _generate_mermaid_image(self, req: ImageRequirement) -> ImageResult:
        """将 Mermaid 代码渲染为图片"""
        mermaid_code = req.prompt or req.keywords
        if not mermaid_code:
            return ImageResult(
                position=req.position,
                url="",
                method=IMAGE_SOURCE_MERMAID,
                keywords=req.keywords,
                section_title=req.section_title,
                description="Mermaid 代码为空",
            )

        try:
            encoded = base64.urlsafe_b64encode(
                zlib.compress(mermaid_code.encode("utf-8"), 9)
            ).decode("ascii")
            image_url = f"https://mermaid.ink/img/pako:{encoded}"

            cos_url = await self.cos_service.upload_from_url(
                image_url,
                filename=f"mermaid-{req.position}.png",
            )

            return ImageResult(
                position=req.position,
                url=cos_url or image_url,
                method=IMAGE_SOURCE_MERMAID,
                keywords=req.keywords,
                section_title=req.section_title,
                description="Mermaid 流程图",
            )
        except Exception as e:
            return ImageResult(
                position=req.position,
                url="",
                method=IMAGE_SOURCE_MERMAID,
                keywords=req.keywords,
                section_title=req.section_title,
                description=f"Mermaid 渲染失败: {str(e)}",
            )

    async def _generate_iconify_image(self, req: ImageRequirement) -> ImageResult:
        """通过 Iconify API 获取图标"""
        keywords = req.keywords.strip() if req.keywords else "check"
        if ":" in keywords:
            prefix, name = keywords.split(":", 1)
        else:
            prefix, name = "material-symbols", keywords.replace(" ", "-")

        icon_url = f"https://api.iconify.design/{prefix}/{name}.svg"

        try:
            cos_url = await self.cos_service.upload_from_url(
                icon_url,
                filename=f"icon-{req.position}.svg",
            )

            return ImageResult(
                position=req.position,
                url=cos_url or icon_url,
                method=IMAGE_SOURCE_ICONIFY,
                keywords=req.keywords,
                section_title=req.section_title,
                description=f"Icon: {prefix}:{name}",
            )
        except Exception:
            return ImageResult(
                position=req.position,
                url=icon_url,
                method=IMAGE_SOURCE_ICONIFY,
                keywords=req.keywords,
                section_title=req.section_title,
                description=f"Icon (直链): {prefix}:{name}",
            )

    async def _generate_emoji_pack_image(self, req: ImageRequirement) -> ImageResult:
        """搜索表情包"""
        query = f"{req.keywords} 表情包" if req.keywords else "表情包"
        photos = await self.pexels_service.search_photos(query=query, per_page=1)
        if not photos:
            return ImageResult(
                position=req.position,
                url="",
                method=IMAGE_SOURCE_EMOJI_PACK,
                keywords=req.keywords,
                section_title=req.section_title,
                description="未搜索到匹配表情包",
            )

        photo_url = photos[0]["url"]
        cos_url = await self.cos_service.upload_from_url(
            photo_url,
            filename=f"emoji-{req.position}.jpg",
        )

        return ImageResult(
            position=req.position,
            url=cos_url or photo_url,
            method=IMAGE_SOURCE_EMOJI_PACK,
            keywords=req.keywords,
            section_title=req.section_title,
            description="表情包配图",
        )

    async def _generate_svg_diagram_image(self, req: ImageRequirement) -> ImageResult:
        """调用 LLM 生成 SVG 概念示意图"""
        requirement = req.prompt or req.keywords
        if not requirement:
            return ImageResult(
                position=req.position,
                url="",
                method=IMAGE_SOURCE_SVG_DIAGRAM,
                keywords=req.keywords,
                section_title=req.section_title,
                description="SVG 示意图需求为空",
            )

        prompt = PromptConstant.SVG_DIAGRAM_GENERATION_PROMPT.format(
            requirement=requirement,
        )

        try:
            raw = await self._call_llm(prompt)
            svg_content = raw.strip()

            if not svg_content.startswith("<?xml"):
                svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content

            cos_url = self.cos_service.upload_svg_as_png(
                svg_content,
                filename=f"diagram-{req.position}",
            )

            return ImageResult(
                position=req.position,
                url=cos_url,
                method=IMAGE_SOURCE_SVG_DIAGRAM,
                keywords=req.keywords,
                section_title=req.section_title,
                description="SVG 概念示意图",
            )
        except Exception as e:
            return ImageResult(
                position=req.position,
                url="",
                method=IMAGE_SOURCE_SVG_DIAGRAM,
                keywords=req.keywords,
                section_title=req.section_title,
                description=f"SVG 生成失败: {str(e)}",
            )

    # ══════════════════════════════════════════════════════════════
    # LLM 调用辅助方法（不变）
    # ══════════════════════════════════════════════════════════════

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM（非流式），返回完整响应文本"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    async def _call_llm_stream(self, prompt: str):
        """调用 LLM（流式），异步生成器逐 chunk 返回"""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4096,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    # ══════════════════════════════════════════════════════════════
    # 其他辅助方法
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_json(raw: str) -> dict | list:
        """从 LLM 原始响应中解析 JSON（兼容 markdown 代码块包裹）"""
        raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        for pattern in [r"(\[.*\])", r"(\{.*\})"]:
            m = re.search(pattern, raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue

        raise RuntimeError(f"无法解析 LLM 返回的 JSON: {raw[:200]}...")

    @staticmethod
    def _append_style(prompt: str, style: Optional[str]) -> str:
        """根据文章风格附加相应的 Prompt"""
        if style and style in STYLE_PROMPT_MAP:
            return prompt + STYLE_PROMPT_MAP[style]
        return prompt
