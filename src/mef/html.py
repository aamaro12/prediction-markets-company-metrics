"""Read public HTML without executing scripts. Preserve table/cell positions."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import urljoin


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: "Node | None" = field(default=None, repr=False)

    def descendants(self, tag=None):
        for child in self.children:
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def text(self):
        if self.tag in {"script", "style", "noscript"}:
            return ""
        return clean(" ".join(c.text() if isinstance(c, Node) else c for c in self.children))

    def ancestor(self, tag):
        p = self.parent
        while p:
            if p.tag == tag:
                return p
            p = p.parent
        return None


class Parser(HTMLParser):
    VOID = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        # Recover the common optional closing tags in HTML tables and paragraphs.
        if tag in {"tr", "td", "th", "li", "p"} and self.stack[-1].tag == tag:
            self.stack.pop()
        n = Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(n)
        if tag not in self.VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class Page:
    def __init__(self, html: str, url: str):
        p = Parser()
        p.feed(html)
        self.root, self.url = p.root, url
        titles = list(self.root.descendants("title"))
        self.title = titles[0].text() if titles else ""

    def links(self):
        return [
            {"url": urljoin(self.url, n.attrs["href"]), "text": n.text()}
            for n in self.root.descendants("a")
            if n.attrs.get("href")
        ]

    def paragraphs(self):
        return [
            {"locator": f"paragraph-{i:04d}", "text": n.text()}
            for i, n in enumerate(self.root.descendants("p"), 1)
            if n.text()
        ]

    def items(self):
        """List items, numbered apart from paragraphs so adding them moves no existing paragraph locator."""
        return [
            {"locator": f"item-{i:04d}", "text": n.text()}
            for i, n in enumerate(self.root.descendants("li"), 1)
            if n.text()
        ]

    def tables(self):
        tables = []
        for i, table in enumerate(self.root.descendants("table"), 1):
            rows = []
            for j, row in enumerate((r for r in table.descendants("tr") if r.ancestor("table") is table), 1):
                cells = [c for c in row.descendants() if c.tag in {"td", "th"} and c.ancestor("tr") is row]
                rows.append(
                    {
                        "locator": f"table-{i:03d}/row-{j:03d}",
                        "cells": [
                            {
                                "text": c.text(),
                                "colspan": c.attrs.get("colspan", "1"),
                                "rowspan": c.attrs.get("rowspan", "1"),
                                "locator": f"table-{i:03d}/row-{j:03d}/cell-{k:03d}",
                            }
                            for k, c in enumerate(cells, 1)
                        ],
                    }
                )
            tables.append({"locator": f"table-{i:03d}", "text": table.text(), "rows": rows})
        return tables
