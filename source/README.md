# Source Files 源文件目录

此目录包含 LTRL 翻译项目的原始源文件，用于版本控制和备份。

## 目录结构

```
source/
├── original/          # 原始Excel文件（勿直接修改）
├── marked/            # 添加标记后的Excel文件
├── companion/         # 伴侣文档（Word格式）
├── reference/         # 翻译规范、分析报告、术语表
└── images/            # 从Excel提取的图片
```

## 文件说明

### original/
原始Excel文件，包含：
- `LTRL Chapter O ver0.xlsx` - 引言
- `LTRL Chapter I ver0.xlsx` - 第一章
- `LTRL Chapter II ver0.xlsx` - 第二章
- `LTRL Chapter III ver0.xlsx` - 第三章
- `LTRL Chapter IV ver0.xlsx` - 第四章
- `LTRL Chapter V ver0.xlsx` - 第五章

### marked/
添加结构标记后的Excel文件，用于生成Markdown：
- 包含 `【正文原文】`、`【正文译文】` 等标记
- 用于自动化转换流程

### companion/
伴侣文档，包含翻译注释和补充材料：
- `LTRL Chapter I 伴侣1.0.docx`

### reference/
项目参考资料：
- `翻译须知及规范.docx` - 翻译规范文档
- `项目分析报告.md` - 项目分析
- `疑问汇总及术语对照表.xlsx` - 术语对照表

### images/
从Excel文件中提取的图片资源

## 工作流程

1. **编辑阶段**：在 `original/` 中的Excel文件进行翻译
2. **标记阶段**：运行 `add_markers_xml.py` 生成 `marked/` 中的文件
3. **转换阶段**：运行 `convert_marked_excel.py` 生成 `data/chapters/` 中的Markdown
4. **部署阶段**：Markdown自动部署到网站

## 注意事项

- `original/` 中的文件应保持不变，作为备份
- `marked/` 中的文件由脚本自动生成，如需修改应重新运行脚本
- 提交前确保所有修改已同步到Markdown
