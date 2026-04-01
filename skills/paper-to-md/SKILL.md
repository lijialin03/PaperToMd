---
name: paper-to-md
description: 解析 arXiv 论文并保存到本地 Markdown 文件
---

# Paper-to-MD Skill

## 描述

**名称**：paper-to-md
**版本**：1.0.0
**类型**：论文分析辅助工具

核心功能：
- 从 arXiv 下载论文 PDF 并提取全文
- 提供专业的论文分析模板
- 将 LLM 分析结果保存为 Markdown 文件
- 支持论文列表管理和整理

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                      工作流程                                │
├─────────────────────────────────────────────────────────────┤
│  1. 准备阶段（PaperToMd）                                   │
│     ├─ 下载论文 PDF（带重试机制）                            │
│     ├─ 提取论文全文                                          │
│     └─ 准备分析模板                                          │
│                                                              │
│  2. 分析阶段（会话 LLM）⭐                                   │
│     ├─ 读取论文全文和模板                                    │
│     └─ 深度分析生成结构化内容                                │
│                                                              │
│  3. 写入阶段（PaperToMd）                                   │
│     ├─ 保存分析结果为 Markdown                               │
│     └─ 更新论文列表状态                                      │
└─────────────────────────────────────────────────────────────┘
```

**重要**：分析阶段必须由会话 LLM 完成，Skill 本身不生成分析内容。

## API

### PaperToMd 类

```python
from scripts import PaperToMd

helper = PaperToMd(
    template='default',      # 模板名称
    storage_dir=None,        # 存储目录
    config_path=None         # 配置文件路径
)
```

#### 核心方法

| 方法 | 说明 |
|------|------|
| `prepare_paper(url, download_pdf=True)` | 准备论文（下载 + 元数据） |
| `extract_text(pdf_path)` | 提取 PDF 文本 |
| `get_template()` | 获取分析模板 |
| `write_analysis(content, metadata)` | 写入分析结果 |
| `get_pending_papers()` | 获取未处理论文列表 |
| `add_pending_paper(url)` | 添加论文到未处理列表 |
| `get_analysis_files()` | 获取所有分析文件 |
| `get_analysis_content(arxiv_id)` | 获取指定论文的分析内容 |

### KnowledgeOrganizer 类

```python
from scripts import KnowledgeOrganizer

organizer = KnowledgeOrganizer()
result = organizer.prepare_organize()
```

#### 方法

| 方法 | 说明 |
|------|------|
| `prepare_organize()` | 提取标签和推荐数据 |
| `write_organized_content(content, title)` | 写入整理报告 |

## 文件结构

```
paper-to-md/
├── README.md              # 用户文档
├── SKILL.md               # Skill 开发者文档
├── config.yaml            # 配置文件
├── templates.yaml         # 模板定义
├── analyze.py             # 独立运行入口
└── scripts/
    ├── __init__.py
    ├── converter.py       # PaperToMd 主类
    ├── local_storage.py   # 本地存储
    ├── paper_downloader.py # 论文下载
    ├── paper_parser.py    # 模板解析
    ├── llm_client.py      # LLM 调用
    └── knowledge_organizer.py # 论文整理
```

## 依赖

- `arxiv` - 论文下载
- `pymupdf` 或 `pdfplumber` - PDF 文本提取
- `pyyaml` - 配置解析
- `litellm` - LLM 调用

```bash
pip install arxiv pymupdf pdfplumber pyyaml litellm
```
