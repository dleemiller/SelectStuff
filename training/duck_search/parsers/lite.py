from lxml.html import HTMLParser, document_fromstring
from duck_search.utils import _normalize, _normalize_url


class LiteParser:
    endpoint = "https://lite.duckduckgo.com/lite/"

    @staticmethod
    def no_results(content: bytes) -> bool:
        return b"No more results." in content

    @staticmethod
    def _parse_tree(content: bytes, parser: HTMLParser) -> list:
        tree = document_fromstring(content, parser)
        return tree.xpath("//table[last()]//tr")

    @classmethod
    def _extract_results(cls, content: bytes, parser: HTMLParser, seen: set) -> list:
        results = []
        data = iter(cls._parse_tree(content, parser))
        try:
            while True:
                row1 = next(data)
                href = (row1.xpath(".//a//@href") or [None])[0]
                if (
                    not href
                    or href in seen
                    or href.startswith(
                        (
                            "http://www.google.com/search?q=",
                            "https://duckduckgo.com/y.js?ad_domain",
                        )
                    )
                ):
                    for _ in range(3):
                        next(data)
                    continue
                seen.add(href)
                title = (row1.xpath(".//a//text()") or [""])[0]
                row2 = next(data)
                body = "".join(
                    row2.xpath(".//td[@class='result-snippet']//text()") or []
                )
                results.append(
                    {
                        "title": _normalize(title),
                        "href": _normalize_url(href),
                        "body": _normalize(body),
                    }
                )
                for _ in range(2):
                    next(data)
        except StopIteration:
            pass
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
        next_page = tree.xpath(
            "//form[./input[contains(@value, 'ext')]]/input[@name='s']/@value"
        )
        if next_page:
            return {"s": str(next_page[0])}
        return None
