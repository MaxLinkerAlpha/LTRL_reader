#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / 'source' / 'reference' / '疑问汇总及术语对照表.xlsx'
OUT_MD = ROOT / '术语对照表整理.md'
OUT_JSON = ROOT / 'data' / 'terminology.json'

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


@dataclass
class TermEntry:
    term: str
    primary: str = ''
    alternatives: list[str] = field(default_factory=list)

    def add_alt(self, text: str):
        t = normalize_cn(text)
        if t and t != self.primary and t not in self.alternatives:
            self.alternatives.append(t)


def normalize_space(s: str) -> str:
    return re.sub(r'\s+', ' ', s.replace('\u00a0', ' ').replace('\u200b', ' ')).strip()


def normalize_term(s: str) -> str:
    s = normalize_space(s)
    s = s.replace('Instrunent', 'Instrument')
    s = re.sub(r'\s*,\s*$', '', s)
    s = re.sub(r'\s*\.$', '', s)
    s = s.strip(' ,;')
    return s


def normalize_cn(s: str) -> str:
    s = normalize_space(s)
    s = s.strip('，,；;。.')
    return s


def key_term(s: str) -> str:
    s = normalize_term(s).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def has_cjk(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', s or ''))


def split_alts(text: str) -> list[str]:
    t = normalize_cn(text)
    if not t:
        return []
    parts = re.split(r'[、；;]|\s+/\s+|\s*\|\s*', t)
    out = []
    for p in parts:
        pp = normalize_cn(p)
        if pp and pp not in out:
            out.append(pp)
    return out


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
    # 主要取顾枝鹰术语表，作为主译名优先源
    m: dict[str, str] = {}
    for _, vals in wb.iter_rows('顾枝鹰《拉丁语语法新编》术语表', max_col=3):
        cell = vals[0]
        if not cell:
            continue
        # 格式通常为: 中文 + 空格 + English/Latin
        mm = re.match(r'^(?P<cn>[\u4e00-\u9fff\[\]（）()、，。·\-—\s]+?)\s*(?P<en>[A-Za-zÀ-ž][A-Za-zÀ-ž\-’\' /]+)$', cell)
        if not mm:
            continue
        cn = normalize_cn(mm.group('cn'))
        en = normalize_term(mm.group('en'))
        if not has_cjk(cn):
            continue
        if en and cn:
            m[key_term(en)] = cn
    return m


def parse_comprehensive_terms(wb: WorkbookXml) -> OrderedDict[str, TermEntry]:
    scholar = parse_scholar_map(wb)
    entries: OrderedDict[str, TermEntry] = OrderedDict()
    table_started = False

    for rn, vals in wb.iter_rows('综合术语表', max_col=6):
        a, b, c, d = vals[0], vals[1], vals[2], vals[3]
        if not table_started:
            if a == '拉丁语' and b == '英语' and c.startswith('暂定中文'):
                table_started = True
            continue

        term = normalize_term(b)
        cn = normalize_cn(c)
        alt = normalize_cn(d)

        if not term:
            continue
        # 术语项仅保留英/拉术语，过滤混入的中文说明行
        if has_cjk(term):
            continue
        if not re.search(r'[A-Za-zÀ-ž]{3,}', term):
            continue
        # skip index headers/noise
        if key_term(term) in {'general index', 'english index'}:
            continue
        if re.fullmatch(r'[A-Z]', term):
            continue

        k = key_term(term)
        scholar_cn = scholar.get(k, '')

        primary = scholar_cn or cn
        if not primary:
            continue

        if k not in entries:
            entries[k] = TermEntry(term=term, primary=primary)
        e = entries[k]

        # prefer scholar terminology as primary if available
        if scholar_cn:
            e.primary = scholar_cn
        elif not e.primary:
            e.primary = primary

        if cn and cn != e.primary:
            e.add_alt(cn)
        for p in split_alts(alt):
            e.add_alt(p)

    return entries


def write_md(entries: OrderedDict[str, TermEntry]):
    lines = []
    lines.append('# LTRL 术语对照表')
    lines.append('')
    lines.append('> 数据源：`source/reference/疑问汇总及术语对照表.xlsx`（综合术语表）')
    lines.append('> 主译名优先策略：优先采用顾枝鹰等学者确定术语；其余保留为备选。')
    lines.append('')
    lines.append('| 英文/拉丁语 | 主要术语译文 | 备选术语译文 |')
    lines.append('|------------|-------------|-------------|')
    for e in sorted(entries.values(), key=lambda x: x.term.lower()):
        alts = ' / '.join(e.alternatives)
        lines.append(f'| {e.term} | {e.primary} | {alts} |')
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


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

        explanation = ''
        if e.alternatives:
            explanation = '备选：' + ' / '.join(e.alternatives)

        abbr = old.get(key, {}).get('abbreviation', '')
        m = re.search(r'\(([^)]+)\)', e.term)
        if not abbr and m and len(m.group(1)) <= 12:
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
