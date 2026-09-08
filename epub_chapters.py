from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET


CONTENT_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote"}
SKIPPED_TITLES = {"cover", "contents", "table of contents", "版权信息", "目录"}


@dataclass
class Chapter:
    title: str
    content: str


@dataclass
class TocEntry:
    path: str
    anchor: str
    title: str


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def first_text(root: ET.Element, name: str) -> str:
    for element in root.iter():
        if local_name(element) == name and element.text:
            return element.text.strip()
    return ""


def href_target(href: str, base_path: str) -> tuple[str, str]:
    parsed = urlparse(href)
    path = unquote(parsed.path)
    if not path:
        path = base_path
    elif not path.startswith("/"):
        path = posixpath.normpath(posixpath.join(posixpath.dirname(base_path), path))
    else:
        path = path.lstrip("/")
    return path.lstrip("/"), unquote(parsed.fragment)


def _element_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def document_text(root: ET.Element, start_anchor: str = "", end_anchor: str = "") -> str:
    nodes = list(root.iter())
    start_index = 0
    end_index = len(nodes)
    if start_anchor:
        start = next(
            (
                node
                for node in nodes
                if node.attrib.get("id") == start_anchor or node.attrib.get("name") == start_anchor
            ),
            None,
        )
        if start is None:
            return ""
        start_index = nodes.index(start) + 1
    if end_anchor:
        end = next(
            (
                node
                for node in nodes
                if node.attrib.get("id") == end_anchor or node.attrib.get("name") == end_anchor
            ),
            None,
        )
        if end is not None:
            end_index = nodes.index(end)

    parts = []
    for index, node in enumerate(nodes):
        if start_index <= index < end_index and local_name(node).lower() in CONTENT_TAGS:
            text = _element_text(node)
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def _read_xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    return ET.fromstring(archive.read(path))


def _toc_from_ncx(
    archive: zipfile.ZipFile,
    manifest: dict[str, tuple[str, str, str]],
    spine: ET.Element,
    opf_path: str,
) -> list[TocEntry]:
    ncx_id = spine.attrib.get("toc", "")
    ncx = manifest.get(ncx_id) if ncx_id else next(
        (item for item in manifest.values() if item[1] == "application/x-dtbncx+xml"),
        None,
    )
    if not ncx or not ncx[0]:
        return []
    ncx_path = href_target(ncx[0], opf_path)[0]
    ncx_root = _read_xml(archive, ncx_path)
    entries = []
    for point in ncx_root.iter():
        if local_name(point) != "navPoint":
            continue
        label = next(
            (_element_text(child) for child in point.iter() if local_name(child) == "text"),
            "",
        )
        source = next(
            (child.attrib.get("src", "") for child in point.iter() if local_name(child) == "content"),
            "",
        )
        if label and source:
            path, anchor = href_target(source, ncx_path)
            entries.append(TocEntry(path, anchor, label))
    return entries


def _toc_from_nav(
    archive: zipfile.ZipFile,
    manifest: dict[str, tuple[str, str, str]],
    opf_path: str,
) -> list[TocEntry]:
    nav = next((item for item in manifest.values() if "nav" in item[2].split()), None)
    if not nav or not nav[0]:
        return []
    nav_path = href_target(nav[0], opf_path)[0]
    nav_root = _read_xml(archive, nav_path)
    toc_root = next(
        (
            node
            for node in nav_root.iter()
            if local_name(node).lower() == "nav"
            and any(
                local_name(ET.Element(key)).lower() == "type" and value == "toc"
                for key, value in node.attrib.items()
            )
        ),
        nav_root,
    )
    entries = []
    for node in toc_root.iter():
        if local_name(node).lower() != "a" or not node.attrib.get("href"):
            continue
        title = _element_text(node)
        if title:
            path, anchor = href_target(node.attrib["href"], nav_path)
            entries.append(TocEntry(path, anchor, title))
    return entries


def parse_epub(path: str | Path) -> list[Chapter]:
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        container = _read_xml(archive, "META-INF/container.xml")
        opf_path = next(
            (
                node.attrib.get("full-path")
                for node in container.iter()
                if local_name(node) == "rootfile"
            ),
            None,
        )
        if not opf_path:
            raise ValueError("无法读取 EPUB 内容索引")
        opf = _read_xml(archive, opf_path)
        manifest = {
            node.attrib.get("id", ""): (
                node.attrib.get("href", ""),
                node.attrib.get("media-type", ""),
                node.attrib.get("properties", ""),
            )
            for node in opf.iter()
            if local_name(node) == "item"
        }
        spine = next((node for node in opf.iter() if local_name(node) == "spine"), None)
        if spine is None:
            raise ValueError("EPUB 没有阅读顺序")

        spine_files = []
        for node in spine:
            if local_name(node) != "itemref":
                continue
            href = manifest.get(node.attrib.get("idref", ""), ("", "", ""))[0]
            if href:
                spine_files.append(href_target(href, opf_path)[0])

        toc_entries = _toc_from_ncx(archive, manifest, spine, opf_path)
        if not toc_entries:
            toc_entries = _toc_from_nav(archive, manifest, opf_path)
        by_path: dict[str, list[TocEntry]] = {}
        for entry in toc_entries:
            by_path.setdefault(entry.path, []).append(entry)

        chapters = []
        current_volume = ""
        for index, spine_path in enumerate(spine_files):
            entries = by_path.get(spine_path, [])
            if toc_entries and not entries:
                continue
            try:
                root = _read_xml(archive, spine_path)
            except (KeyError, ET.ParseError):
                continue

            page_title = first_text(root, "title")
            if page_title.strip().lower() in SKIPPED_TITLES:
                continue
            label = next(
                (entry.title for entry in entries if not entry.anchor),
                entries[0].title if entries else "",
            ).strip()
            if label.lower() in SKIPPED_TITLES:
                continue
            if label and not label.isdigit() and label.lower() not in SKIPPED_TITLES:
                current_volume = label

            anchored = [entry for entry in entries if entry.anchor]
            if anchored:
                for entry_index, entry in enumerate(anchored):
                    end_anchor = (
                        anchored[entry_index + 1].anchor
                        if entry_index + 1 < len(anchored)
                        else ""
                    )
                    content = document_text(root, entry.anchor, end_anchor)
                    if content and not content.startswith("版权信息"):
                        chapters.append(Chapter(entry.title.strip(), content))
                continue

            content = document_text(root)
            if not content or content.startswith("版权信息"):
                continue
            local_heading = next(
                (
                    _element_text(node)
                    for node in root.iter()
                    if local_name(node).lower() in {"h1", "h2", "h3"}
                    and _element_text(node)
                ),
                "",
            )
            title = (
                f"{current_volume or '正文'} · 第 {label} 章"
                if label.isdigit()
                else label or current_volume or local_heading or f"第 {index + 1} 章"
            )
            chapters.append(Chapter(title, content))

    if not chapters:
        raise ValueError("没有从 EPUB 读取到正文")
    return chapters
