"""
论文下载器
支持从 arXiv 等平台下载论文 PDF 并提取文本

工作流程：
- 属于"准备阶段"，负责下载和提取论文
- 不进行论文分析，分析由会话 LLM 完成

使用示例：
    >>> from scripts import PaperDownloader
    >>> downloader = PaperDownloader()
    >>>
    >>> # 下载论文并提取元数据
    >>> pdf_path, metadata = downloader.fetch_from_arxiv('2506.13131', download_pdf=True)
    >>>
    >>> # 提取论文全文
    >>> paper_text = downloader.extract_text_from_pdf(pdf_path)
    >>>
    >>> print(f"论文标题：{metadata['title']}")
    >>> print(f"论文长度：{len(paper_text)} 字符")
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import arxiv
except ImportError:
    arxiv = None

try:
    import requests
except ImportError:
    requests = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)


class PaperDownloader:
    """
    从 arXiv 等平台下载论文

    核心功能：
    - fetch_from_arxiv(): 从 arXiv 获取论文元数据和 PDF
    - download_from_url(): 从通用 URL 下载 PDF
    - extract_text_from_pdf(): 从 PDF 提取文本
    """

    def __init__(self, cache_dir: str = "/tmp/paper_cache", retry_times: int = 3):
        """
        初始化下载器

        Args:
            cache_dir: 论文缓存目录
            retry_times: 下载失败重试次数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.retry_times = retry_times

        # 检查依赖
        if arxiv is None:
            logger.warning("arxiv 库未安装，arXiv 下载功能不可用")
        if fitz is None and pdfplumber is None:
            logger.warning("PDF 解析库未安装，请安装 PyMuPDF 或 pdfplumber")

    def fetch_from_arxiv(self, arxiv_id: str, download_pdf: bool = False) -> Tuple[Optional[str], dict]:
        """
        从 arXiv 获取论文信息

        Args:
            arxiv_id: arXiv 编号 (如：2401.xxxxx)
            download_pdf: 是否下载 PDF（默认 False，仅获取元数据）

        Returns:
            (pdf_path, metadata): PDF 文件路径（如果下载）和元数据
        """
        if arxiv is None:
            raise ImportError("请安装 arxiv 库：pip install arxiv")

        # 规范化 arXiv ID
        arxiv_id = arxiv_id.replace("arXiv:", "").strip()

        logger.info(f"正在从 arXiv 获取：{arxiv_id}")

        # 重试机制
        max_retries = self.retry_times
        retry_delay = 2  # 初始延迟 2 秒

        for attempt in range(max_retries):
            try:
                # 获取论文元数据（无需下载）
                search = arxiv.Search(id_list=[arxiv_id])
                paper = next(search.results())

                # 提取元数据
                metadata = {
                    'title': paper.title,
                    'authors': [author.name for author in paper.authors],
                    'published': paper.published.strftime("%Y-%m-%d") if paper.published else None,
                    'arxiv_id': arxiv_id,
                    'url': paper.entry_id,
                    'summary': paper.summary,
                    'pdf_url': paper.pdf_url,
                    'categories': paper.categories if hasattr(paper, 'categories') else []
                }

                pdf_path = None

                # 如果需要下载 PDF
                if download_pdf:
                    # 创建一个子目录来存放 PDF
                    pdf_dir = self.cache_dir / arxiv_id
                    pdf_dir.mkdir(parents=True, exist_ok=True)

                    # 检查是否已经下载（检查目录中是否存在.pdf 文件）
                    existing_pdfs = list(pdf_dir.glob("*.pdf"))
                    if existing_pdfs:
                        pdf_path = str(existing_pdfs[0])
                        logger.info(f"PDF 已存在，跳过下载：{pdf_path}")
                        return pdf_path, metadata

                    # 下载 PDF 到该目录
                    logger.info(f"正在下载 PDF 到：{pdf_dir} (尝试 {attempt + 1}/{max_retries})")
                    paper.download_pdf(str(pdf_dir))

                    # 找到下载的 PDF 文件
                    pdf_files = list(pdf_dir.glob("*.pdf"))
                    if pdf_files:
                        pdf_path = str(pdf_files[0])
                        logger.info(f"下载成功：{pdf_path}")
                        return pdf_path, metadata
                    else:
                        # 如果找不到文件，尝试使用预期的文件名
                        expected_path = pdf_dir / f"{arxiv_id}.pdf"
                        if expected_path.exists():
                            pdf_path = str(expected_path)
                            return pdf_path, metadata
                        else:
                            raise FileNotFoundError(f"无法找到下载的 PDF 文件")
                else:
                    # 不下载 PDF，直接返回元数据
                    return pdf_path, metadata

            except Exception as e:
                logger.warning(f"获取论文失败 (尝试 {attempt + 1}/{max_retries}): {e}")

                # 如果是最后一次尝试，抛出异常
                if attempt == max_retries - 1:
                    logger.error(f"获取论文失败，已达到最大重试次数：{e}")
                    raise Exception(f"获取论文失败（已重试 {max_retries} 次）: {e}")

                # 否则等待后重试
                wait_time = retry_delay * (2 ** attempt)  # 指数退避
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        # 不应该到达这里
        raise Exception("获取论文失败")

    def download_from_url(self, url: str) -> Tuple[str, dict]:
        """
        从通用 URL 下载论文

        Args:
            url: 论文 URL

        Returns:
            (pdf_path, metadata): PDF 文件路径和元数据
        """
        if requests is None:
            raise ImportError("请安装 requests 库：pip install requests")

        logger.info(f"正在从 URL 下载：{url}")

        # 检查是否是 arXiv URL
        arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', url)
        if arxiv_match:
            return self.fetch_from_arxiv(arxiv_match.group(1), download_pdf=True)

        # 通用下载
        filename = url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        pdf_path = self.cache_dir / filename

        # 检查缓存
        if pdf_path.exists():
            logger.info(f"使用缓存文件：{pdf_path}")
            return str(pdf_path), {'url': url}

        # 下载
        for attempt in range(self.retry_times):
            try:
                response = requests.get(url, timeout=30, stream=True)
                response.raise_for_status()

                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"下载成功：{pdf_path}")
                return str(pdf_path), {'url': url}

            except Exception as e:
                logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        从 PDF 提取文本内容

        Args:
            pdf_path: PDF 文件路径

        Returns:
            提取的文本内容
        """
        logger.info(f"正在解析 PDF: {pdf_path}")

        # 优先使用 PyMuPDF
        if fitz is not None:
            return self._extract_with_pymupdf(pdf_path)
        # 备选使用 pdfplumber
        elif pdfplumber is not None:
            return self._extract_with_pdfplumber(pdf_path)
        else:
            raise ImportError("请安装 PyMuPDF 或 pdfplumber: pip install pymupdf pdfplumber")

    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """使用 PyMuPDF 提取文本"""
        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(text)

        doc.close()
        return '\n\n'.join(text_parts)

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """使用 pdfplumber 提取文本"""
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return '\n\n'.join(text_parts)

    def clear_cache(self):
        """清空缓存目录"""
        for file in self.cache_dir.glob('*'):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                import shutil
                shutil.rmtree(file)
        logger.info(f"已清空缓存：{self.cache_dir}")
