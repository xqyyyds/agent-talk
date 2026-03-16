"""
搜索客户端（使用 LangChain TavilySearchResults）

标准 LangChain 工具集成方式
"""
import logging
from typing import List, Dict, Optional

from app.config import settings
from app.core.runtime_config import get_runtime_config

logger = logging.getLogger("agent_service")

# Tavily 是可选依赖
try:
    from langchain_tavily import TavilySearch
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("langchain_tavily not installed. Search functionality will be disabled.")


class SearchClient:
    """搜索服务客户端（使用 LangChain TavilySearchResults）"""

    def __init__(self):
        """初始化搜索客户端"""
        self.api_key = settings.tavily_api_key
        self._tool_api_key = ""
        self.search_tool = None

    def _build_tool(self, api_key: str) -> None:
        if not TAVILY_AVAILABLE:
            self.search_tool = None
            self._tool_api_key = ""
            return
        if not api_key or api_key == "your-tavily-api-key-here":
            self.search_tool = None
            self._tool_api_key = ""
            return
        self.search_tool = TavilySearch(
            max_results=5,
            search_depth="advanced",
            include_domains=[],
            exclude_domains=[],
            api_key=api_key,
        )
        self._tool_api_key = api_key
        logger.info("✓ TavilySearch initialized")

    async def _ensure_tool(self) -> None:
        cfg = await get_runtime_config()
        current_key = str(cfg.get("tavily_api_key", settings.tavily_api_key))
        if current_key != self._tool_api_key:
            self._build_tool(current_key)

    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        执行搜索

        使用 LangChain TavilySearch 工具

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        await self._ensure_tool()
        if not self.search_tool:
            logger.warning("Search tool not available")
            return []

        try:
            # 使用 LangChain 工具的 ainvoke 方法
            results = await self.search_tool.ainvoke({"query": query})

            # TavilySearch 返回 {'results': [...]} 格式
            # 需要先提取 results['results'] 列表
            if isinstance(results, dict) and 'results' in results:
                results_list = results['results']
                logger.debug(f"搜索返回字典格式，提取 results 列表，共 {len(results_list)} 条")
            elif isinstance(results, list):
                results_list = results
                logger.debug(f"搜索返回列表格式，共 {len(results_list)} 条")
            else:
                logger.warning(f"搜索返回格式未知: {type(results)}, 内容: {results}")
                # 尝试处理可能是 answer 字段的情况
                if isinstance(results, dict) and 'answer' in results:
                    # Tavily 有时候返回 {'answer': '...', 'results': [...]}
                    return [{
                        "title": "搜索结果",
                        "content": results['answer'],
                        "url": ""
                    }]
                return []

            # 转换为统一格式
            formatted_results = []
            for doc in results_list[:max_results]:
                if isinstance(doc, dict):
                    formatted_results.append({
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "url": doc.get("url", "")
                    })
                else:
                    logger.warning(f"搜索结果项不是字典: {type(doc)}")

            logger.info(f"搜索完成，返回 {len(formatted_results)} 条结果")
            return formatted_results

        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return []

    async def search_hotspot(self, topic: str, category: str = "") -> List[Dict]:
        """
        搜索热点新闻详情

        Args:
            topic: 热点主题（如：GPT-4、华为Mate60）
            category: 热点类别（可选）

        Returns:
            去重后的新闻结果列表
        """
        if not self.search_tool:
            return []

        # 搜索两个查询
        query1 = f"{topic} 最新新闻"
        query2 = f"{topic} 最新报道"

        # 并发搜索
        import asyncio
        results1, results2 = await asyncio.gather(
            self.search(query1, max_results=5),
            self.search(query2, max_results=5)
        )

        # 合并结果
        all_results = results1 + results2

        # 去重（基于 URL）
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results


# 全局单例
search_client = SearchClient()
