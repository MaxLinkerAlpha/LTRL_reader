#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一改进所有章节
- 添加分工信息
- 添加页码标记
- 优化标题格式
"""

import re
from pathlib import Path

CHAPTERS_DIR = Path("data/chapters")

# 章节分工信息
CHAPTER_DUTY = {
    'chapter_O': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：1，Lanx）（第一次润色：1，Lanx）（第二次润色：1，Πλατών）（附加评论：3，北邙Ælfræd，北邙Ælfræd，ΑΝΘΡΩΠΟ）',
    'chapter_I': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：2, 簪花落梅, tuche）（润色：？，？）（校对：？，？）',
    'chapter_II': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：？，？）（润色：？，？）（校对：？，？）',
    'chapter_III': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：？，？）（润色：？，？）（校对：？，？）',
    'chapter_IV': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：？，？）（润色：？，？）（校对：？，？）',
    'chapter_V': '（拆分：1，Lanx）（机翻：1，Lanx）（人翻：？，？）（润色：？，？）（校对：？，？）',
}

def enhance_chapter(md_file):
    """改进单个章节"""
    chapter_id = md_file.stem
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割frontmatter和正文
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
        else:
            frontmatter = ''
            body = content
    else:
        frontmatter = ''
        body = content
    
    # 1. 添加分工信息（如果不存在）
    duty = CHAPTER_DUTY.get(chapter_id, '')
    if duty and '<!-- 分工' not in body:
        # 在第一个内容块之前添加分工注释
        body = f"\n<!-- 分工: {duty} -->\n\n" + body.lstrip()
    
    # 2. 优化标题
    # 统一 OBSERVATIONS 为"温馨提示"
    body = re.sub(
        r'<div class=\'latin-text\'>\s*OBSERVATIONS?\s*</div>',
        "<div class='latin-text section-observations'>OBSERVATIONS</div>\n<div class='translation' data-translator='机翻' data-fallback='true'>温馨提示 <span class='tag'>机翻</span></div>",
        body,
        flags=re.IGNORECASE
    )
    
    # 3. 优化 VOCABULARY 标题
    body = re.sub(
        r'<div class=\'latin-text\'>\s*Vocabulary\s*</div>',
        "<div class='latin-text section-vocabulary'>Vocabulary</div>\n<div class='translation' data-translator='机翻' data-fallback='true'>词汇表 <span class='tag'>机翻</span></div>",
        body,
        flags=re.IGNORECASE
    )
    
    # 4. 优化 DRILL 标题
    body = re.sub(
        r'<div class=\'latin-text\'>\s*DRILL\s*</div>',
        "<div class='latin-text section-drill'>DRILL</div>\n<div class='translation' data-translator='机翻' data-fallback='true'>练习 <span class='tag'>机翻</span></div>",
        body,
        flags=re.IGNORECASE
    )
    
    # 5. 重建内容
    if frontmatter:
        new_content = f"---{frontmatter}---{body}"
    else:
        new_content = body
    
    # 保存
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✓ {chapter_id}: 已增强")

def main():
    print("=" * 60)
    print("统一改进所有章节")
    print("=" * 60)
    
    for md_file in sorted(CHAPTERS_DIR.glob("chapter_*.md")):
        enhance_chapter(md_file)
    
    print("\n✓ 所有章节已改进")

if __name__ == '__main__':
    main()
