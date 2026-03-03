#!/usr/bin/env python3
"""Regenerate chapter markdown files from source/original Excel workbooks.

Key rules implemented for this repository:
- Translator attribution prefers explicit translator column, then row background color mapping.
- Do NOT merge named translators into machine translation based on workflow assignment text.
- Translator notes are emitted as dedicated blocks.
- Table-like consecutive declension lines are grouped into one table block.
- Section heading hierarchy supports:
  - ## major sections
  - ### subsection (lines containing "§")
- Preserve screenshot/page metadata position from source rows.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# Canonical translator naming.
CANONICAL_NAME_MAP = {
    "tuche": "tuche est",
    "tuche est": "tuche est",
    "簪子": "簪花落梅",
    "簪花": "簪花落梅",
    "yancey": "Yancey",
    "lanx": "Lanx",
    "mecius": "Mecius",
    "机翻": "机翻",
}

DEFAULT_TRANSLATOR_COLOR = {
    "Lanx": "#FFC000",
    "簪花落梅": "#C3EAD5",
    "Yancey": "#FDEBFF",
    "tuche est": "#00A3F5",
    "Mecius": "#D58EFF",
    "李勋": "#9A38D7",
    "机翻": "#999999",
}

# Stable fallback color->translator mapping inferred from existing legend conventions.
KNOWN_COLOR_NAME = {
    "FFFFC000": "Lanx",
    "FF00A3F5": "tuche est",
    "FF00B0F0": "tuche est",
    "FFC3EAD5": "簪花落梅",
    "FFFDEBFF": "Yancey",
    "FFD58EFF": "Mecius",
    "FF9A38D7": "李勋",
    "FF99DDFF": "Yancey",
    "FF8CDDFA": "Yancey",
}

CHAPTER_FILES = [
    ("O", "source/original/LTRL Chapter O ver0.xlsx", "data/chapters/chapter_O.md"),
    ("I", "source/original/LTRL Chapter I ver0.xlsx", "data/chapters/chapter_I.md"),
    ("II", "source/original/LTRL Chapter II ver0.xlsx", "data/chapters/chapter_II.md"),
    ("III", "source/original/LTRL Chapter III ver0.xlsx", "data/chapters/chapter_III.md"),
    ("IV", "source/original/LTRL Chapter IV ver0.xlsx", "data/chapters/chapter_IV.md"),
    ("V", "source/original/LTRL Chapter V ver0.xlsx", "data/chapters/chapter_V.md"),
]

KNOWN_SECTION_TITLES = {
    "vocabulary",
    "vocabulary notes",
    "derivatives and cognates",
    "derivatives",
    "prepositions",
    "observations",
    "observation",
    "principal parts",
    "compound verbs, prefixes, assimilation, and vowel weakening",
    "grammar",
    "morphology",
    "short readings",
    "summary and synopsis tables",
    "exercises",
    "单词表",
    "单词笔记",
    "温馨提示",
    "观察",
    "派生词和同源词",
}

NOT_TITLE_PATTERNS = [
    r"\bDRILL\b",
    r"\bDRILI\b",
    r"\bMAY NOW BE DONE\b",
    r"\bPAGE\s*\d+\b",
]

ADMIN_LINE_PATTERNS = [
    r"本文档仅供组内学习交流使用",
    r"认领章节/分工具体内容及流程",
    r"本章工序总认领人",
    r"认领你的专属行颜色",
    r"本章特殊规范",
    r"\(灰色表示书中例举内容\)",
    r"OCR版本校正已完成",
    r"专属行的底色",
    r"拆分：",
    r"机翻：",
    r"人翻：",
    r"润色",
    r"校对",
    r"排版/美化",
    r"游击队",
    r"简明拉丁语",
    r"暂时前来查漏补缺",
    r"截图序号",
    r"正文页数",
    r"本章分工",
]

TABLE_KEYWORDS = [
    "Nom.",
    "Gen.",
    "Dat.",
    "Acc.",
    "Abl.",
    "Voc.",
    "Singular",
    "Plural",
    "Declension",
    "Person",
    "Perfect Active Stem",
]


@dataclass
class RowRecord:
    row_no: int
    values: Dict[int, str]
    style_ids: Dict[int, int]


def col_idx(ref: str) -> int:
    m = re.match(r"([A-Z]+)", ref)
    if not m:
        return 0
    result = 0
    for ch in m.group(1):
        result = result * 26 + (ord(ch) - 64)
    return result


def parse_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: List[str] = []
    for si in root.findall("a:si", NS):
        t = si.find("a:t", NS)
        if t is not None:
            out.append(t.text or "")
            continue
        text_parts: List[str] = []
        for r in si.findall("a:r", NS):
            rt = r.find("a:t", NS)
            if rt is not None and rt.text:
                text_parts.append(rt.text)
        out.append("".join(text_parts))
    return out


def parse_styles(zf: zipfile.ZipFile) -> Tuple[List[Optional[str]], List[int]]:
    root = ET.fromstring(zf.read("xl/styles.xml"))

    fill_rgb_by_fill_id: List[Optional[str]] = []
    fills = root.find("a:fills", NS)
    if fills is None:
        fills = []
    for f in fills:
        rgb = None
        pattern = f.find("a:patternFill", NS)
        if pattern is not None:
            fg = pattern.find("a:fgColor", NS)
            if fg is not None:
                rgb = fg.attrib.get("rgb")
        fill_rgb_by_fill_id.append(rgb)

    fill_id_by_style_id: List[int] = []
    cell_xfs = root.find("a:cellXfs", NS)
    if cell_xfs is None:
        cell_xfs = []
    for xf in cell_xfs:
        fill_id_by_style_id.append(int(xf.attrib.get("fillId", 0)))

    return fill_rgb_by_fill_id, fill_id_by_style_id


def parse_sheet_rows(zf: zipfile.ZipFile, shared: List[str]) -> List[RowRecord]:
    root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    sheet_data = root.find("a:sheetData", NS)
    if sheet_data is None:
        return []

    rows: List[RowRecord] = []
    for row in sheet_data.findall("a:row", NS):
        row_no = int(row.attrib.get("r", "0"))
        values: Dict[int, str] = {}
        style_ids: Dict[int, int] = {}

        for c in row.findall("a:c", NS):
            ref = c.attrib.get("r", "")
            cidx = col_idx(ref)
            if not cidx:
                continue

            style_ids[cidx] = int(c.attrib.get("s", "0"))
            ctype = c.attrib.get("t")
            text = ""

            if ctype == "s":
                v = c.find("a:v", NS)
                if v is not None and v.text is not None:
                    idx = int(v.text)
                    if 0 <= idx < len(shared):
                        text = shared[idx]
            elif ctype == "inlineStr":
                t = c.find("a:is/a:t", NS)
                if t is not None and t.text is not None:
                    text = t.text
            else:
                v = c.find("a:v", NS)
                if v is not None and v.text is not None:
                    text = v.text

            if text.strip():
                values[cidx] = text.strip()

        if values:
            rows.append(RowRecord(row_no=row_no, values=values, style_ids=style_ids))

    return rows


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()


def contains_cjk(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s))


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def normalize_name(name: str) -> str:
    n = normalize_whitespace(name)
    n = re.sub(r"^[\[【(（]+", "", n)
    n = re.sub(r"[\]】)）]+$", "", n)
    n = re.sub(r"\s+", " ", n)
    lower = n.lower()
    if lower in CANONICAL_NAME_MAP:
        return CANONICAL_NAME_MAP[lower]
    return CANONICAL_NAME_MAP.get(n, n)


def rgb_to_hex(argb: Optional[str]) -> Optional[str]:
    if not argb:
        return None
    val = argb.strip().upper()
    if len(val) == 8:
        return f"#{val[2:]}"
    if len(val) == 6:
        return f"#{val}"
    return None


def dominant_row_fill(
    row: RowRecord,
    fill_rgb_by_fill_id: List[Optional[str]],
    fill_id_by_style_id: List[int],
) -> Optional[str]:
    colors: List[str] = []
    for col in range(1, 6):
        style_id = row.style_ids.get(col)
        if style_id is None or style_id >= len(fill_id_by_style_id):
            continue
        fill_id = fill_id_by_style_id[style_id]
        if fill_id >= len(fill_rgb_by_fill_id):
            continue
        rgb = fill_rgb_by_fill_id[fill_id]
        if rgb:
            colors.append(rgb)
    if not colors:
        return None
    return Counter(colors).most_common(1)[0][0]


def parse_seq_page(text: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"序号\s*(\d+)\s*[，,]\s*页数\s*(\d+)", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_shot_page(marker: str, content: str) -> Optional[Tuple[int, int]]:
    m1 = re.search(r"截图序号[:：]\s*(\d+)", marker)
    m2 = re.search(r"正文页数[:：]\s*(\d+)", content)
    if not m1 or not m2:
        return None
    return int(m1.group(1)), int(m2.group(1))


def is_translator_note(text: str, marker: str = "") -> bool:
    t = normalize_whitespace(text)
    m = normalize_whitespace(marker)
    if "译者注释" in m:
        return True
    if t.startswith("*"):
        return True
    if t.startswith("注：") or t.startswith("注:"):
        return True
    if "译者注" in t or "本句删除" in t:
        return True
    return False


def is_table_like_line(text: str) -> bool:
    t = normalize_whitespace(text)
    if not t:
        return False
    if any(k in t for k in TABLE_KEYWORDS):
        return True
    # Rough declension row pattern: starts with case abbreviation + two columns.
    if re.match(r"^(Nom|Gen|Dat|Acc|Abl|Voc)\.?\s+\S+", t):
        return True
    if re.match(r"^[1-5](st|nd|rd|th)\s+Declension", t, re.IGNORECASE):
        return True
    return False


def is_subsection_title(text: str) -> bool:
    t = normalize_whitespace(text)
    # Only explicit subsection labels should be elevated as headings.
    if re.match(r"^§\s*\d+[A-Za-z0-9.\-]*", t):
        return True
    return False


def extract_explicit_translator(raw_translator: str) -> Optional[str]:
    t = normalize_whitespace(raw_translator)
    if not t:
        return None

    m = re.search(r"译者\s*[:：]\s*([^】\]]+)", t)
    if m:
        return normalize_name(m.group(1))

    # Some sheets place only a translator name in this column.
    guessed = guess_name_from_legend_text(t)
    if guessed:
        return normalize_name(guessed)
    return None


def is_section_title(text: str) -> bool:
    t = normalize_whitespace(text)
    if not t:
        return False

    low = t.lower()
    if any(re.search(p, t, flags=re.IGNORECASE) for p in NOT_TITLE_PATTERNS):
        return False

    if low in KNOWN_SECTION_TITLES:
        return True
    if low.startswith("序号"):
        return False

    if len(t) <= 90 and re.fullmatch(r"[A-Z0-9\s,.'\-()]+", t) and any(ch.isalpha() for ch in t):
        return True

    return False


def is_admin_line(text: str) -> bool:
    t = normalize_whitespace(text)
    if not t:
        return True
    for pat in ADMIN_LINE_PATTERNS:
        if re.search(pat, t):
            return True
    if t in {"略", "图略"}:
        return True
    if "暂缓" in t and len(t) <= 12:
        return True
    if re.fullmatch(r"[A-Za-z\u4e00-\u9fff\s]{1,20}", t) and normalize_name(t) in {
        "Lanx",
        "Yancey",
        "Mecius",
        "tuche est",
        "cyan",
        "iambicus",
        "Adrian",
        "簪花落梅",
        "李勋",
        "机翻",
    }:
        return True
    return False


def guess_name_from_legend_text(text: str) -> Optional[str]:
    t = normalize_whitespace(text)
    if not t:
        return None
    for pat in ADMIN_LINE_PATTERNS:
        if re.search(pat, t):
            return None

    t = re.split(r"[（(]", t, maxsplit=1)[0]
    t = re.split(r"[，,;；]|\s{2,}|\t+", t, maxsplit=1)[0]
    t = re.split(r"\s+", t, maxsplit=1)[0]
    t = t.strip("-•· ")
    if not t:
        return None

    if re.fullmatch(r"[A-Za-z][A-Za-z\s]{0,20}", t) and len(t) <= 20:
        return normalize_name(t)
    if re.fullmatch(r"[\u4e00-\u9fffA-Za-z]{2,12}", t):
        return normalize_name(t)
    return None


def detect_color_name_map(
    rows: List[RowRecord],
    fill_rgb_by_fill_id: List[Optional[str]],
    fill_id_by_style_id: List[int],
) -> Dict[str, str]:
    color_to_name_votes: Dict[str, Counter] = {}

    legend_end = min(180, len(rows))
    for idx, row in enumerate(rows[:180]):
        line = normalize_whitespace(row.values.get(1, ""))
        if parse_seq_page(line):
            legend_end = idx
            break

    for row in rows[:legend_end]:
        text_cells = [(k, v) for k, v in row.values.items() if k <= 5 and normalize_whitespace(v)]
        if len(text_cells) != 1:
            continue
        _, text = text_cells[0]
        if len(normalize_whitespace(text)) > 60:
            continue

        color = dominant_row_fill(row, fill_rgb_by_fill_id, fill_id_by_style_id)
        if not color:
            continue

        name = guess_name_from_legend_text(text)
        if not name:
            continue

        color_to_name_votes.setdefault(color, Counter())[name] += 1

    out: Dict[str, str] = {}
    for color, votes in color_to_name_votes.items():
        out[color] = normalize_name(votes.most_common(1)[0][0])

    for color, name in KNOWN_COLOR_NAME.items():
        out.setdefault(color, normalize_name(name))

    return out


def build_translation_line(text: str, translator: str, color_hex: str) -> str:
    esc = html_escape(text)
    t_esc = html_escape(translator)
    return (
        f"<div class='translation' data-translator='{t_esc}' style='border-color:{color_hex}'>"
        f"{esc} <span class='tag' style='background:{color_hex}'>{t_esc}</span></div>"
    )


def build_translator_note_line(text: str, translator: str) -> str:
    return (
        f"<div class='translator-note' data-translator='{html_escape(translator)}'>"
        f"【译者注释】{html_escape(text)}</div>"
    )


def choose_translator(
    explicit_name: Optional[str],
    row_color: Optional[str],
    color_to_name: Dict[str, str],
) -> str:
    explicit = normalize_name(explicit_name) if explicit_name else None
    color_name = normalize_name(color_to_name[row_color]) if row_color and row_color in color_to_name else None

    # Prefer named contributors over machine translation.
    if explicit and explicit != "机翻":
        return explicit
    if color_name and color_name != "机翻":
        return color_name
    if color_name:
        return color_name
    if explicit:
        return explicit
    return "机翻"


def flush_table_buffer(out: List[str], table_buffer: List[str]) -> None:
    if len(table_buffer) < 2:
        for line in table_buffer:
            out.append(f"<div class='latin-text'>{html_escape(line)}</div>")
    else:
        out.append("<div class='table-content'>" + "<br>".join(html_escape(x) for x in table_buffer) + "</div>")
    table_buffer.clear()


def generate_marked_mode_lines(
    rows: List[RowRecord],
    fill_rgb_by_fill_id: List[Optional[str]],
    fill_id_by_style_id: List[int],
    color_to_name: Dict[str, str],
) -> Tuple[List[str], set[str], Dict[str, str]]:
    out: List[str] = []
    translators: set[str] = set()
    detected_color_by_translator: Dict[str, str] = {}
    inited_section = False
    table_buffer: List[str] = []

    for row in rows:
        marker = normalize_whitespace(row.values.get(1, ""))
        seq_info = normalize_whitespace(row.values.get(2, ""))
        raw_translator = normalize_whitespace(row.values.get(3, ""))
        content = normalize_whitespace(row.values.get(5, ""))

        if not content and marker:
            content = marker

        if not marker and not content:
            continue

        shot_page = parse_shot_page(marker, seq_info or content)
        if shot_page:
            flush_table_buffer(out, table_buffer)
            out.append(f"<!-- shot:{shot_page[0]} page:{shot_page[1]} -->")
            continue

        # keep seq/page marker at original position
        if seq_info:
            seq_page = parse_seq_page(seq_info)
            if seq_page:
                flush_table_buffer(out, table_buffer)
                out.append(f"<!-- seq:{seq_page[0]} page:{seq_page[1]} -->")
                continue

        if is_admin_line(marker) or is_admin_line(content):
            seq_page = parse_seq_page(content)
            if seq_page:
                flush_table_buffer(out, table_buffer)
                out.append(f"<!-- seq:{seq_page[0]} page:{seq_page[1]} -->")
            continue

        row_color = dominant_row_fill(row, fill_rgb_by_fill_id, fill_id_by_style_id)
        row_hex = rgb_to_hex(row_color) if row_color else None

        explicit_name = extract_explicit_translator(raw_translator)

        if "标题原文" in marker:
            flush_table_buffer(out, table_buffer)
            title = normalize_whitespace(content or marker)
            if title:
                out.append(f"## {html_escape(title)}")
                inited_section = True
            continue

        if "标题译文" in marker:
            flush_table_buffer(out, table_buffer)
            if not content:
                continue
            # Keep translated heading in same level representation.
            out.append(f"## {html_escape(content)}")
            continue

        if "正文原文" in marker or "原书脚注原文" in marker:
            if not inited_section:
                out.append("## 内容")
                inited_section = True

            if is_subsection_title(content):
                flush_table_buffer(out, table_buffer)
                out.append(f"### {html_escape(content)}")
                continue

            if is_table_like_line(content):
                table_buffer.append(content)
                continue

            flush_table_buffer(out, table_buffer)
            out.append(f"<div class='latin-text'>{html_escape(content)}</div>")
            continue

        if "正文译文" in marker or "原书脚注译文" in marker:
            flush_table_buffer(out, table_buffer)
            translator = choose_translator(explicit_name, row_color, color_to_name)
            color = DEFAULT_TRANSLATOR_COLOR.get(translator) or row_hex or "#999999"
            translators.add(translator)
            if row_hex:
                detected_color_by_translator.setdefault(translator, row_hex)

            if is_subsection_title(content):
                out.append(f"### {html_escape(content)}")
                continue

            if is_translator_note(content, marker):
                out.append(build_translator_note_line(content, translator))
            else:
                out.append(build_translation_line(content, translator, color))
            continue

        # Fallback classification
        if is_section_title(content):
            flush_table_buffer(out, table_buffer)
            out.append(f"## {html_escape(content)}")
            inited_section = True
        elif is_subsection_title(content):
            flush_table_buffer(out, table_buffer)
            out.append(f"### {html_escape(content)}")
        elif contains_cjk(content):
            flush_table_buffer(out, table_buffer)
            translator = choose_translator(explicit_name, row_color, color_to_name)
            color = DEFAULT_TRANSLATOR_COLOR.get(translator) or row_hex or "#999999"
            translators.add(translator)
            if row_hex:
                detected_color_by_translator.setdefault(translator, row_hex)
            if is_translator_note(content, marker):
                out.append(build_translator_note_line(content, translator))
            else:
                out.append(build_translation_line(content, translator, color))
        else:
            if not inited_section:
                out.append("## 内容")
                inited_section = True
            if is_table_like_line(content):
                table_buffer.append(content)
            else:
                flush_table_buffer(out, table_buffer)
                out.append(f"<div class='latin-text'>{html_escape(content)}</div>")

    flush_table_buffer(out, table_buffer)
    return out, translators, detected_color_by_translator


def generate_color_mode_lines(
    rows: List[RowRecord],
    fill_rgb_by_fill_id: List[Optional[str]],
    fill_id_by_style_id: List[int],
    color_to_name: Dict[str, str],
) -> Tuple[List[str], set[str], Dict[str, str]]:
    out: List[str] = []
    translators: set[str] = set()
    detected_color_by_translator: Dict[str, str] = {}
    inited_section = False
    table_buffer: List[str] = []

    for row in rows:
        text = normalize_whitespace(row.values.get(1, ""))
        if not text:
            continue

        seq_page = parse_seq_page(text)
        if seq_page:
            flush_table_buffer(out, table_buffer)
            out.append(f"<!-- seq:{seq_page[0]} page:{seq_page[1]} -->")
            continue

        if is_admin_line(text):
            continue

        if is_section_title(text):
            flush_table_buffer(out, table_buffer)
            out.append(f"## {html_escape(text)}")
            inited_section = True
            continue

        if is_subsection_title(text):
            flush_table_buffer(out, table_buffer)
            out.append(f"### {html_escape(text)}")
            continue

        row_color = dominant_row_fill(row, fill_rgb_by_fill_id, fill_id_by_style_id)
        row_hex = rgb_to_hex(row_color) if row_color else None

        if contains_cjk(text):
            flush_table_buffer(out, table_buffer)
            translator = choose_translator(None, row_color, color_to_name)
            color = DEFAULT_TRANSLATOR_COLOR.get(translator) or row_hex or "#999999"
            translators.add(translator)
            if row_hex:
                detected_color_by_translator.setdefault(translator, row_hex)

            if is_translator_note(text):
                out.append(build_translator_note_line(text, translator))
            else:
                out.append(build_translation_line(text, translator, color))
        else:
            if not inited_section:
                out.append("## 内容")
                inited_section = True

            if is_table_like_line(text):
                table_buffer.append(text)
            else:
                flush_table_buffer(out, table_buffer)
                out.append(f"<div class='latin-text'>{html_escape(text)}</div>")

    flush_table_buffer(out, table_buffer)
    return out, translators, detected_color_by_translator


def generate_for_workbook(
    workbook_path: Path,
    chapter_id: str,
    chapter_title: str,
) -> Tuple[str, set[str], Dict[str, str]]:
    with zipfile.ZipFile(workbook_path) as zf:
        shared = parse_shared_strings(zf)
        fill_rgb_by_fill_id, fill_id_by_style_id = parse_styles(zf)
        rows = parse_sheet_rows(zf, shared)

    color_to_name = detect_color_name_map(rows, fill_rgb_by_fill_id, fill_id_by_style_id)

    marked_score = 0
    for r in rows[:120]:
        marker = normalize_whitespace(r.values.get(1, ""))
        if marker.startswith("【") and "】" in marker:
            marked_score += 1
    marked_mode = marked_score >= 10

    if marked_mode:
        body_lines, translators, detected_colors = generate_marked_mode_lines(
            rows,
            fill_rgb_by_fill_id,
            fill_id_by_style_id,
            color_to_name,
        )
    else:
        body_lines, translators, detected_colors = generate_color_mode_lines(
            rows,
            fill_rgb_by_fill_id,
            fill_id_by_style_id,
            color_to_name,
        )

    if not body_lines:
        body_lines = ["## 内容"]

    trans_list = sorted(translators)
    title = chapter_title or f"Chapter {chapter_id}"

    header = [
        "---",
        f"id: chapter_{chapter_id}",
        f'title: "{title}"',
        "translators: [" + ", ".join(f'\"{t}\"' for t in trans_list) + "]",
        "---",
        "",
    ]

    md = "\n".join(header + body_lines).rstrip() + "\n"
    return md, translators, detected_colors


def update_config_translators(
    config_path: Path,
    translators_found: set[str],
    detected_colors: Dict[str, str],
) -> None:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    existing = {t["id"]: t for t in data.get("translators", [])}

    ordered = [
        "Lanx",
        "簪花落梅",
        "Yancey",
        "tuche est",
        "Mecius",
        "李勋",
        "机翻",
    ]

    merged: List[str] = []
    for name in ordered:
        if name in translators_found or name in existing:
            merged.append(name)
    for name in sorted(translators_found):
        if name not in merged:
            merged.append(name)

    new_translators = []
    for name in merged:
        old = existing.get(name, {})
        color = (
            DEFAULT_TRANSLATOR_COLOR.get(name)
            or detected_colors.get(name)
            or old.get("color")
            or "#666666"
        )
        desc = "待校订" if name == "机翻" else "译者"
        is_primary = name == "Lanx"
        new_translators.append(
            {
                "id": name,
                "name": name,
                "color": color,
                "is_primary": is_primary,
                "description": old.get("description", desc),
            }
        )

    data["translators"] = new_translators
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config_path = root / "data/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    chapter_titles = {c["id"]: c.get("title", c["id"]) for c in config.get("chapters", [])}

    all_translators: set[str] = set()
    merged_detected_colors: Dict[str, str] = {}

    for chapter_roman, src_rel, dst_rel in CHAPTER_FILES:
        src = root / src_rel
        dst = root / dst_rel
        chapter_id = f"chapter_{chapter_roman}"
        title = chapter_titles.get(chapter_id, chapter_id)

        md, translators, detected = generate_for_workbook(src, chapter_roman, title)
        dst.write_text(md, encoding="utf-8")

        all_translators.update(translators)
        for k, v in detected.items():
            merged_detected_colors.setdefault(k, v)

        print(f"generated {dst_rel}: translators={sorted(translators)}")

    update_config_translators(config_path, all_translators, merged_detected_colors)
    print("updated data/config.json translators")


if __name__ == "__main__":
    main()
