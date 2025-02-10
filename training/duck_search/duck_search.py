"""Module duck_search.duck_search

This module provides the DuckSearch class for querying DuckDuckGo search results
using different backends. It implements adaptive rate limiting via a token bucket
and retries with exponential backoff with jitter.
"""

import logging
import os
import random
import warnings
from functools import cached_property
from time import sleep, time
from types import TracebackType
from typing import Literal, Optional, cast

import primp
from lxml.html import HTMLParser as LHTMLParser

from .exceptions import DuckDuckGoSearchException, RatelimitException, TimeoutException
from .utils import _expand_proxy_tb_alias

from .parsers import HtmlParser, LiteParser

logger = logging.getLogger("duck_search.DuckSearch")


class DuckSearch:
    """DuckDuckGo Search client.

    This class handles sending search queries to DuckDuckGo using either the HTML or Lite
    backend, managing rate limits via a token bucket and retrying on transient errors.

    Attributes:
        client: The underlying HTTP client.
    """

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
        headers: Optional[dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: Optional[int] = 10,
        verify: bool = True,
    ) -> None:
        """Initialize a new DuckSearch instance.

        Args:
            headers: Optional HTTP headers.
            proxy: Optional proxy string.
            timeout: Timeout in seconds for HTTP requests.
            verify: Whether to verify SSL certificates.
        """
        ddgs_proxy = os.environ.get("DuckSearch_PROXY")
        self.proxy = ddgs_proxy if ddgs_proxy else _expand_proxy_tb_alias(proxy)
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
        # Token bucket settings: enforce roughly 1 request every 6 seconds (~10 req/min).
        self.bucket_capacity: float = 1.0
        self.refill_rate: float = 1.0 / 6.0
        self.tokens: float = self.bucket_capacity
        self.token_last_refill: float = time()

    def __enter__(self) -> "DuckSearch":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
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
        """Wait until a token is available in the token bucket."""
        now = time()
        elapsed = now - self.token_last_refill
        self.tokens = min(
            self.bucket_capacity, self.tokens + elapsed * self.refill_rate
        )
        self.token_last_refill = now
        if self.tokens < 1:
            sleep((1 - self.tokens) / self.refill_rate)
            self._wait_for_token()  # recursive call after sleep
        else:
            self.tokens -= 1

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter for a given attempt.

        Args:
            attempt: The current retry attempt (starting at 1).

        Returns:
            A delay in seconds.
        """
        base_delay = 1.0
        delay = base_delay * (2 ** (attempt - 1))
        return delay * random.uniform(0.8, 1.2)

    def _make_request(
        self,
        method: Literal["GET", "HEAD", "OPTIONS", "DELETE", "POST", "PUT", "PATCH"],
        url: str,
        **kwargs,
    ) -> bytes:
        """Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The response content as bytes.

        Raises:
            TimeoutException, DuckDuckGoSearchException, RatelimitException.
        """
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            self._wait_for_token()
            try:
                resp = self.client.request(method, url, **kwargs)
            except Exception as ex:
                if "time" in str(ex).lower():
                    raise TimeoutException(
                        "%s %s: %s", url, type(ex).__name__, ex
                    ) from ex
                raise DuckDuckGoSearchException(
                    "%s %s: %s", url, type(ex).__name__, ex
                ) from ex
            logger.debug(
                "_make_request() %s %d %d",
                resp.url,
                resp.status_code,
                len(resp.content),
            )
            if resp.status_code == 200:
                return cast(bytes, resp.content)
            if resp.status_code in (202, 301, 403):
                if attempt < max_attempts:
                    delay = self._calculate_backoff(attempt)
                    logger.info(
                        "Rate limit hit (%s) on %s. Retrying in %.2fs (attempt %d/%d).",
                        resp.status_code,
                        resp.url,
                        delay,
                        attempt,
                        max_attempts,
                    )
                    sleep(delay)
                    continue
            raise DuckDuckGoSearchException(
                "%s returned status %s.", resp.url, resp.status_code
            )
        raise RatelimitException(
            "%s exceeded rate limit after %d attempts.", url, max_attempts
        )

    def _build_payload(
        self, keywords: str, region: str, timelimit: Optional[str] = None
    ) -> dict[str, str]:
        """Build the initial payload for a search query.

        Args:
            keywords: Search keywords.
            region: Region code.
            timelimit: Optional time limit filter.

        Returns:
            A dictionary of query parameters.
        """
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
        return payload

    def _search_paginated(
        self,
        parser_cls,
        keywords: str,
        region: str,
        timelimit: Optional[str],
        max_results: Optional[int],
    ) -> list[dict[str, str]]:
        """Handle pagination of search results.

        Args:
            parser_cls: The parser class (e.g. HtmlParser or LiteParser).
            keywords: Search keywords.
            region: Region code.
            timelimit: Optional time limit.
            max_results: Maximum results to return.

        Returns:
            A list of search results.
        """
        payload = self._build_payload(keywords, region, timelimit)
        results: list[dict[str, str]] = []
        seen = set()
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
        timelimit: Optional[str] = None,
        backend: str = "auto",
        max_results: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """Perform a DuckDuckGo text search.

        Args:
            keywords: Search keywords.
            region: Region code (e.g. "wt-wt", "us-en").
            timelimit: Optional time limit filter.
            backend: Which backend to use ("html", "lite", or "auto").
            max_results: Maximum number of results to return.

        Returns:
            A list of dictionaries containing search result data.

        Raises:
            DuckDuckGoSearchException if all backends fail.
        """
        if backend in ("api", "ecosia"):
            warnings.warn(
                "backend=%s is deprecated, using backend='auto'" % backend, stacklevel=2
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
                logger.info("Error with backend '%s': %s", b, ex)
                last_err = ex
        raise DuckDuckGoSearchException(last_err)
