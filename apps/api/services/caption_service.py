import re
import math
import zlib
import struct
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from utils.logging import get_logger

logger = get_logger("CaptionService")

# Standard 8x12 readable bitmap font definitions for ASCII characters (32..126)
FONT_BITMAPS: Dict[str, List[int]] = {
    ' ': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '!': [0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x00,0x00,0x18,0x18,0x00],
    '"': [0x66,0x66,0x66,0x24,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '#': [0x24,0x24,0x7E,0x24,0x24,0x7E,0x24,0x24,0x00,0x00,0x00,0x00],
    '$': [0x18,0x3E,0x60,0x3C,0x06,0x7C,0x18,0x18,0x00,0x00,0x00,0x00],
    '%': [0x62,0x66,0x0C,0x18,0x30,0x66,0x46,0x00,0x00,0x00,0x00,0x00],
    '&': [0x38,0x6C,0x38,0x76,0xDC,0xCC,0x76,0x00,0x00,0x00,0x00,0x00],
    "'": [0x18,0x18,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '(': [0x0C,0x18,0x30,0x30,0x30,0x18,0x0C,0x00,0x00,0x00,0x00,0x00],
    ')': [0x30,0x18,0x0C,0x0C,0x0C,0x18,0x30,0x00,0x00,0x00,0x00,0x00],
    '*': [0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00,0x00,0x00,0x00,0x00],
    '+': [0x00,0x18,0x18,0x7E,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00],
    ',': [0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x08,0x10,0x00,0x00],
    '-': [0x00,0x00,0x00,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '.': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00,0x00,0x00],
    '/': [0x02,0x06,0x0C,0x18,0x30,0x60,0x40,0x00,0x00,0x00,0x00,0x00],
    '0': [0x3C,0x66,0x6E,0x76,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    '1': [0x18,0x38,0x18,0x18,0x18,0x18,0x7E,0x00,0x00,0x00,0x00,0x00],
    '2': [0x3C,0x66,0x06,0x1C,0x30,0x60,0x7E,0x00,0x00,0x00,0x00,0x00],
    '3': [0x3C,0x66,0x06,0x1C,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    '4': [0x0C,0x1C,0x34,0x64,0x7E,0x04,0x04,0x00,0x00,0x00,0x00,0x00],
    '5': [0x7E,0x60,0x7C,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    '6': [0x1C,0x30,0x60,0x7C,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    '7': [0x7E,0x06,0x0C,0x18,0x30,0x30,0x30,0x00,0x00,0x00,0x00,0x00],
    '8': [0x3C,0x66,0x66,0x3C,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    '9': [0x3C,0x66,0x66,0x3E,0x06,0x0C,0x38,0x00,0x00,0x00,0x00,0x00],
    ':': [0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00,0x00,0x00,0x00,0x00],
    ';': [0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x08,0x10,0x00,0x00,0x00],
    '<': [0x06,0x0C,0x18,0x30,0x18,0x0C,0x06,0x00,0x00,0x00,0x00,0x00],
    '=': [0x00,0x00,0x7E,0x00,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '>': [0x60,0x30,0x18,0x0C,0x18,0x30,0x60,0x00,0x00,0x00,0x00,0x00],
    '?': [0x3C,0x66,0x06,0x0C,0x18,0x00,0x18,0x00,0x00,0x00,0x00,0x00],
    '@': [0x3C,0x66,0x6E,0x6A,0x6E,0x60,0x3C,0x00,0x00,0x00,0x00,0x00],
    'A': [0x18,0x3C,0x66,0x66,0x7E,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'B': [0x7C,0x66,0x66,0x7C,0x66,0x66,0x7C,0x00,0x00,0x00,0x00,0x00],
    'C': [0x3C,0x66,0x60,0x60,0x60,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'D': [0x78,0x6C,0x66,0x66,0x66,0x6C,0x78,0x00,0x00,0x00,0x00,0x00],
    'E': [0x7E,0x60,0x60,0x7C,0x60,0x60,0x7E,0x00,0x00,0x00,0x00,0x00],
    'F': [0x7E,0x60,0x60,0x7C,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00],
    'G': [0x3C,0x66,0x60,0x6E,0x66,0x66,0x3E,0x00,0x00,0x00,0x00,0x00],
    'H': [0x66,0x66,0x66,0x7E,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'I': [0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00],
    'J': [0x0E,0x06,0x06,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'K': [0x66,0x6C,0x78,0x70,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00],
    'L': [0x60,0x60,0x60,0x60,0x60,0x60,0x7E,0x00,0x00,0x00,0x00,0x00],
    'M': [0x63,0x77,0x7F,0x6B,0x63,0x63,0x63,0x00,0x00,0x00,0x00,0x00],
    'N': [0x66,0x76,0x7E,0x7E,0x6E,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'O': [0x3C,0x66,0x66,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'P': [0x7C,0x66,0x66,0x7C,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00],
    'Q': [0x3C,0x66,0x66,0x66,0x6A,0x6C,0x36,0x00,0x00,0x00,0x00,0x00],
    'R': [0x7C,0x66,0x66,0x7C,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00],
    'S': [0x3C,0x66,0x60,0x3C,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'T': [0x7E,0x18,0x18,0x18,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00],
    'U': [0x66,0x66,0x66,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'V': [0x66,0x66,0x66,0x66,0x66,0x3C,0x18,0x00,0x00,0x00,0x00,0x00],
    'W': [0x63,0x63,0x63,0x6B,0x7F,0x77,0x63,0x00,0x00,0x00,0x00,0x00],
    'X': [0x66,0x66,0x3C,0x18,0x3C,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'Y': [0x66,0x66,0x66,0x3C,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00],
    'Z': [0x7E,0x06,0x0C,0x18,0x30,0x60,0x7E,0x00,0x00,0x00,0x00,0x00],
    '[': [0x3C,0x30,0x30,0x30,0x30,0x30,0x3C,0x00,0x00,0x00,0x00,0x00],
    '\\': [0x40,0x60,0x30,0x18,0x0C,0x06,0x02,0x00,0x00,0x00,0x00,0x00],
    ']': [0x3C,0x0C,0x0C,0x0C,0x0C,0x0C,0x3C,0x00,0x00,0x00,0x00,0x00],
    '^': [0x18,0x3C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    '_': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF,0x00,0x00],
    '`': [0x18,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
    'a': [0x00,0x00,0x3C,0x06,0x3E,0x66,0x3E,0x00,0x00,0x00,0x00,0x00],
    'b': [0x60,0x60,0x7C,0x66,0x66,0x66,0x7C,0x00,0x00,0x00,0x00,0x00],
    'c': [0x00,0x00,0x3C,0x66,0x60,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'd': [0x06,0x06,0x3E,0x66,0x66,0x66,0x3E,0x00,0x00,0x00,0x00,0x00],
    'e': [0x00,0x00,0x3C,0x66,0x7E,0x60,0x3C,0x00,0x00,0x00,0x00,0x00],
    'f': [0x0E,0x18,0x3E,0x18,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00],
    'g': [0x00,0x00,0x3E,0x66,0x66,0x3E,0x06,0x3C,0x00,0x00,0x00,0x00],
    'h': [0x60,0x60,0x7C,0x66,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'i': [0x18,0x00,0x38,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00],
    'j': [0x06,0x00,0x0E,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'k': [0x60,0x60,0x66,0x6C,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00],
    'l': [0x38,0x18,0x18,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00],
    'm': [0x00,0x00,0x66,0x7F,0x7B,0x63,0x63,0x00,0x00,0x00,0x00,0x00],
    'n': [0x00,0x00,0x7C,0x66,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00],
    'o': [0x00,0x00,0x3C,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00],
    'p': [0x00,0x00,0x7C,0x66,0x66,0x7C,0x60,0x60,0x00,0x00,0x00,0x00],
    'q': [0x00,0x00,0x3E,0x66,0x66,0x3E,0x06,0x06,0x00,0x00,0x00,0x00],
    'r': [0x00,0x00,0x7C,0x66,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00],
    's': [0x00,0x00,0x3E,0x60,0x3C,0x06,0x7C,0x00,0x00,0x00,0x00,0x00],
    't': [0x18,0x18,0x7E,0x18,0x18,0x18,0x0E,0x00,0x00,0x00,0x00,0x00],
    'u': [0x00,0x00,0x66,0x66,0x66,0x66,0x3E,0x00,0x00,0x00,0x00,0x00],
    'v': [0x00,0x00,0x66,0x66,0x66,0x3C,0x18,0x00,0x00,0x00,0x00,0x00],
    'w': [0x00,0x00,0x63,0x6B,0x7F,0x36,0x22,0x00,0x00,0x00,0x00,0x00],
    'x': [0x00,0x00,0x66,0x3C,0x18,0x3C,0x66,0x00,0x00,0x00,0x00,0x00],
    'y': [0x00,0x00,0x66,0x66,0x66,0x3E,0x06,0x3C,0x00,0x00,0x00,0x00],
    'z': [0x00,0x00,0x7E,0x0C,0x18,0x30,0x7E,0x00,0x00,0x00,0x00,0x00],
}

@dataclass
class CaptionCue:
    start_time: float  # Relative to clip start (seconds)
    end_time: float    # Relative to clip start (seconds)
    text: str
    highlight_words: List[str] = field(default_factory=list)

class CaptionService:
    """
    Subsystem for short-form caption segmentation, timing alignment,
    SRT/VTT export, ASS generation, and RGBA overlay rasterization.
    """

    STYLE_PRESETS = {
        "BOLD_PUNCH": {
            "name": "Bold Punch (Viral)",
            "fontname": "Arial",
            "scale_9_16": 5,
            "scale_1_1": 4,
            "scale_4_5": 4,
            "scale_16_9": 3,
            "text_color": (255, 230, 0, 255),       # Vibrant Yellow
            "highlight_color": (0, 255, 255, 255),   # Bright Cyan
            "pill_bg": (10, 10, 15, 220),            # Deep dark card
            "border_color": (255, 230, 0, 180),
            "margin_v_9_16": 320,
            "margin_v_1_1": 90,
            "margin_v_4_5": 130,
            "margin_v_16_9": 70,
        },
        "CLEAN_SUBTITLE": {
            "name": "Clean Subtitle",
            "fontname": "Arial",
            "scale_9_16": 4,
            "scale_1_1": 3,
            "scale_4_5": 3,
            "scale_16_9": 3,
            "text_color": (255, 255, 255, 255),     # Clean White
            "highlight_color": (99, 102, 241, 255),  # Indigo Highlight
            "pill_bg": (15, 23, 42, 210),            # Slate card
            "border_color": (99, 102, 241, 150),
            "margin_v_9_16": 260,
            "margin_v_1_1": 80,
            "margin_v_4_5": 110,
            "margin_v_16_9": 60,
        },
        "KINETIC_HIGHLIGHT": {
            "name": "Kinetic Highlight",
            "fontname": "Arial",
            "scale_9_16": 5,
            "scale_1_1": 4,
            "scale_4_5": 4,
            "scale_16_9": 3,
            "text_color": (255, 255, 255, 255),     # Pure White
            "highlight_color": (0, 255, 200, 255),   # Neon Mint/Cyan
            "pill_bg": (20, 15, 35, 230),            # Dark Violet card
            "border_color": (0, 255, 200, 180),
            "margin_v_9_16": 290,
            "margin_v_1_1": 85,
            "margin_v_4_5": 120,
            "margin_v_16_9": 65,
        },
        "MINIMAL_WHITE": {
            "name": "Minimal White",
            "fontname": "Arial",
            "scale_9_16": 3,
            "scale_1_1": 3,
            "scale_4_5": 3,
            "scale_16_9": 2,
            "text_color": (245, 245, 245, 255),     # Soft White
            "highlight_color": (16, 185, 129, 255),  # Emerald Green
            "pill_bg": (0, 0, 0, 180),               # Minimal translucent black
            "border_color": (255, 255, 255, 80),
            "margin_v_9_16": 240,
            "margin_v_1_1": 70,
            "margin_v_4_5": 90,
            "margin_v_16_9": 50,
        }
    }

    def generate_cues_from_segments(
        self,
        clip_start: float,
        clip_end: float,
        segments: List[Dict[str, Any]],
        highlight_keywords: Optional[List[str]] = None,
        max_words_per_cue: int = 4
    ) -> List[CaptionCue]:
        """
        Extracts and aligns transcript segments falling within [clip_start, clip_end],
        shifting times to start at 0.0, and sub-segmenting long sentences into
        punchy short-form beats (1-4 words per beat).
        """
        cues: List[CaptionCue] = []
        clip_duration = max(0.1, clip_end - clip_start)
        keywords_lower = [k.strip().lower() for k in (highlight_keywords or []) if k.strip()]

        for seg in segments:
            seg_start = float(seg.get("start_time", 0.0))
            seg_end = float(seg.get("end_time", 0.0))
            seg_text = seg.get("text", "").strip()

            if not seg_text:
                continue

            # Check for overlap with clip range
            if seg_end <= clip_start or seg_start >= clip_end:
                continue

            # Clip segment to boundaries
            clamped_start = max(clip_start, seg_start)
            clamped_end = min(clip_end, seg_end)
            if clamped_end <= clamped_start:
                continue

            rel_start = round(clamped_start - clip_start, 3)
            rel_end = round(clamped_end - clip_start, 3)
            rel_duration = max(0.1, rel_end - rel_start)

            words = seg_text.split()
            if not words:
                continue

            if len(words) <= max_words_per_cue:
                hl = [w for w in words if re.sub(r'[^\w]', '', w).lower() in keywords_lower]
                cues.append(CaptionCue(
                    start_time=rel_start,
                    end_time=rel_end,
                    text=seg_text,
                    highlight_words=hl
                ))
            else:
                num_chunks = math.ceil(len(words) / max_words_per_cue)
                chunk_duration = rel_duration / num_chunks

                for i in range(num_chunks):
                    chunk_words = words[i * max_words_per_cue : (i + 1) * max_words_per_cue]
                    c_start = round(rel_start + (i * chunk_duration), 3)
                    c_end = round(min(rel_end, c_start + chunk_duration), 3)
                    c_text = " ".join(chunk_words)
                    hl = [w for w in chunk_words if re.sub(r'[^\w]', '', w).lower() in keywords_lower]

                    cues.append(CaptionCue(
                        start_time=c_start,
                        end_time=c_end,
                        text=c_text,
                        highlight_words=hl
                    ))

        if not cues and clip_duration > 0:
            cues.append(CaptionCue(
                start_time=0.0,
                end_time=clip_duration,
                text="[Video Highlight]",
                highlight_words=[]
            ))

        return sorted(cues, key=lambda c: c.start_time)

    def _format_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_vtt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def build_srt(self, cues: List[CaptionCue]) -> str:
        lines = []
        for idx, cue in enumerate(cues, start=1):
            lines.append(str(idx))
            lines.append(f"{self._format_srt_time(cue.start_time)} --> {self._format_srt_time(cue.end_time)}")
            lines.append(cue.text)
            lines.append("")
        return "\n".join(lines)

    def build_vtt(self, cues: List[CaptionCue]) -> str:
        lines = ["WEBVTT", ""]
        for idx, cue in enumerate(cues, start=1):
            lines.append(str(idx))
            lines.append(f"{self._format_vtt_time(cue.start_time)} --> {self._format_vtt_time(cue.end_time)}")
            lines.append(cue.text)
            lines.append("")
        return "\n".join(lines)

    def _format_ass_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        if cs >= 100: cs = 99
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def build_ass(
        self,
        cues: List[CaptionCue],
        style_name: str = "BOLD_PUNCH",
        aspect_ratio: str = "9:16",
        highlight_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Generates Advanced SubStation Alpha (.ass) subtitle file content
        with typography, safe-area positioning, outline, shadow, and word highlighting.
        """
        style = self.STYLE_PRESETS.get(style_name, self.STYLE_PRESETS["BOLD_PUNCH"])

        res_map = {
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "4:5": (1080, 1350),
            "16:9": (1920, 1080)
        }
        res_x, res_y = res_map.get(aspect_ratio, (1080, 1920))
        clean_ratio = aspect_ratio.replace(":", "_")
        margin_v = style.get(f"margin_v_{clean_ratio}", 280)
        fontsize = 54 if "9_16" in clean_ratio else 44

        keywords_lower = [k.strip().lower() for k in (highlight_keywords or []) if k.strip()]

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ReflowCaption,Arial,{fontsize},&H0000FFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3.5,2.0,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for cue in cues:
            start_str = self._format_ass_time(cue.start_time)
            end_str = self._format_ass_time(cue.end_time)

            formatted_text = cue.text
            if keywords_lower:
                words = formatted_text.split()
                styled_words = []
                for w in words:
                    clean_w = re.sub(r'[^\w]', '', w).lower()
                    if clean_w in keywords_lower:
                        styled_words.append(f"{{\\c&H00FFFF&\\b1}}{w}{{\\c&H0000FFFF&\\b1}}")
                    else:
                        styled_words.append(w)
                formatted_text = " ".join(styled_words)

            events.append(f"Dialogue: 0,{start_str},{end_str},ReflowCaption,,0,0,0,,{formatted_text}")

        return header + "\n".join(events) + "\n"

    def create_caption_overlay_png(
        self,
        cue: CaptionCue,
        width: int,
        height: int,
        style_name: str = "BOLD_PUNCH",
        aspect_ratio: str = "9:16",
        highlight_keywords: Optional[List[str]] = None
    ) -> bytes:
        """
        Renders a standalone transparent RGBA PNG with an aligned caption card / pill.
        """
        style = self.STYLE_PRESETS.get(style_name, self.STYLE_PRESETS["BOLD_PUNCH"])
        clean_ratio = aspect_ratio.replace(":", "_")
        scale = style.get(f"scale_{clean_ratio}", 4)
        margin_v = style.get(f"margin_v_{clean_ratio}", 280)

        text_color = style["text_color"]
        hl_color = style["highlight_color"]
        pill_bg = style["pill_bg"]
        border_color = style["border_color"]

        keywords_lower = [k.strip().lower() for k in (highlight_keywords or []) if k.strip()]

        # Prepare Words and glyph layout
        words = cue.text.split()
        char_w = 8 * scale
        char_h = 12 * scale
        space_w = 6 * scale

        # Calculate line width
        total_text_w = 0
        word_metadata = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w).lower()
            is_hl = clean_w in keywords_lower
            w_width = len(w) * char_w
            word_metadata.append((w, is_hl, w_width))
            total_text_w += w_width + space_w
        if word_metadata:
            total_text_w -= space_w

        # Safe boundaries & Pill Card sizing
        padding_x = 24 * scale // 3
        padding_y = 16 * scale // 3
        card_w = min(width - 80, total_text_w + (padding_x * 2))
        card_h = char_h + (padding_y * 2)

        card_x1 = (width - card_w) // 2
        card_x2 = card_x1 + card_w
        card_y2 = height - margin_v
        card_y1 = card_y2 - card_h

        # Initialize RGBA buffer (default fully transparent 0,0,0,0)
        # Using flat 1D list of rows for high performance
        grid = {} # (x, y) -> (r, g, b, a)

        # 1. Draw Pill Card background with rounded corners and border
        corner_r = min(card_h // 3, 24)
        for cy in range(card_y1, card_y2):
            for cx in range(card_x1, card_x2):
                # Check rounded corners
                is_inside = True
                if cx < card_x1 + corner_r and cy < card_y1 + corner_r:
                    if (cx - (card_x1 + corner_r))**2 + (cy - (card_y1 + corner_r))**2 > corner_r**2:
                        is_inside = False
                elif cx > card_x2 - corner_r and cy < card_y1 + corner_r:
                    if (cx - (card_x2 - corner_r))**2 + (cy - (card_y1 + corner_r))**2 > corner_r**2:
                        is_inside = False
                elif cx < card_x1 + corner_r and cy > card_y2 - corner_r:
                    if (cx - (card_x1 + corner_r))**2 + (cy - (card_y2 - corner_r))**2 > corner_r**2:
                        is_inside = False
                elif cx > card_x2 - corner_r and cy > card_y2 - corner_r:
                    if (cx - (card_x2 - corner_r))**2 + (cy - (card_y2 - corner_r))**2 > corner_r**2:
                        is_inside = False

                if is_inside:
                    # Check border
                    is_border = (cx <= card_x1 + 2 or cx >= card_x2 - 3 or cy <= card_y1 + 2 or cy >= card_y2 - 3)
                    grid[(cx, cy)] = border_color if is_border else pill_bg

        # 2. Draw Characters onto Grid
        curr_text_x = card_x1 + padding_x
        text_y = card_y1 + padding_y

        for word, is_hl, w_w in word_metadata:
            color = hl_color if is_hl else text_color
            for ch in word:
                bitmap = FONT_BITMAPS.get(ch, FONT_BITMAPS.get('?'))
                if bitmap:
                    for row_idx, row_val in enumerate(bitmap):
                        for col_idx in range(8):
                            if (row_val >> (7 - col_idx)) & 1:
                                # Scale pixel
                                for sy in range(scale):
                                    for sx in range(scale):
                                        px = curr_text_x + (col_idx * scale) + sx
                                        py = text_y + (row_idx * scale) + sy
                                        if 0 <= px < width and 0 <= py < height:
                                            grid[(px, py)] = color
                curr_text_x += char_w
            curr_text_x += space_w

        # 3. Assemble PNG data chunks
        raw_rows = bytearray()
        for y in range(height):
            raw_rows.append(0) # Filter type 0
            for x in range(width):
                px_val = grid.get((x, y), (0, 0, 0, 0))
                raw_rows.extend(px_val)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

        png = bytearray(b'\x89PNG\r\n\x1a\n')
        png.extend(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)))
        png.extend(chunk(b'IDAT', zlib.compress(bytes(raw_rows), 6)))
        png.extend(chunk(b'IEND', b''))
        return bytes(png)

caption_service = CaptionService()
