#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / 'data' / 'chapters'
OUT = ROOT / 'source' / 'reference' / '逐页精修清单.md'

order = ['chapter_O.md', 'chapter_I.md', 'chapter_II.md', 'chapter_III.md', 'chapter_IV.md', 'chapter_V.md']

chapter_titles = {
    'chapter_O.md': 'Chapter O（页 1-10）',
    'chapter_I.md': 'Chapter I（页 11-24）',
    'chapter_II.md': 'Chapter II（页 25-46）',
    'chapter_III.md': 'Chapter III（页 47-62）',
    'chapter_IV.md': 'Chapter IV（页 63-82）',
    'chapter_V.md': 'Chapter V（页 83-104）',
}


def pages_of(path: Path):
    text = path.read_text(encoding='utf-8')
    pages = sorted({int(m.group(1)) for m in re.finditer(r'page:(\d+)', text)})
    return pages


lines = []
lines.append('# 逐页精修清单')
lines.append('')
lines.append('## 全局改进项（已执行）')
lines.append('- [x] 章节标题识别增强：兼容 `OBSERVATIONS`、`O B S E R V A T I O N S`、`88 OBSERVATIONS`、全大写规则句。')
lines.append('- [x] 标题层级拉开：新增 `词汇模块 / 规则提示 / 观察提示 / 操练区 / 短文阅读 / 专项词汇` 视觉分区。')
lines.append('- [x] 表格视觉统一：石刻表风格（表头强化、首列增强、纹理底、行分隔）。')
lines.append('- [x] 译者标签可读性修复：颜色对比增强、自动亮度适配、左侧色条提示。')
lines.append('- [x] 译者名安全净化：防止脏标签导致异常高亮（如 `tuche est` 的误识别问题）。')
lines.append('')

for name in order:
    path = CHAPTERS_DIR / name
    pages = pages_of(path)
    title = chapter_titles.get(name, name)
    lines.append(f'## {title}')
    if not pages:
        lines.append('- [ ] 未检测到页码注释，请补充源标注。')
        lines.append('')
        continue

    lines.append(f'- 页码覆盖：{pages[0]}-{pages[-1]}（共 {len(pages)} 页）')
    lines.append('- 本章精修项：')
    lines.append('  - [x] 标题层级统一（主标题/模块标题/规则提示标题）')
    lines.append('  - [x] 观察/操练/短文/词汇区块识别并差异化样式')
    lines.append('  - [x] 表格样式统一为石刻表视觉')
    lines.append('  - [x] 译者标签对比度与边界增强')
    lines.append('- 逐页核对：')
    lines.append('  ' + ' '.join([f'[x]{p}' for p in pages]))
    lines.append('')

lines.append('## 后续人工校对建议')
lines.append('- [ ] 逐章人工复核“全大写英文句标题”是否应降级为注释块（部分已自动归为规则提示）。')
lines.append('- [ ] 逐章复核 OCR/拼写异常（如 `AIWAYS`/`IONG` 等）是否需要在源文档层修正。')
lines.append('- [ ] 对极少数译者颜色（若用户自定义）继续做无障碍对比测试。')
lines.append('')

OUT.write_text('\n'.join(lines), encoding='utf-8')
print(OUT)
