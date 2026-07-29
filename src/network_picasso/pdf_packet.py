from __future__ import annotations

import re
import struct
import textwrap
import unicodedata
import zlib
from dataclasses import dataclass, field


PAGE_W = 842.0
PAGE_H = 595.0
MARGIN_X = 48.0


@dataclass
class PdfImage:
    name: str
    png: bytes


@dataclass
class PdfSection:
    title: str
    markdown: str


@dataclass
class PdfPacketMetadata:
    customer: str = ""
    project: str = ""
    exported_at: str = ""
    source: str = "Network Picasso generated model"
    title: str = "Network Picasso Diagram Packet"
    subtitle: str = "IBM Cloud architecture design package"
    summary_items: list[tuple[str, str]] = field(default_factory=list)


def _png_chunks(png: bytes) -> dict[str, list[bytes]]:
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Not a PNG image")
    chunks: dict[str, list[bytes]] = {}
    pos = 8
    while pos + 8 <= len(png):
        length = struct.unpack(">I", png[pos:pos + 4])[0]
        ctype = png[pos + 4:pos + 8].decode("ascii")
        data = png[pos + 8:pos + 8 + length]
        chunks.setdefault(ctype, []).append(data)
        pos += 12 + length
        if ctype == "IEND":
            break
    return chunks


def _unfilter_scanlines(raw: bytes, width: int, height: int, channels: int) -> list[bytearray]:
    stride = width * channels
    rows: list[bytearray] = []
    pos = 0
    prev = bytearray(stride)
    for _ in range(height):
        filter_type = raw[pos]
        pos += 1
        row = bytearray(raw[pos:pos + stride])
        pos += stride
        recon = bytearray(stride)
        for i, value in enumerate(row):
            left = recon[i - channels] if i >= channels else 0
            up = prev[i]
            up_left = prev[i - channels] if i >= channels else 0
            if filter_type == 0:
                recon[i] = value
            elif filter_type == 1:
                recon[i] = (value + left) & 0xFF
            elif filter_type == 2:
                recon[i] = (value + up) & 0xFF
            elif filter_type == 3:
                recon[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                p = left + up - up_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - up_left)
                pred = left if pa <= pb and pa <= pc else up if pb <= pc else up_left
                recon[i] = (value + pred) & 0xFF
            else:
                raise ValueError(f"Unsupported PNG filter type {filter_type}")
        rows.append(recon)
        prev = recon
    return rows


def _png_pdf_image(png: bytes) -> tuple[int, int, bytes, str, int]:
    chunks = _png_chunks(png)
    ihdr = chunks["IHDR"][0]
    width, height, bit_depth, color_type = struct.unpack(">IIBB", ihdr[:10])
    if bit_depth != 8:
        raise ValueError("Only 8-bit PNG exports are supported")
    idat = b"".join(chunks.get("IDAT", []))
    if color_type == 2:
        return width, height, idat, "/DeviceRGB", 3
    if color_type == 0:
        return width, height, idat, "/DeviceGray", 1
    if color_type == 6:
        raw = zlib.decompress(idat)
        rows = _unfilter_scanlines(raw, width, height, 4)
        rgb_rows = []
        for row in rows:
            out = bytearray()
            for i in range(0, len(row), 4):
                r, g, b, a = row[i:i + 4]
                out.extend((
                    (r * a + 255 * (255 - a)) // 255,
                    (g * a + 255 * (255 - a)) // 255,
                    (b * a + 255 * (255 - a)) // 255,
                ))
            rgb_rows.append(b"\x00" + bytes(out))
        return width, height, zlib.compress(b"".join(rgb_rows)), "/DeviceRGB", 3
    raise ValueError(f"Unsupported PNG color type {color_type}")


def _clean_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2022", "-")
    return text.encode("ascii", "ignore").decode("ascii")


def _pdf_string(value: object) -> str:
    text = _clean_text(value)
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def _text_op(text: object, x: float, y: float, size: int = 10, font: str = "F1") -> str:
    return f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td {_pdf_string(text)} Tj ET\n"


def _line(x1: float, y1: float, x2: float, y2: float, width: float = 0.7) -> str:
    return f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n"


def _rect(x: float, y: float, w: float, h: float, gray: float = 0.96) -> str:
    return f"{gray:.3f} g {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f 0 g\n"


def _wrap(value: object, width: int) -> list[str]:
    text = re.sub(r"\s+", " ", _clean_text(value)).strip()
    if not text:
        return []
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False) or [text]


def _markdown_lines(markdown: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw in markdown.splitlines():
        text = _clean_text(raw).strip()
        if not text:
            lines.append(("blank", ""))
        elif text.startswith("# "):
            lines.append(("h1", text[2:].strip()))
        elif text.startswith("## "):
            lines.append(("h2", text[3:].strip()))
        elif text.startswith("- "):
            lines.append(("bullet", text[2:].strip()))
        else:
            lines.append(("body", text))
    return lines


def _build_text_pages(section: PdfSection) -> list[bytes]:
    pages: list[bytes] = []
    content = ""
    y = 528.0

    def new_page() -> None:
        nonlocal content, y
        if content:
            pages.append(content.encode("ascii"))
        content = _text_op(section.title, MARGIN_X, 555, 18, "F2")
        content += _line(MARGIN_X, 542, PAGE_W - MARGIN_X, 542, 0.8)
        y = 520.0

    new_page()
    for kind, text in _markdown_lines(section.markdown):
        if kind == "blank":
            y -= 8
            continue
        font = "F1"
        size = 10
        indent = 0.0
        line_gap = 13.0
        wrap_width = 116
        prefix = ""
        if kind == "h1":
            font, size, line_gap = "F2", 14, 18.0
        elif kind == "h2":
            font, size, line_gap = "F2", 12, 16.0
        elif kind == "bullet":
            indent, prefix, wrap_width = 12.0, "- ", 110
        for index, line in enumerate(_wrap(text, wrap_width)):
            if y < 48:
                new_page()
            rendered = f"{prefix if index == 0 else '  '}{line}" if prefix else line
            content += _text_op(rendered, MARGIN_X + indent, y, size, font)
            y -= line_gap
        if kind in {"h1", "h2"}:
            y -= 4
    if content:
        pages.append(content.encode("ascii"))
    return pages


def build_pdf_packet(
    images: list[PdfImage],
    *,
    metadata: PdfPacketMetadata | None = None,
    sections: list[PdfSection] | None = None,
    title: str = "Network Picasso Diagram Packet",
) -> bytes:
    """Create a polished seller packet with cover, TOC, diagrams, and appendices."""
    metadata = metadata or PdfPacketMetadata(title=title)
    if title and metadata.title == "Network Picasso Diagram Packet":
        metadata.title = title
    sections = sections or []
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    page_refs: list[int] = []
    page_contents: list[tuple[bytes, dict[str, int]]] = []

    toc: list[tuple[str, int]] = [
        ("Cover", 1),
        ("Table of Contents", 2),
    ]
    start_page = 3
    for idx, image in enumerate(images):
        toc.append((image.name, start_page + idx))
    appendix_start = start_page + len(images)
    for section in sections:
        pages = _build_text_pages(section)
        toc.append((section.title, appendix_start))
        appendix_start += len(pages)

    cover = ""
    cover += _rect(0, 0, PAGE_W, PAGE_H, 0.985)
    cover += _text_op("Network Picasso", MARGIN_X, 540, 16, "F2")
    cover += _line(MARGIN_X, 526, PAGE_W - MARGIN_X, 526, 1.0)
    cover += _text_op(metadata.title, MARGIN_X, 420, 28, "F2")
    cover += _text_op(metadata.subtitle, MARGIN_X, 390, 14, "F1")
    cover += _line(MARGIN_X, 370, PAGE_W - MARGIN_X, 370, 1.0)
    cover_fields = [
        ("Customer", metadata.customer),
        ("Project", metadata.project),
        ("Export source", metadata.source),
        ("Exported", metadata.exported_at),
    ]
    y = 325.0
    for label, value in cover_fields:
        cover += _text_op(label, MARGIN_X, y, 10, "F2")
        cover += _text_op(value or "Not specified", 170, y, 10, "F1")
        y -= 22
    y -= 12
    for label, value in metadata.summary_items[:9]:
        cover += _text_op(label, MARGIN_X, y, 9, "F2")
        cover += _text_op(value or "Not specified", 170, y, 9, "F1")
        y -= 17
    page_contents.append((cover.encode("ascii"), {}))

    toc_content = _text_op("Table of Contents", MARGIN_X, 555, 22, "F2")
    toc_content += _line(MARGIN_X, 540, PAGE_W - MARGIN_X, 540, 0.8)
    y = 505.0
    for label, page in toc:
        if y < 58:
            break
        toc_content += _text_op(label, MARGIN_X, y, 11, "F1")
        toc_content += _text_op(str(page), PAGE_W - MARGIN_X - 24, y, 11, "F1")
        toc_content += _line(MARGIN_X + 210, y - 2, PAGE_W - MARGIN_X - 36, y - 2, 0.25)
        y -= 22
    page_contents.append((toc_content.encode("ascii"), {}))

    for idx, image in enumerate(images, start=1):
        width_px, height_px, image_data, color_space, colors = _png_pdf_image(image.png)
        image_ref = add(
            (
                f"<< /Type /XObject /Subtype /Image /Width {width_px} /Height {height_px} "
                f"/ColorSpace {color_space} /BitsPerComponent 8 /Filter /FlateDecode "
                f"/DecodeParms << /Predictor 15 /Colors {colors} /BitsPerComponent 8 /Columns {width_px} >> "
                f"/Length {len(image_data)} >>\nstream\n"
            ).encode("ascii") + image_data + b"\nendstream"
        )
        max_w, max_h = 756.0, 485.0
        scale = min(max_w / width_px, max_h / height_px, 1.0)
        draw_w = width_px * scale
        draw_h = height_px * scale
        x = (PAGE_W - draw_w) / 2
        y_img = 48.0
        content = _text_op(f"{idx}. {image.name}", MARGIN_X, 555, 16, "F2")
        content += _line(MARGIN_X, 542, PAGE_W - MARGIN_X, 542, 0.8)
        content += f"q\n{draw_w:.2f} 0 0 {draw_h:.2f} {x:.2f} {y_img:.2f} cm /Im{idx} Do\nQ\n"
        page_contents.append((content.encode("ascii"), {f"Im{idx}": image_ref}))

    for section in sections:
        for page in _build_text_pages(section):
            page_contents.append((page, {}))

    total_pages = len(page_contents)
    for page_number, (content, xobjects) in enumerate(page_contents, start=1):
        footer = _text_op(f"{page_number} / {total_pages}", PAGE_W - MARGIN_X - 42, 24, 8, "F1")
        footer += _text_op("Network Picasso", MARGIN_X, 24, 8, "F1")
        page_body = content + footer.encode("ascii")
        content_ref = add(f"<< /Length {len(page_body)} >>\nstream\n".encode("ascii") + page_body + b"endstream")
        xobject_def = ""
        if xobjects:
            xobject_def = " /XObject << " + " ".join(f"/{name} {ref} 0 R" for name, ref in xobjects.items()) + " >>"
        page_ref = add(
            (
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
                f"/Resources << /Font << /F1 0 0 R /F2 0 0 R >>{xobject_def} >> "
                f"/Contents {content_ref} 0 R >>"
            ).encode("ascii")
        )
        page_refs.append(page_ref)

    font_ref = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    bold_ref = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    pages_ref = add(f"<< /Type /Pages /Count {len(page_refs)} /Kids [{kids}] >>".encode("ascii"))
    catalog_ref = add(f"<< /Type /Catalog /Pages {pages_ref} 0 R >>".encode("ascii"))
    info_ref = add(f"<< /Title {_pdf_string(metadata.title)} /Producer (Network Picasso) >>".encode("ascii"))

    fixed_objects = []
    for obj in objects:
        fixed = obj.replace(b"/Parent 0 0 R", f"/Parent {pages_ref} 0 R".encode("ascii"))
        fixed = fixed.replace(b"/F1 0 0 R", f"/F1 {font_ref} 0 R".encode("ascii"))
        fixed = fixed.replace(b"/F2 0 0 R", f"/F2 {bold_ref} 0 R".encode("ascii"))
        fixed_objects.append(fixed)

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(fixed_objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(fixed_objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer << /Size {len(fixed_objects) + 1} /Root {catalog_ref} 0 R /Info {info_ref} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)
