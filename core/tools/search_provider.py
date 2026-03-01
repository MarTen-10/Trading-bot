from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


class UnifiedSearch:
    """Supports Brave + Tavily without replacing existing OpenClaw web_search.

    Selection:
    - prefer='auto': Brave first, then Tavily
    - prefer='brave': Brave only
    - prefer='tavily': Tavily only
    """

    def __init__(self, brave_api_key: str | None = None, tavily_api_key: str | None = None):
        self.brave_api_key = brave_api_key or os.getenv("BRAVE_API_KEY", "")
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")

    def search(self, query: str, count: int = 5, prefer: str = "auto") -> dict[str, Any]:
        prefer = prefer.lower()
        if prefer not in {"auto", "brave", "tavily"}:
            raise ValueError("prefer must be auto|brave|tavily")

        if prefer in {"auto", "brave"} and self.brave_api_key:
            brave = self._search_brave(query, count)
            if brave["ok"] or prefer == "brave":
                return brave

        if prefer in {"auto", "tavily"} and self.tavily_api_key:
            return self._search_tavily(query, count)

        return {
            "ok": False,
            "provider": None,
            "error": "no_provider_configured",
            "hint": "Set BRAVE_API_KEY and/or TAVILY_API_KEY",
            "results": [],
        }

    def _search_brave(self, query: str, count: int) -> dict[str, Any]:
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.brave_api_key,
                },
                params={"q": query, "count": max(1, min(count, 10))},
                timeout=20,
            )
            data = r.json()
            items = data.get("web", {}).get("results", [])
            results = [
                SearchResult(
                    title=i.get("title", ""),
                    url=i.get("url", ""),
                    snippet=i.get("description", ""),
                    source="brave",
                ).__dict__
                for i in items
            ]
            return {"ok": r.ok, "provider": "brave", "status_code": r.status_code, "results": results}
        except Exception as e:
            return {"ok": False, "provider": "brave", "error": str(e), "results": []}

    def _search_tavily(self, query: str, count: int) -> dict[str, Any]:
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max(1, min(count, 10)),
                },
                timeout=20,
            )
            data = r.json()
            items = data.get("results", [])
            results = [
                SearchResult(
                    title=i.get("title", ""),
                    url=i.get("url", ""),
                    snippet=i.get("content", ""),
                    source="tavily",
                ).__dict__
                for i in items
            ]
            return {"ok": r.ok, "provider": "tavily", "status_code": r.status_code, "results": results}
        except Exception as e:
            return {"ok": False, "provider": "tavily", "error": str(e), "results": []}
