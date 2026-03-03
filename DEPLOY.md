# 部署与使用指南

## 快速部署到 GitHub Pages

### 1. 创建 GitHub 仓库

如果尚未创建，请访问：https://github.com/new

仓库名称：**`LTRL_reader`**

→ 你的仓库地址：https://github.com/MaxLinkerAlpha/LTRL_reader

---

### 2. 上传文件

将以下文件上传到仓库：

```
LTRL_reader/
├── index.html              ← 主页面
├── data/
│   ├── config.json           ← 站点配置
│   ├── terminology.json      ← 术语对照表
│   ├── chapters/             ← 章节内容
│   │   ├── chapter-o.md
│   │   ├── chapter-1.md
│   │   ├── chapter-2.md
│   │   ├── chapter-3.md
│   │   ├── chapter-4.md
│   │   └── chapter-5.md
│   └── companion/            ← 伴侣注释
│       └── chapter-1-companion.md
├── README.md               ← 项目说明
└── DEPLOY.md               ← 本文件
```

**上传方法：**

方法 A：网页直接上传
1. 进入 https://github.com/MaxLinkerAlpha/LTRL_reader
2. 点击 "Add file" → "Upload files"
3. 将所有文件和文件夹拖到页面上
4. 点击 "Commit changes"

方法 B：命令行上传
```bash
# 进入项目文件夹
cd LTRL_reader

# 初始化 git
git init
git add .
git commit -m "初始化项目"

# 连接到你的 GitHub 仓库
git remote add origin https://github.com/MaxLinkerAlpha/LTRL_reader.git

# 上传
git push -u origin main
```

---

### 3. 开启 GitHub Pages

1. 访问 https://github.com/MaxLinkerAlpha/LTRL_reader/settings/pages
2. "Source" 选择 **"Deploy from a branch"**
3. "Branch" 选择 **"main"**，文件夹选 **"/ (root)"**
4. 点击 **"Save"**
5. 等待 1-2 分钟

**访问地址：** https://MaxLinkerAlpha.github.io/LTRL_reader

---

### 4. 配置评论功能（Utterances）

1. 访问 https://github.com/apps/utterances
2. 点击 "Install"
3. 选择仓库 **MaxLinkerAlpha/LTRL_reader**
4. 确保已开启 Issues 功能（Settings → General → Issues ✓）

---

## 修改内容指南

### 修改章节内容

1. 访问 https://github.com/MaxLinkerAlpha/LTRL_reader/tree/main/data/chapters
2. 点击要修改的 `.md` 文件（如 chapter-1.md）
3. 点击右上角的 ✏️ 编辑按钮
4. 修改 Markdown 内容
5. 点击页面底部的 "Commit changes"
6. 等待 1 分钟后刷新网页

### Markdown 格式示例

```markdown
---
id: chapter-1
number: 1
title: Chapter I - 名词概述
translators: [Lanx, Cyan]
version: "1.0"
status: incomplete
---

## Section 1. 标题

### Latin
Rōma in Italiā est.
[forvo:roma] [forvo:italia]

### Translation:Lanx
罗马在意大利。

### Translation:Cyan
罗马位于意大利。

### Note
这里是伴侣注释。
```

### 添加新章节

1. 在 `data/chapters/` 下创建新文件（如 chapter-6.md）
2. 按格式填写内容
3. 编辑 `data/config.json`，在 chapters 数组中添加：

```json
{
  "id": "chapter-6",
  "number": 6,
  "title": "Chapter VI - 新章节",
  "has_companion": false,
  "available": true
}
```

### 添加术语

编辑 `data/terminology.json`：

```json
{
  "nominative": {
    "term": "Nominative",
    "translation": "主格",
    "explanation": "表示句子主语的格",
    "abbreviation": "Nom."
  }
}
```

---

## 常见问题排查

### 网页显示空白

1. 按 **F12** 打开浏览器开发者工具
2. 切换到 **Console** 标签
3. 查看红色错误信息

常见原因：
- 文件未上传完整
- 文件名大小写不匹配（Linux 服务器区分大小写）
- JSON 格式错误

### 评论功能不工作

1. 确保已安装 Utterances: https://github.com/apps/utterances
2. 确保仓库是 Public
3. 确保已开启 Issues 功能

### 网页地址

- 仓库：https://github.com/MaxLinkerAlpha/LTRL_reader
- 网页：https://MaxLinkerAlpha.github.io/LTRL_reader

---

## 本地预览（开发测试）

如需本地测试，启动本地服务器：

```bash
# Python 3
python -m http.server 8000

# 或使用 Node.js
npx http-server -p 8000
```

访问：http://localhost:8000

---

## 鸣谢

**LTRL翻译小组** - 感谢所有译者的辛勤工作和专业贡献。

- 译者：Lanx、簪花落梅、Yancey、tuche est、Mecius
- 特别感谢所有参与审校、润色的贡献者

---

**MaxLinkerAlpha 🏛️ LTRL Reader**
