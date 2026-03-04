# LTRL 拉丁语阅读器

**Learn to Read Latin (LTRL)** 的中文翻译在线阅读器。

→ **在线访问**: https://MaxLinkerAlpha.github.io/LTRL_reader

---

## 项目简介

本项目是耶鲁大学出版社出版的权威拉丁语教材《Learn to Read Latin》的民间中文翻译版。

### 功能特点

- 📖 多译者对比阅读
- 🔍 术语提示（鼠标悬停查看）
- 🔊 Forvo 发音链接
- 💡 梅老师小贴士
- 💬 GitHub 评论

---

## 版权声明

### 原书版权
- **作者**: Andrew Keller, Stephanie Russell
- **出版社**: Yale University Press
- **ISBN**: 978-0-300-11539-2 (Part 1)

### 免责声明

⚠️ 本站内容仅供学习交流使用，**禁止商业用途**。版权归原作者及出版社所有。

---

## 目录结构

```
LTRL_reader/
├── index.html              # 主页面
├── data/
│   ├── config.json         # 站点配置
│   ├── terminology.json    # 术语表
│   ├── chapters/           # 章节内容
│   └── companion/          # 梅老师小贴士
├── README.md               # 本文件
└── DEPLOY.md               # 部署指南
```

---

## 数据生成

章节 Markdown 由 Excel 源文件自动生成：

```bash
python3 scripts/regenerate_chapters_from_excel.py --root .
```

脚本会读取 `source/original/*.xlsx`，重建 `data/chapters/*.md`，并同步规范化 `data/config.json` 中的译者信息。

---

## 鸣谢

**LTRL翻译小组** - 感谢所有译者的辛勤工作和专业贡献。

- 译者（按ID）：Lanx、簪花落梅、Yancey、tuche est、Mecius
- 特别感谢：所有参与审校、润色的贡献者

本项目由 **Max Linker** 创建并维护，使用 **Kimi Code** 辅助开发。

---

**Learn to Read Laitn** 🏛️
