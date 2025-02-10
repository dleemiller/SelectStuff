from __future__ import annotations

import logging
import os
import random
import warnings
from functools import cached_property
from time import sleep, time
from types import TracebackType
from typing import Literal, cast

import primp
from lxml.html import HTMLParser as LHTMLParser

from .exceptions import (
    ConversationLimitException,
    DuckDuckGoSearchException,
    RatelimitException,
    TimeoutException,
)
from .utils import _expand_proxy_tb_alias, _normalize, _normalize_url
from .parsers import HtmlParser, LiteParser

logger = logging.getLogger("duckduckgo_search.DDGS")


class DDGS:
    """DuckDuckgo_search class to retrieve search results from duckduckgo.com."""

    _impersonates = (
        "chrome_100",
        "chrome_101",
        "chrome_104",
        "chrome_105",
        "chrome_106",
        "chrome_107",
        "chrome_108",
        "chrome_109",
        "chrome_114",
        "chrome_116",
        "chrome_117",
        "chrome_118",
        "chrome_119",
        "chrome_120",
        "chrome_123",
        "chrome_124",
        "chrome_126",
        "chrome_127",
        "chrome_128",
        "chrome_129",
        "chrome_130",
        "chrome_131",
        "safari_ios_16.5",
        "safari_ios_17.2",
        "safari_ios_17.4.1",
        "safari_ios_18.1.1",
        "safari_15.3",
        "safari_15.5",
        "safari_15.6.1",
        "safari_16",
        "safari_16.5",
        "safari_17.0",
        "safari_17.2.1",
        "safari_17.4.1",
        "safari_17.5",
        "safari_18",
        "safari_18.2",
        "safari_ipad_18",
        "edge_101",
        "edge_122",
        "edge_127",
        "edge_131",
        "firefox_109",
        "firefox_117",
        "firefox_128",
        "firefox_133",
    )
    _impersonates_os = ("android", "ios", "linux", "macos", "windows")

    def __init__(
        self,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        proxies: dict[str, str] | str | None = None,  # deprecated
        timeout: int | None = 10,
        verify: bool = True,
    ) -> None:
        ddgs_proxy: str | None = os.environ.get("DDGS_PROXY")
        self.proxy: str | None = (
            ddgs_proxy if ddgs_proxy else _expand_proxy_tb_alias(proxy)
        )
        if not proxy and proxies:
            warnings.warn("'proxies' is deprecated, use 'proxy' instead.", stacklevel=1)
            self.proxy = (
                proxies.get("http") or proxies.get("https")
                if isinstance(proxies, dict)
                else proxies
            )
        self.headers = headers or {}
        self.headers["Referer"] = "https://duckduckgo.com/"
        self.client = primp.Client(
            headers=self.headers,
            proxy=self.proxy,
            timeout=timeout,
            cookie_store=True,
            referer=True,
            impersonate=random.choice(self._impersonates),
            impersonate_os=random.choice(self._impersonates_os),
            follow_redirects=False,
            verify=verify,
        )
        self._chat_messages: list[dict[str, str]] = []
        self._chat_tokens_count = 0
        self._chat_vqd: str = ""

        # Token Bucket settings: enforce roughly 1 request every 6 seconds (~10 req/min)
        self.bucket_capacity: float = 1.0
        self.refill_rate: float = 1.0 / 6.0
        self.tokens: float = self.bucket_capacity
        self.token_last_refill: float = time()

    def __enter__(self) -> DDGS:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        pass

    @cached_property
    def parser(self) -> LHTMLParser:
        return LHTMLParser(
            remove_blank_text=True,
            remove_comments=True,
            remove_pis=True,
            collect_ids=False,
        )

    def _wait_for_token(self) -> None:
        """Refill token bucket and wait until one token is available."""
        now = time()
        elapsed = now - self.token_last_refill
        self.tokens = min(
            self.bucket_capacity, self.tokens + elapsed * self.refill_rate
        )
        self.token_last_refill = now
        if self.tokens < 1:
            sleep((1 - self.tokens) / self.refill_rate)
            self._wait_for_token()
        else:
            self.tokens -= 1

    def _calculate_backoff(self, attempt: int) -> float:
        base_delay = 1.0
        delay = base_delay * (2 ** (attempt - 1))
        return delay * random.uniform(0.8, 1.2)

    def _make_request(
        self,
        method: Literal["GET", "HEAD", "OPTIONS", "DELETE", "POST", "PUT", "PATCH"],
        url: str,
        **kwargs,
    ) -> bytes:
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            self._wait_for_token()
            try:
                resp = self.client.request(method, url, **kwargs)
            except Exception as ex:
                if "time" in str(ex).lower():
                    raise TimeoutException(f"{url} {type(ex).__name__}: {ex}") from ex
                raise DuckDuckGoSearchException(
                    f"{url} {type(ex).__name__}: {ex}"
                ) from ex
            logger.debug(
                f"_make_request() {resp.url} {resp.status_code} {len(resp.content)}"
            )
            if resp.status_code == 200:
                return cast(bytes, resp.content)
            elif resp.status_code in (202, 301, 403):
                if attempt < max_attempts:
                    delay = self._calculate_backoff(attempt)
                    logger.info(
                        f"Rate limit hit ({resp.status_code}) on {resp.url}. Retrying in {delay:.2f}s (attempt {attempt}/{max_attempts})."
                    )
                    sleep(delay)
                    continue
            raise DuckDuckGoSearchException(
                f"{resp.url} returned status {resp.status_code}."
            )
        raise RatelimitException(
            f"{url} exceeded rate limit after {max_attempts} attempts."
        )

    def _search_paginated(
        self,
        parser_cls,
        keywords: str,
        region: str,
        timelimit: str | None,
        max_results: int | None,
    ) -> list[dict[str, str]]:
        payload = {
            "q": keywords,
            "s": "0",
            "o": "json",
            "api": "d.js",
            "vqd": "",
            "kl": region,
            "bing_market": region,
        }
        if timelimit:
            payload["df"] = timelimit
        results, seen = [], set()
        while True:
            content = self._make_request("POST", parser_cls.endpoint, data=payload)
            if parser_cls.no_results(content):
                break
            page_results = parser_cls.parse(content, seen)
            results.extend(page_results)
            if max_results and len(results) >= max_results:
                return results[:max_results]
            next_payload = parser_cls.next_payload(content)
            if not next_payload:
                break
            payload = next_payload
        return results

    def text(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        backend: str = "auto",
        max_results: int | None = None,
    ) -> list[dict[str, str]]:
        if backend in ("api", "ecosia"):
            warnings.warn(
                f"{backend=} is deprecated, using backend='auto'", stacklevel=2
            )
            backend = "auto"
        backends = ["html", "lite"] if backend == "auto" else [backend]
        random.shuffle(backends)
        last_err = None
        for b in backends:
            try:
                if b == "html":
                    return self._search_paginated(
                        HtmlParser, keywords, region, timelimit, max_results
                    )
                elif b == "lite":
                    return self._search_paginated(
                        LiteParser, keywords, region, timelimit, max_results
                    )
            except Exception as ex:
                logger.info(f"Error with backend '{b}': {ex}")
                last_err = ex
        raise DuckDuckGoSearchException(last_err)
