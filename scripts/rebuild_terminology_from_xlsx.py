#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / 'source' / 'reference' / '疑问汇总及术语对照表.xlsx'
OUT_MD = ROOT / '术语对照表整理.md'
OUT_JSON = ROOT / 'data' / 'terminology.json'

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

CASE_FAMILIES = {'Ablative', 'Accusative', 'Dative', 'Genitive', 'Nominative', 'Vocative', 'Locative'}


@dataclass
class TermEntry:
    term: str
    primary: str
    alternatives: list[str] = field(default_factory=list)
    abbreviation: str = ''

    def add_alt(self, text: str):
        t = normalize_cn(text)
        if not t or t == self.primary:
            return
        if t not in self.alternatives:
            self.alternatives.append(t)


def normalize_space(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').replace('\u00a0', ' ').replace('\u200b', ' ')).strip()


def normalize_term(s: str) -> str:
    s = normalize_space(s)
    s = s.replace('Instrunent', 'Instrument')
    s = s.strip(' ,;.')
    return s


def normalize_cn(s: str) -> str:
    return normalize_space(s).strip('，,；;。. ')


def has_cjk(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', s or ''))


def key_term(s: str) -> str:
    s = normalize_term(s).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def split_alts(text: str) -> list[str]:
    t = normalize_cn(text)
    if not t:
        return []
    parts = re.split(r'[、；;]|(?<!\w)/(?!\w)|\s*\|\s*', t)
    out = []
    for p in parts:
        pp = normalize_cn(p)
        if pp and pp not in out:
            out.append(pp)
    return out


def split_primary_and_alts(text: str) -> tuple[str, list[str]]:
    parts = split_alts(text)
    if not parts:
        return '', []
    return parts[0], parts[1:]


def slugify(term: str) -> str:
    s = term.lower()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return re.sub(r'_+', '_', s).strip('_') or 'term'


class WorkbookXml:
    def __init__(self, path: Path):
        self.z = ZipFile(path)
        self.shared_strings = self._load_shared_strings()
        self.sheet_targets = self._load_sheet_targets()

    def _load_shared_strings(self) -> list[str]:
        if 'xl/sharedStrings.xml' not in self.z.namelist():
            return []
        root = ET.fromstring(self.z.read('xl/sharedStrings.xml'))
        out = []
        for si in root.findall(f'{NS}si'):
            out.append(''.join(t.text or '' for t in si.iter(f'{NS}t')))
        return out

    def _load_sheet_targets(self) -> dict[str, str]:
        wb = ET.fromstring(self.z.read('xl/workbook.xml'))
        rels = ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))
        rns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
        rid_to_target = {r.attrib['Id']: r.attrib['Target'] for r in rels.findall('r:Relationship', rns)}
        out = {}
        for s in wb.findall(f'.//{NS}sheet'):
            name = s.attrib['name']
            rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            out[name] = 'xl/' + rid_to_target[rid]
        return out

    def iter_rows(self, sheet_name: str, max_col: int = 8):
        sh = ET.fromstring(self.z.read(self.sheet_targets[sheet_name]))
        col_map = {chr(ord('A') + i): i for i in range(max_col)}

        def cval(c) -> str:
            t = c.attrib.get('t')
            v = c.find(f'{NS}v')
            if v is None:
                isel = c.find(f'{NS}is')
                if isel is None:
                    return ''
                return ''.join(x.text or '' for x in isel.iter(f'{NS}t'))
            raw = v.text or ''
            if t == 's' and raw.isdigit():
                idx = int(raw)
                if idx < len(self.shared_strings):
                    return self.shared_strings[idx]
            return raw

        for r in sh.findall(f'.//{NS}row'):
            rn = int(r.attrib.get('r', '0'))
            vals = [''] * max_col
            for c in r.findall(f'{NS}c'):
                ref = c.attrib.get('r', 'A1')
                col = ''.join(ch for ch in ref if ch.isalpha())
                if col in col_map:
                    vals[col_map[col]] = normalize_space(cval(c))
            yield rn, vals


def parse_scholar_map(wb: WorkbookXml) -> dict[str, str]:
    # 顾枝鹰术语表作为“主译名优先”来源
    m = {}
    for _, vals in wb.iter_rows('顾枝鹰《拉丁语语法新编》术语表', max_col=3):
        cell = vals[1] if len(vals) > 1 else vals[0]
        if not cell:
            continue
        mm = re.match(r'^(?P<cn>[\u4e00-\u9fff\[\]（）()、，。·\-—\s]+?)\s*(?P<en>[A-Za-zÀ-ž][A-Za-zÀ-ž\-’\' /]+)$', cell)
        if not mm:
            continue
        cn = normalize_cn(mm.group('cn'))
        en = normalize_term(mm.group('en'))
        if has_cjk(cn) and en:
            m[key_term(en)] = cn
    return m


def compose_term(raw_term: str, current_family: str) -> tuple[str, str]:
    term = normalize_term(raw_term)
    # 还原 "of Accompaniment" -> "Ablative of Accompaniment"
    if current_family and re.match(r'^(of|with)\b', term, re.IGNORECASE):
        term = f'{current_family} {term}'

    first = term.split(' ', 1)[0]
    if first in CASE_FAMILIES:
        current_family = first
    return term, current_family


def parse_comprehensive_terms(wb: WorkbookXml) -> OrderedDict[str, TermEntry]:
    scholar = parse_scholar_map(wb)
    entries: OrderedDict[str, TermEntry] = OrderedDict()
    in_table = False
    current_family = ''
    raw_rows = []

    for _, vals in wb.iter_rows('综合术语表', max_col=6):
        a, b, c, d = vals[0], vals[1], vals[2], vals[3]

        if not in_table:
            if a == '【拉丁文/希腊文术语】' and b == '【英文术语】':
                in_table = True
            continue

        raw_rows.append({'term_raw': normalize_term(b), 'cn': normalize_cn(c), 'alt': normalize_cn(d)})

    # 部分表格存在“术语列与中文列错一行”的情况：如 Accentuation -> 时段(内), 下一行才是重读。
    # 使用锚点识别后，对后续行执行一次前移校正。
    anchors = {
        'Absolute': '独立夺格',
        'Accentuation': '重读',
        'antepenult': '倒三音节',
        'penult': '倒二音节',
    }
    anchor_hits = 0
    shift_start = None
    for i in range(len(raw_rows) - 1):
        t = raw_rows[i]['term_raw']
        if t in anchors and raw_rows[i]['cn'] != anchors[t] and raw_rows[i + 1]['cn'] == anchors[t]:
            anchor_hits += 1
            shift_start = i if shift_start is None else min(shift_start, i)
    if anchor_hits >= 2 and shift_start is not None:
        for i in range(shift_start, len(raw_rows) - 1):
            raw_rows[i]['cn'] = raw_rows[i + 1]['cn']

    for row in raw_rows:
        term = row['term_raw']
        cn = row['cn']
        alt = row['alt']
        if not term:
            continue

        term, current_family = compose_term(term, current_family)
        if has_cjk(term):
            continue
        if re.fullmatch(r'[A-Z]', term):
            continue
        if key_term(term) in {'general index', 'english index'}:
            continue
        if not re.search(r'[A-Za-zÀ-ž]{3,}', term):
            continue

        cn_primary, cn_alts = split_primary_and_alts(cn)
        d_alts = split_alts(alt)

        scholar_primary = scholar.get(key_term(term), '')
        primary = scholar_primary or cn_primary
        if not primary:
            continue

        k = key_term(term)
        if k not in entries:
            entries[k] = TermEntry(term=term, primary=primary)
        e = entries[k]

        if scholar_primary:
            e.primary = scholar_primary
            # scholar 主译名存在时，避免把“暂定中文”误差带入备选（保守策略）
        else:
            e.primary = primary

        for a0 in cn_alts:
            e.add_alt(a0)
        for a0 in d_alts:
            e.add_alt(a0)

    return entries


def write_md(entries: OrderedDict[str, TermEntry]):
    groups = defaultdict(list)
    for e in entries.values():
        initial = e.term[0].upper() if e.term and e.term[0].isalpha() else '#'
        groups[initial].append(e)

    lines = []
    lines.append('# LTRL 术语对照表')
    lines.append('')
    lines.append('> 数据源：`source/reference/疑问汇总及术语对照表.xlsx`（综合术语表）')
    lines.append('> 主译名优先：顾枝鹰等学者术语；同一术语的其他译法保留在“备选术语译文”。')
    lines.append('')

    ordered_keys = [k for k in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if k in groups]
    if '#' in groups:
        ordered_keys.append('#')

    for g in ordered_keys:
        lines.append(f'## {g}')
        lines.append('')
        lines.append('| 英文/拉丁语 | 主要术语译文 | 备选术语译文 |')
        lines.append('|------------|-------------|-------------|')
        for e in sorted(groups[g], key=lambda x: x.term.lower()):
            alt = ' / '.join(e.alternatives)
            lines.append(f'| {e.term} | {e.primary} | {alt} |')
        lines.append('')

    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')


def write_json(entries: OrderedDict[str, TermEntry]):
    old = json.loads(OUT_JSON.read_text(encoding='utf-8')) if OUT_JSON.exists() else {}
    term_to_key = {v.get('term', '').strip(): k for k, v in old.items() if v.get('term')}

    out = {}
    used = set()
    for e in sorted(entries.values(), key=lambda x: x.term.lower()):
        key = term_to_key.get(e.term) or slugify(e.term)
        base = key
        i = 2
        while key in used:
            key = f'{base}_{i}'
            i += 1
        used.add(key)

        explanation = '备选：' + ' / '.join(e.alternatives) if e.alternatives else ''
        abbr = old.get(key, {}).get('abbreviation', '')
        if not abbr:
            m = re.search(r'\(([^)]+)\)', e.term)
            if m and len(m.group(1)) <= 12:
                abbr = m.group(1)

        out[key] = {
            'term': e.term,
            'translation': e.primary,
            'explanation': explanation,
            'abbreviation': abbr,
        }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    wb = WorkbookXml(XLSX)
    entries = parse_comprehensive_terms(wb)
    write_md(entries)
    write_json(entries)
    print('entries:', len(entries))


if __name__ == '__main__':
    main()
