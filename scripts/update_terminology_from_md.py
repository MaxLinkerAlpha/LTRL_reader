#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_MD = ROOT / '术语对照表整理.md'
DST_JSON = ROOT / 'data' / 'terminology.json'


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or 'term'


def parse_md_tables(md_text: str):
    rows = []
    for line in md_text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < 2:
            continue
        if cols[0] in {'英文/拉丁语', '------------', ''}:
            continue
        if set(cols[0]) == {'-'}:
            continue
        term = cols[0]
        translation = cols[1] if len(cols) > 1 else ''
        alt = cols[2] if len(cols) > 2 else ''
        if not term or not translation:
            continue
        rows.append((term, translation, alt))
    return rows


def main():
    md_text = SRC_MD.read_text(encoding='utf-8')
    rows = parse_md_tables(md_text)

    old = json.loads(DST_JSON.read_text(encoding='utf-8')) if DST_JSON.exists() else {}

    # term -> existing key (preserve current IDs where possible)
    existing_term_to_key = {}
    for k, v in old.items():
        t = (v.get('term') or '').strip()
        if t and t not in existing_term_to_key:
            existing_term_to_key[t] = k

    out = {}
    used_keys = set()

    def allocate_key(term: str):
        if term in existing_term_to_key:
            k = existing_term_to_key[term]
            if k not in used_keys:
                return k
        base = slugify(term)
        k = base
        i = 2
        while k in used_keys:
            k = f'{base}_{i}'
            i += 1
        return k

    for term, translation, alt in rows:
        key = allocate_key(term)
        used_keys.add(key)
        old_entry = old.get(key, {})

        abbr = old_entry.get('abbreviation', '')
        # keep existing abbreviation when present; otherwise infer from parentheses
        if not abbr:
            m = re.search(r'\(([^)]+)\)', term)
            if m and len(m.group(1)) <= 12:
                abbr = m.group(1)

        explanation = translation
        if alt:
            explanation = f"{translation}（备选：{alt}）"

        out[key] = {
            'term': term,
            'translation': translation,
            'explanation': explanation,
            'abbreviation': abbr,
        }

    # stable order by term for readable diffs
    ordered = dict(sorted(out.items(), key=lambda kv: kv[1]['term'].lower()))
    DST_JSON.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f'rows={len(rows)} unique_terms={len({r[0] for r in rows})} output={len(ordered)}')


if __name__ == '__main__':
    main()
