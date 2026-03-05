#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转换伴侣文档为HTML可解析格式
添加 [ref:xxx] 标记以匹配章节内容
"""

import re
from pathlib import Path

def convert_companion():
    input_file = Path("source/companion/LTRL Chapter I 伴侣1.0.md")
    output_file = Path("data/companion/chapter-I-companion.md")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析章节
    # 伴侣文档结构: ## 语法部分, ### Section 1., ### 主格, etc.
    
    # 定义章节映射 (伴侣小标题 -> ref标记)
    section_mapping = {
        # 词汇部分
        'Vocabulary': 'vocabulary',
        '单词表': 'vocabulary',
        'Vocabulary Notes': 'vocabulary-notes',
        '词汇注释': 'vocabulary-notes',
        
        # 介词
        'Prepositions': 'prepositions',
        '介词': 'prepositions',
        
        # 派生词
        'Derivatives and Cognates': 'derivatives-and-cognates',
        '派生词和同源词': 'derivatives-and-cognates',
        
        # 观察/提示
        'OBSERVATIONS': 'observations',
        '温馨提示': 'observations',
        
        # 格相关 - 使用包含匹配
        '主格': 'nominative',
        'Nominative': 'nominative',
        '属格': 'genitive',
        'Genitive': 'genitive',
        '与格': 'dative',
        'Dative': 'dative',
        '宾格': 'accusative',
        'Accusative': 'accusative',
        '离格': 'ablative',
        'Ablative': 'ablative',
        '呼格': 'vocative',
        'Vocative': 'vocative',
        
        # 语法部分
        '语法部分': 'grammar',
        'GRAMMAR': 'grammar',
        'Section 1': 'section-1',
    }
    
    # 分割内容
    lines = content.split('\n')
    output_lines = []
    current_section = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是章节标题 (## 或 ###)
        if line.startswith('## ') or line.startswith('### '):
            # 提取标题文本
            title_match = re.search(r'^#+ \*\*(.+?)\*\*', line)
            if title_match:
                title = title_match.group(1)
                
                # 清理标题中的Markdown格式
                clean_title = re.sub(r'\*\*|\*|\<[^>]+\>', '', title).strip()
                
                # 查找匹配的ref
                ref_key = None
                for key, ref in section_mapping.items():
                    if key.lower() in clean_title.lower():
                        ref_key = ref
                        break
                
                # 如果没有找到映射，使用slugified标题
                if not ref_key:
                    ref_key = re.sub(r'[^\w\s]', '', clean_title).lower().replace(' ', '-')
                
                # 添加 [ref:xxx] 标记
                output_lines.append(line)
                output_lines.append('')
                output_lines.append(f'[ref:{ref_key}]')
            else:
                output_lines.append(line)
        else:
            output_lines.append(line)
        
        i += 1
    
    # 写入输出文件
    output_content = '\n'.join(output_lines)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✓ 已转换: {input_file} -> {output_file}")
    
    # 显示生成的ref标记
    refs = re.findall(r'\[ref:(.+?)\]', output_content)
    print(f"\n生成的ref标记 ({len(refs)}个):")
    for ref in refs:
        print(f"  - {ref}")

if __name__ == '__main__':
    convert_companion()
