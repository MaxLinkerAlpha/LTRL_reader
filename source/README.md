# Source Files 源文件目录

此目录包含 LTRL 翻译项目的原始源文件，用于版本控制和备份。

## 目录结构

```
source/
├── original/          # 原始Excel文件（勿直接修改）
├── marked/            # 添加标记后的Excel文件
├── companion/         # 伴侣文档
└── reference/         # 翻译规范、分析报告、术语表
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
- `chapter-1-companion.md` - 第一章伴侣注释

伴侣文档内容为各章节重点语法概念的详细讲解，包含例句分析和扩展阅读推荐。

### reference/
项目参考资料：
- `翻译须知及规范.docx` - 翻译规范文档
- `项目分析报告.md` - 项目分析
- `疑问汇总及术语对照表.xlsx` - 术语对照表（800+术语）

## 工作流程

1. **编辑阶段**：在 `original/` 中的Excel文件进行翻译
2. **标记阶段**：运行标记脚本生成 `marked/` 中的文件
3. **转换阶段**：将标记后的Excel转换为 `data/chapters/` 中的Markdown
4. **部署阶段**：Markdown自动部署到网站

## 注意事项

- `original/` 中的文件应保持不变，作为备份
- `marked/` 中的文件由脚本自动生成，如需修改应重新运行脚本
- 提交前确保所有修改已同步到Markdown

---

## 鸣谢

**LTRL翻译小组** - 所有译者均隶属于此小组，感谢他们的辛勤工作和专业贡献。

---

**Learn to Read Laitn** 🏛️
