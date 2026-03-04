#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新构建术语表 - 从Excel正确解析
"""

import zipfile
import re
import html as html_module
import json
from pathlib import Path

def decode_unicode(text):
    if not text:
        return ""
    return html_module.unescape(text)

def parse_excel(xlsx_path):
    """解析Excel文件"""
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        with z.open('xl/worksheets/sheet1.xml') as f:
            content = f.read().decode('utf-8')
        
        try:
            with z.open('xl/sharedStrings.xml') as f:
                shared = f.read().decode('utf-8')
            shared_strings = re.findall(r'<t[^>]*>(.*?)</t>', shared, re.DOTALL)
            shared_strings = [decode_unicode(s) for s in shared_strings]
        except:
            shared_strings = []
        
        rows = {}
        
        inline_pattern = r'<c r="([A-Z]+)(\d+)"[^>]*t="inlineStr"[^>]*>.*?<t[^>]*>(.*?)</t>.*?</c>'
        for col, row, text in re.findall(inline_pattern, content, re.DOTALL):
            row = int(row)
            text = decode_unicode(text)
            if row not in rows:
                rows[row] = {}
            rows[row][col] = text
        
        s_pattern = r'<c r="([A-Z]+)(\d+)"[^>]*t="s"[^>]*>.*?<v>(\d+)</v>.*?</c>'
        for col, row, idx in re.findall(s_pattern, content, re.DOTALL):
            row = int(row)
            idx = int(idx)
            if idx < len(shared_strings):
                if row not in rows:
                    rows[row] = {}
                rows[row][col] = shared_strings[idx]
    
    return rows

def is_chinese(text):
    """判断是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def is_english_only(text):
    """判断是否只包含英文字符"""
    return bool(re.match(r'^[a-zA-Z\s\(\)/\-]+$', text.strip()))

def process_terminology(rows):
    """处理术语数据"""
    terminology = []
    
    for i in range(4, max(rows.keys()) + 1):
        if i not in rows:
            continue
        
        row_data = rows[i]
        
        latin = row_data.get('A', '').strip()
        english = row_data.get('B', '').strip()
        translation = row_data.get('C', '').strip()
        abbreviation = row_data.get('D', '').strip()
        alternatives = row_data.get('E', '').strip()
        example = row_data.get('F', '').strip()
        
        # 跳过空行
        if not english and not translation:
            continue
        
        # 检测中英文是否颠倒
        # 如果B列主要是中文，C列主要是英文，则交换
        if is_chinese(english) and (is_english_only(translation) or not translation):
            english, translation = translation, english
        
        # 清理英文术语
        english_clean = english.rstrip(',').strip()
        
        # 处理Ablative系列术语（以"of "开头）
        if english_clean.startswith('of '):
            full_term = f"Ablative {english_clean}"
            
            # 使用合适的译文（添加"夺格"后缀）
            if translation and '夺格' not in translation:
                translation = translation + "夺格"
            
            terminology.append({
                'term': full_term,
                'translation': translation if translation else '',
                'abbreviation': abbreviation if abbreviation else None,
                'alternatives': alternatives if alternatives else None,
                'explanation': example if example else None
            })
            continue
        
        # 处理特殊术语
        if english_clean == 'Absolute':
            terminology.append({
                'term': 'Ablative Absolute',
                'translation': '独立夺格',
                'abbreviation': None,
                'alternatives': None,
                'explanation': None
            })
            continue
        
        # 跳过无效术语
        if len(english_clean) <= 1:
            continue
        
        # 跳过无意义译文
        if translation in ['E', '']:
            continue
        
        # 跳过一些明显错误的术语（根据观察到的模式）
        if 'irrational spondee' in translation:
            # 这是错误的译文，使用正确的
            translation = '方式夺格'
        
        # 保存普通术语
        if translation:
            terminology.append({
                'term': english_clean,
                'translation': translation,
                'abbreviation': abbreviation if abbreviation else None,
                'alternatives': alternatives if alternatives else None,
                'explanation': example if example else None
            })
    
    return terminology

def main():
    xlsx_path = Path("source/reference/术语对照表.xlsx")
    
    print("解析Excel...")
    rows = parse_excel(xlsx_path)
    print(f"  共 {len(rows)} 行")
    
    print("\n处理术语...")
    terms = process_terminology(rows)
    print(f"  提取 {len(terms)} 个术语")
    
    # 转换为字典格式
    output = {}
    seen_terms = set()  # 用于去重
    
    for term in terms:
        if not term['translation']:
            continue
        
        # 生成安全的key
        safe_key = re.sub(r'[^\w\s]', '', term['term']).strip().lower().replace(' ', '_')
        safe_key = re.sub(r'_+', '_', safe_key)
        safe_key = safe_key[:50]
        
        # 检查是否已存在
        term_key = term['term'].lower()
        if term_key in seen_terms:
            continue
        seen_terms.add(term_key)
        
        # 避免key冲突
        if safe_key in output:
            safe_key = f"{safe_key}_{len(output)}"
        
        output[safe_key] = term
    
    # 保存JSON
    json_path = Path("data/terminology.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已保存: {json_path} ({len(output)} 条)")
    
    # 生成Markdown
    md_path = Path("术语对照表整理.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 术语对照表\n\n")
        f.write("> 来源：《剑桥古典希腊语语法》《拉丁语语法新编》\n\n")
        f.write(f"> 共 {len(output)} 条术语\n\n")
        
        # 按首字母分组
        current_letter = ''
        for term in sorted(output.values(), key=lambda x: x['term'].lower()):
            first_letter = term['term'][0].upper() if term['term'] else '#'
            if first_letter != current_letter:
                current_letter = first_letter
                f.write(f"\n## {current_letter}\n\n")
            
            f.write(f"### {term['term']}\n")
            f.write(f"- **译名**: {term['translation']}\n")
            if term['abbreviation']:
                f.write(f"- **简称**: {term['abbreviation']}\n")
            if term['alternatives']:
                f.write(f"- **备选**: {term['alternatives']}\n")
            if term['explanation']:
                f.write(f"- **说明**: {term['explanation']}\n")
            f.write("\n")
    
    print(f"  ✓ 已保存: {md_path}")

if __name__ == '__main__':
    main()
