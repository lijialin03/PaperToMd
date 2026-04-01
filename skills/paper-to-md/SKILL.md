---
name: paper-to-md
description: Download arXiv papers, extract text, and save LLM-analyzed content to local Markdown files. Triggers when asked to download, analyze, or summarize arXiv papers.
metadata:
  {
    "openclaw":
      {
        "emoji": "📄",
        "os": ["darwin", "linux"],
        "requires": { "pip": ["arxiv", "pymupdf", "pdfplumber", "pyyaml", "litellm"] },
        "install":
          [
            {
              "id": "pip-deps",
              "kind": "pip",
              "packages": ["arxiv", "pymupdf", "pdfplumber", "pyyaml", "litellm"],
              "label": "Install Paper-to-MD dependencies (pip)",
            },
          ],
      },
  }
---

# Paper-to-MD

## Overview

Download arXiv papers, extract full text, and save LLM-analyzed content to local Markdown files. Supports batch processing, paper list management, and knowledge organization.

## Quick start

1. Install dependencies: `pip install arxiv pymupdf pdfplumber pyyaml litellm`
2. Configure LLM (Ollama recommended, free):
   ```bash
   ollama run llama3.1
   ```
3. Run analysis:
   ```bash
   python {baseDir}/analyze.py --url "https://arxiv.org/abs/2506.13131"
   ```

## Commands

### Analyze single paper

```bash
python {baseDir}/analyze.py --url "https://arxiv.org/abs/2506.13131" --stream
```

### Process pending papers

Add papers to `paperstorge/unprocessed.md`:
```markdown
# 0401
https://arxiv.org/abs/2506.13131
https://arxiv.org/abs/2408.11869
```

Then run:
```bash
python {baseDir}/analyze.py --pending
python {baseDir}/analyze.py --pending --delay 30  # Custom delay between papers
```

### Batch process from file

```bash
python {baseDir}/analyze.py --input-file papers.txt
```

### Organize analyzed papers

```bash
python {baseDir}/analyze.py --organize
```

## Configuration

### LLM Configuration

Use Ollama (free, local):
```bash
export OLLAMA_HOST="http://localhost:11434"
python {baseDir}/analyze.py --url "..." --model ollama/llama3.1
```

Use Claude API:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python {baseDir}/analyze.py --url "..." --model anthropic/claude-sonnet-4-6 --delay 60
```

Or use `config.yaml`:
```yaml
llm:
  model: "ollama/llama3.1"
  api_base: "http://localhost:11434"
  max_tokens: 8192
  timeout: 120
```

### Storage Configuration

```yaml
storage:
  base_dir: "~/paperstorge"
```

## Output Structure

```
paperstorge/
├── unprocessed.md    # Pending papers
├── processed.md      # Processed papers
├── analysis/         # Paper analysis (by arXiv ID)
│   └── 2506.13131.md
└── summary/          # Organization reports (by date)
    └── 2026-04-01.md
```

## API

### PaperToMd Class

```python
from scripts import PaperToMd

helper = PaperToMd(storage_dir='~/paperstorge')
pdf_path, metadata = helper.prepare_paper('https://arxiv.org/abs/2506.13131')
text = helper.extract_text(pdf_path)
template = helper.get_template()
# Pass text + template to LLM, then:
helper.write_analysis(analysis_content, metadata)
```

### KnowledgeOrganizer Class

```python
from scripts import KnowledgeOrganizer

organizer = KnowledgeOrganizer()
result = organizer.prepare_organize()  # Extract tags & recommendations
organizer.write_organized_content(report, title="论文整理报告")
```

## Rate Limit Handling

- Auto-retry: Up to 3 retries with exponential backoff (5s → 10s → 20s)
- Paper delay: Use `--delay` to set seconds between papers (default: 10)
- For API models (Claude, GPT-4), use longer delays: `--delay 60`

## Templates

| Template | Description |
|----------|-------------|
| `default` | Three-pass reading method |
| `quick_note` | Quick notes template |
| `literature_review` | Literature review template |

## References

- `README.md` - User documentation
- `scripts/` - Implementation modules
