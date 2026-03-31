# Paper-to-MD

> 基于 OpenClaw 的 skill。
> 同时提供了脱离 OpenClaw 的命独立运行命令。

<div align="left">

[![OpenClaw](https://img.shields.io/badge/OpenClaw-Agent-blue)](https://github.com/openclaw/openclaw)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## 核心功能

**将 arXiv 等平台的论文下载、提取全文，由 LLM 深度分析后保存到本地 Markdown 文件**

## 核心特性

- 论文下载：支持从 arXiv 下载 PDF 并提取全文
- 模板支持：提供"三遍阅读法"等专业分析模板
- LLM 分析：由会话 LLM 根据模板进行深度分析
- 本地存储：将分析结果保存为 Markdown 文件
- 论文整理：自动提取标签和推荐，生成整理报告
- 独立运行：支持命令行独立使用

## 快速开始

### 1. 安装依赖

```bash
pip install arxiv pymupdf pdfplumber pyyaml litellm
```

### 2. 配置 LLM

**使用 Ollama（免费，推荐）**

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama run llama3.1
```

**使用其他 Provider**

litellm 会自动从环境变量读取 API Key：

```bash
# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."
python analyze.py --url "..." --model anthropic/claude-sonnet-4-6-20251101

# OpenAI GPT
export OPENAI_API_KEY="sk-..."
python analyze.py --url "..." --model openai/gpt-4.1

# OpenRouter（有免费模型）
export OPENROUTER_API_KEY="..."
python analyze.py --url "..." --model openrouter/google/gemma-7b-it:free
```

或在 `config.yaml` 中配置：

```yaml
llm:
  model: "openai/gpt-4.1"
  api_key: "sk-..."  # 或使用环境变量
```

### 3. 使用示例

#### 在 OpenClaw 中使用

```python
from scripts import PaperToMd

# 初始化
helper = PaperToMd(storage_dir='~/paperstorge')

# 准备论文
pdf_path, metadata = helper.prepare_paper('https://arxiv.org/abs/2506.13131')
paper_text = helper.extract_text(pdf_path)
template = helper.get_template()

# LLM 分析（由会话 LLM 完成）
# 读取 paper_text 和 template，生成 analysis_content

# 保存到本地
result = helper.write_analysis(analysis_content, metadata)
```

#### 命令行独立运行

```bash
# 分析单篇论文
python analyze.py --url "https://arxiv.org/abs/2506.13131" --stream

# 使用快速笔记模板
python analyze.py --url "https://arxiv.org/abs/2506.13131" --template quick_note

# 使用其他模型
python analyze.py --url "https://arxiv.org/abs/2506.13131" --model ollama/qwen2.5

# 处理未处理列表中的论文
python analyze.py --pending

# 从文件批量处理
python analyze.py --input-file papers.txt

# 整理已分析的论文
python analyze.py --organize
```

**论文列表管理：**

在 `paperstorge/unprocessed.md` 中添加待处理论文：

```markdown
# 0331
https://arxiv.org/abs/2506.13131
https://arxiv.org/abs/2408.11869
```

运行 `python analyze.py --pending` 处理，完成后会自动：
- 从 `unprocessed.md` 移除已处理的论文
- 添加到 `processed.md`

## 目录结构

```
paperstorge/
├── unprocessed.md    # 未处理论文 URL 列表
├── processed.md      # 已处理论文 URL 列表
├── analysis/         # 论文分析结果
│   └── 2401.12345.md
└── summary/          # 论文整理结果
    └── 论文整理 -20260331-120000.md
```

## 可用模板

| 模板 | 说明 | 适用场景 |
|------|------|---------|
| `default` | 三遍阅读法 | 深度解析论文 |
| `quick_note` | 快速笔记 | 快速提取要点 |
| `literature_review` | 文献综述 | 结构化综述 |

## 配置

配置文件 `config.yaml`：

```yaml
# 存储配置
storage:
  base_dir: "~/paperstorge"

# LLM 配置
llm:
  model: "ollama/llama3.1"
  api_base: "http://localhost:11434"
  max_tokens: 8192
  timeout: 120
```

## 文档说明

- **README.md** - 用户文档，介绍使用方法和配置
- **SKILL.md** - OpenClaw Skill 开发者文档，描述 Skill 接口和工作流程
