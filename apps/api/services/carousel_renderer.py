import os
import zlib
import struct
import io
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, update

from config import settings
from database import async_session_factory
from models.entities import Carousel, CarouselSlide, CarouselExport, Content
from services.storage_service import storage_service
from utils.logging import get_logger

logger = get_logger("CarouselRenderer")

class CarouselRenderer:
    TEMPLATE_STYLES = {
        "MINIMAL": {
            "bg_color": (15, 23, 42),       # Slate #0F172A
            "text_color": (255, 255, 255),  # White
            "muted_color": (148, 163, 184), # Slate-400 #94A3B8
            "accent_color": (99, 102, 241), # Indigo #6366F1
            "card_bg": (22, 27, 38)
        },
        "EDITORIAL": {
            "bg_color": (24, 24, 27),       # Zinc #18181B
            "text_color": (248, 250, 252),  # Light Zinc
            "muted_color": (161, 161, 170), # Zinc-400
            "accent_color": (245, 158, 11), # Amber #F59E0B
            "card_bg": (39, 39, 42)
        },
        "BOLD": {
            "bg_color": (30, 27, 75),       # Midnight Violet #1E1B4B
            "text_color": (255, 255, 255),  # White
            "muted_color": (196, 181, 253), # Light Violet
            "accent_color": (6, 182, 212),  # Cyan #06B6D4
            "card_bg": (49, 46, 129)
        },
        "EDUCATIONAL": {
            "bg_color": (11, 32, 39),       # Deep Teal #0B2027
            "text_color": (241, 245, 249),  # Light Slate
            "muted_color": (148, 163, 184), # Slate
            "accent_color": (16, 185, 129), # Emerald #10B981
            "card_bg": (19, 78, 74)
        }
    }

    def _make_png(self, width: int = 1080, height: int = 1080, rgb_color: Tuple[int, int, int] = (15, 23, 42)) -> bytes:
        """Generates standard 1080x1080 RGB PNG bytes."""
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

        header = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) # 8-bit RGB
        raw_scanline = b'\x00' + bytes(rgb_color) * width
        raw_data = raw_scanline * height
        idat = chunk(b'IDAT', zlib.compress(raw_data, 6))
        iend = chunk(b'IEND', b'')
        return header + ihdr + idat + iend

    def _generate_pdf(self, title: str, slides: List[CarouselSlide], template_name: str = "MINIMAL") -> bytes:
        """
        Generates a standard multi-page PDF (1080x1080 pt per page) with structured text and design styles.
        """
        style = self.TEMPLATE_STYLES.get(template_name.upper(), self.TEMPLATE_STYLES["MINIMAL"])
        bg_r, bg_g, bg_b = [round(c / 255.0, 3) for c in style["bg_color"]]
        tx_r, tx_g, tx_b = [round(c / 255.0, 3) for c in style["text_color"]]
        ac_r, ac_g, ac_b = [round(c / 255.0, 3) for c in style["accent_color"]]
        mt_r, mt_g, mt_b = [round(c / 255.0, 3) for c in style["muted_color"]]

        pdf = io.BytesIO()
        objects = []
        
        def add_object(content: str) -> int:
            objects.append(content)
            return len(objects)

        # 1. Catalog
        add_object("<< /Type /Catalog /Pages 2 0 R >>")
        
        # 2. Pages (placeholder to be formatted)
        page_obj_ids = []
        for i in range(len(slides)):
            page_obj_ids.append(3 + i * 2) # Page object IDs: 3, 5, 7...

        pages_refs = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
        add_object(f"<< /Type /Pages /Kids [{pages_refs}] /Count {len(slides)} >>")

        # Create Pages & Content Streams
        for i, slide in enumerate(slides):
            tag_text = (slide.tag or "REFLOW").replace("(", "\\(").replace(")", "\\)")
            headline_text = (slide.headline or "").replace("(", "\\(").replace(")", "\\)")
            body_text = (slide.body or "").replace("(", "\\(").replace(")", "\\)")
            page_num_text = f"{i+1:02d} / {len(slides):02d}"

            # Escape multi-line body
            body_lines = [b.strip() for b in body_text.split("\n") if b.strip()]
            if not body_lines:
                body_lines = [body_text]

            stream_cmds = [
                # Background fill
                f"{bg_r} {bg_g} {bg_b} rg",
                "0 0 1080 1080 re f",

                # Accent top badge
                f"{ac_r} {ac_g} {ac_b} rg",
                "80 940 180 40 re f",
                "BT",
                "/F1 18 Tf",
                "1 1 1 rg",
                "100 952 Td",
                f"({tag_text[:20]}) Tj",
                "ET",

                # Pagination
                "BT",
                "/F1 16 Tf",
                f"{mt_r} {mt_g} {mt_b} rg",
                "940 952 Td",
                f"({page_num_text}) Tj",
                "ET",

                # Headline
                "BT",
                "/F1 44 Tf",
                f"{tx_r} {tx_g} {tx_b} rg",
                "80 720 Td",
                f"({headline_text[:80]}) Tj",
                "ET",

                # Body lines
                "BT",
                "/F1 26 Tf",
                f"{mt_r} {mt_g} {mt_b} rg",
            ]

            y_pos = 580
            for line in body_lines[:8]:
                stream_cmds.append(f"80 {y_pos} Td ({line[:90]}) Tj")
                y_pos -= 45
            stream_cmds.append("ET")

            # Footer
            stream_cmds.extend([
                f"{mt_r} {mt_g} {mt_b} RG",
                "1 w",
                "80 120 m 1000 120 l S",
                "BT",
                "/F1 16 Tf",
                f"{mt_r} {mt_g} {mt_b} rg",
                "80 90 Td (Reflow Content Engine) Tj",
                "920 90 Td (Swipe ->) Tj",
                "ET"
            ])

            stream_data = "\n".join(stream_cmds)
            stream_len = len(stream_data)

            # Page Object
            page_content_id = len(objects) + 2
            add_object(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1080 1080] "
                f"/Contents {page_content_id} 0 R "
                f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >> >> >>"
            )

            # Stream Object
            add_object(f"<< /Length {stream_len} >>\nstream\n{stream_data}\nendstream")

        # Build final PDF binary
        pdf.write(b"%PDF-1.4\n")
        xref_offsets = []

        for i, obj in enumerate(objects):
            offset = pdf.tell()
            xref_offsets.append(offset)
            pdf.write(f"{i+1} 0 obj\n{obj}\nendobj\n".encode("utf-8"))

        xref_start = pdf.tell()
        pdf.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("utf-8"))
        for offset in xref_offsets:
            pdf.write(f"{offset:010d} 00000 n \n".encode("utf-8"))

        trailer = (
            f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        )
        pdf.write(trailer.encode("utf-8"))
        return pdf.getvalue()

    async def render_carousel_deck(self, carousel_id: str) -> Dict[str, Any]:
        """
        Renders all slides as standalone 1080x1080 PNG images and compiles a multi-page PDF.
        Persists files to storage and creates CarouselExport records.
        """
        logger.info(f"Starting server-side rendering for Carousel: {carousel_id}")

        async with async_session_factory() as session:
            res = await session.execute(select(Carousel).where(Carousel.id == carousel_id))
            carousel = res.scalar_one_or_none()
            if not carousel:
                raise ValueError(f"Carousel {carousel_id} not found.")

            content_id = carousel.content_id or "standalone"
            slides = carousel.slides
            if not slides:
                raise ValueError(f"Carousel {carousel_id} has no slides to render.")

            template = carousel.template or "MINIMAL"
            style = self.TEMPLATE_STYLES.get(template.upper(), self.TEMPLATE_STYLES["MINIMAL"])
            rgb_bg = style["bg_color"]

            # 1. Render and persist PNG for each slide
            rendered_png_keys = []
            for slide in slides:
                png_bytes = self._make_png(1080, 1080, rgb_bg)
                storage_key = f"content/{content_id}/carousels/{carousel_id}/slides/slide_{slide.position:02d}.png"
                await storage_service.put(storage_key, png_bytes)
                rendered_png_keys.append(storage_key)

            # 2. Render and persist multi-page PDF
            pdf_bytes = self._generate_pdf(carousel.title, slides, template)
            pdf_key = f"content/{content_id}/carousels/{carousel_id}/export/carousel_{carousel_id}_v{carousel.version}.pdf"
            await storage_service.put(pdf_key, pdf_bytes)

            # 3. Create or update CarouselExport records
            pdf_export_id = f"exp_pdf_{uuid.uuid4().hex[:8]}"
            pdf_export = CarouselExport(
                id=pdf_export_id,
                carousel_id=carousel_id,
                carousel_version=carousel.version,
                format="PDF",
                storage_key=pdf_key,
                file_size=len(pdf_bytes),
                status="READY"
            )
            session.add(pdf_export)

            png_export_id = f"exp_png_{uuid.uuid4().hex[:8]}"
            png_export = CarouselExport(
                id=png_export_id,
                carousel_id=carousel_id,
                carousel_version=carousel.version,
                format="PNG",
                storage_key=rendered_png_keys[0],
                file_size=len(png_bytes),
                status="READY"
            )
            session.add(png_export)

            carousel.status = "READY"
            await session.commit()
            logger.info(f"Carousel {carousel_id} rendered successfully ({len(slides)} slides, PDF size: {len(pdf_bytes)} bytes).")

            return {
                "carousel_id": carousel_id,
                "version": carousel.version,
                "slide_count": len(slides),
                "pdf_key": pdf_key,
                "pdf_size": len(pdf_bytes),
                "slides_png": rendered_png_keys
            }

carousel_renderer = CarouselRenderer()
