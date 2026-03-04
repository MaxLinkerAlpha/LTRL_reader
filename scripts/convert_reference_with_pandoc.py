#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    subprocess.run(cmd, check=True, cwd=ROOT)


def convert_docx(docx: Path, out_md: Path, media_dir: Path):
    media_dir.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    run([
        'pandoc',
        str(docx.relative_to(ROOT)),
        '-f',
        'docx',
        '-t',
        'gfm',
        '--wrap=none',
        '--extract-media',
        str(media_dir),
        '-o',
        str(out_md),
    ])


def clean_markdown(md: str, title: str) -> str:
    text = md.replace('\r\n', '\n')
    text = text.replace('\u00a0', ' ')
    text = text.replace('”<img', '<img').replace('“<img', '<img')

    # Convert raw HTML img tags to markdown images for consistent rendering.
    def _img_repl(m):
        src = m.group(1).strip()
        return f'\n![图片]({src})\n'

    text = re.sub(r'<img[^>]*src="([^"]+)"[^>]*/?>', _img_repl, text, flags=re.IGNORECASE)

    # Remove HTML underline tags left by pandoc raw fragments.
    text = re.sub(r'</?u>', '', text, flags=re.IGNORECASE)

    if not text.startswith('# '):
        text = f'# {title}\n\n{text}'

    # Demote additional H1 headings to H2 to keep one document title.
    lines = text.split('\n')
    h1_seen = False
    for i, line in enumerate(lines):
        if line.startswith('# '):
            if not h1_seen:
                h1_seen = True
            else:
                lines[i] = '## ' + line[2:]
    text = '\n'.join(lines)

    # Normalize excess blank lines.
    text = re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'

    return text


def main() -> None:
    latin_docx = ROOT / 'source' / 'reference' / '拉丁语入门指南.docx'
    model_docx = ROOT / '终极语言学习模型.docx'

    latin_md = Path('data/reference/latin_guide.md')
    model_md = Path('data/reference/ultimate_model.md')

    latin_media = Path('assets/reference/latin-guide')
    model_media = Path('assets/reference/ultimate-model')

    convert_docx(latin_docx, latin_md, latin_media)
    convert_docx(model_docx, model_md, model_media)

    latin_path = ROOT / latin_md
    model_path = ROOT / model_md
    latin_clean = clean_markdown(latin_path.read_text(encoding='utf-8'), '拉丁语入门指南')
    model_clean = clean_markdown(model_path.read_text(encoding='utf-8'), '终极语言学习模型')

    latin_path.write_text(latin_clean, encoding='utf-8')
    model_path.write_text(model_clean, encoding='utf-8')


if __name__ == '__main__':
    main()
