from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


@dataclass
class PdfImage:
    name: str
    png: bytes


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


def _pdf_string(value: str) -> str:
    return "(" + value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def build_pdf_packet(images: list[PdfImage], *, title: str = "Network Picasso Diagram Packet") -> bytes:
    """Create a simple PDF, one rendered PNG per page."""
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    page_refs: list[int] = []
    for idx, image in enumerate(images, start=1):
        width_px, height_px, image_data, color_space, colors = _png_pdf_image(image.png)
        max_w, max_h = 756.0, 540.0
        scale = min(max_w / width_px, max_h / height_px, 1.0)
        draw_w = width_px * scale
        draw_h = height_px * scale
        x = (842.0 - draw_w) / 2
        y = 36.0
        image_ref = add(
            (
                f"<< /Type /XObject /Subtype /Image /Width {width_px} /Height {height_px} "
                f"/ColorSpace {color_space} /BitsPerComponent 8 /Filter /FlateDecode "
                f"/DecodeParms << /Predictor 15 /Colors {colors} /BitsPerComponent 8 /Columns {width_px} >> "
                f"/Length {len(image_data)} >>\nstream\n"
            ).encode("ascii") + image_data + b"\nendstream"
        )
        label = _pdf_string(f"{idx}. {image.name}")
        content = (
            "q\n"
            "BT /F1 16 Tf 40 570 Td " + label + " Tj ET\n"
            f"{draw_w:.2f} 0 0 {draw_h:.2f} {x:.2f} {y:.2f} cm /Im{idx} Do\n"
            "Q\n"
        ).encode("ascii")
        content_ref = add(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"endstream")
        page_ref = add(
            (
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 842 595] "
                f"/Resources << /Font << /F1 0 0 R >> /XObject << /Im{idx} {image_ref} 0 R >> >> "
                f"/Contents {content_ref} 0 R >>"
            ).encode("ascii")
        )
        page_refs.append(page_ref)

    font_ref = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    pages_ref = add(f"<< /Type /Pages /Count {len(page_refs)} /Kids [{kids}] >>".encode("ascii"))
    catalog_ref = add(f"<< /Type /Catalog /Pages {pages_ref} 0 R >>".encode("ascii"))
    info_ref = add(f"<< /Title {_pdf_string(title)} /Producer (Network Picasso) >>".encode("ascii"))

    fixed_objects = []
    for obj in objects:
        fixed = obj.replace(b"/Parent 0 0 R", f"/Parent {pages_ref} 0 R".encode("ascii"))
        fixed = fixed.replace(b"/F1 0 0 R", f"/F1 {font_ref} 0 R".encode("ascii"))
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
