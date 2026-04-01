"""
Paper-to-MD Skill
下载论文、准备模板，由 LLM 分析后保存到本地 Markdown 文件

工作流程：
1. 准备阶段（本 skill）：下载 PDF、提取全文、准备模板
2. 分析阶段（会话 LLM）：根据模板深度分析论文
3. 写入阶段（本 skill）：将 LLM 分析结果保存到本地文件
"""

from .paper_downloader import PaperDownloader
from .paper_parser import PaperParser
from .converter import PaperToMd
from .local_storage import LocalStorage
from .knowledge_organizer import KnowledgeOrganizer
from .llm_client import chat_completion, check_ollama_available, list_ollama_models, DEFAULT_MODEL, DEFAULT_API_BASE

__version__ = "1.0.0"
__all__ = [
    "PaperDownloader",
    "PaperParser",
    "PaperToMd",
    "LocalStorage",
    "KnowledgeOrganizer",
    "chat_completion",
    "check_ollama_available",
    "list_ollama_models",
    "DEFAULT_MODEL",
    "DEFAULT_API_BASE",
]
