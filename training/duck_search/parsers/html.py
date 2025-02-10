from lxml.html import HTMLParser, document_fromstring

# from parsers import __all__
from duck_search.utils import _normalize, _normalize_url


class HtmlParser:
    endpoint = "https://html.duckduckgo.com/html"

    @staticmethod
    def no_results(content: bytes) -> bool:
        return b"No  results." in content

    @staticmethod
    def _parse_tree(content: bytes, parser: HTMLParser) -> list:
        tree = document_fromstring(content, parser)
        return tree.xpath("//div[h2]")

    @classmethod
    def _extract_result(cls, element) -> dict:
        href = (element.xpath("./a/@href") or [None])[0]
        if not href or href.startswith(
            ("http://www.google.com/search?q=", "https://duckduckgo.com/y.js?ad_domain")
        ):
            return {}
        title = (element.xpath("./h2/a/text()") or [""])[0]
        body = "".join(element.xpath("./a//text()") or [])
        return {
            "title": _normalize(title),
            "href": _normalize_url(href),
            "body": _normalize(body),
        }

    @classmethod
    def _extract_results(cls, content: bytes, parser: HTMLParser, seen: set) -> list:
        results = []
        for element in cls._parse_tree(content, parser):
            result = cls._extract_result(element)
            if result and result["href"] not in seen:
                seen.add(result["href"])
                results.append(result)
        return results

    @classmethod
    def parse(cls, content: bytes, seen: set) -> list:
        parser = HTMLParser(
            remove_blank_text=True,
            remove_comments=True,
            remove_pis=True,
            collect_ids=False,
        )
        return cls._extract_results(content, parser, seen)

    @classmethod
    def next_payload(cls, content: bytes) -> dict | None:
        parser = HTMLParser(
            remove_blank_text=True,
            remove_comments=True,
            remove_pis=True,
            collect_ids=False,
        )
        tree = document_fromstring(content, parser)
        nav = tree.xpath('.//div[@class="nav-link"]')
        if not nav:
            return None
        next_page = nav[-1]
        names = next_page.xpath('.//input[@type="hidden"]/@name')
        values = next_page.xpath('.//input[@type="hidden"]/@value')
        if names and values:
            return {str(n): str(v) for n, v in zip(names, values)}
        return None
