"""
Paper-to-MD 主入口
辅助 LLM 分析论文并保存到本地 Markdown 文件

工作流程：
1. 准备阶段：下载 PDF、提取全文、准备模板
2. 分析阶段（会话 LLM）：根据模板深度分析论文
3. 写入阶段：将 LLM 分析结果保存到本地文件
"""

import os
import logging
import re
from typing import Optional, Dict
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from .paper_downloader import PaperDownloader
from .paper_parser import PaperParser
from .local_storage import LocalStorage

logger = logging.getLogger(__name__)


class PaperToMd:
    """
    论文分析辅助工具

    不自动生成分析内容，而是提供辅助功能：
    - 下载论文 PDF
    - 提取论文全文
    - 准备分析模板
    - 写入分析结果到本地文件

    使用示例（本地模式）：
        # 步骤 1：准备论文
        helper = PaperToMd()
        pdf_path, metadata = helper.prepare_paper('https://arxiv.org/abs/2506.13131')
        paper_text = helper.extract_text(pdf_path)
        template = helper.get_template()

        # 步骤 2：LLM 分析（由会话 LLM 完成）
        # 读取 paper_text 和 template，生成 analysis_content

        # 步骤 3：保存到本地文件
        result = helper.write_analysis(
            analysis_content=analysis_content,
            metadata=metadata
        )
    """

    def __init__(self,
                 template: str = None,
                 config_path: Optional[str] = None,
                 storage_dir: Optional[str] = None):
        """
        初始化辅助工具

        Args:
            template: 模板名称（default, quick_note, literature_review）
            config_path: 配置文件路径（可选，默认使用 skill 目录下的 config.yaml）
            storage_dir: 本地存储目录（可选，优先于配置中的设置）
        """
        # 加载配置文件
        # 优先级：1. 用户传入的 config_path 2. skill 目录下的 config.yaml 3. 用户主目录的 config.yaml
        if config_path:
            self.config_path = config_path
        else:
            # 尝试使用 skill 目录下的配置文件
            skill_config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
            if os.path.exists(skill_config_path):
                self.config_path = skill_config_path
            else:
                self.config_path = os.path.expanduser('~/.openclaw/skills/paper-to-md/config.yaml')

        self.config = self._load_config()

        # 使用配置或参数
        self.template = template or self.config.get('parsing', {}).get('default_template', 'default')

        # 初始化组件
        paper_config = self.config.get('paper', {})
        self.downloader = PaperDownloader(
            cache_dir=paper_config.get('cache_dir', '/tmp/paper_cache'),
            retry_times=paper_config.get('retry_times', 3)
        )

        self.parser = PaperParser(template_name=self.template)

        # 初始化本地存储（传入配置，从 config.storage.base_dir 读取路径）
        self.storage = LocalStorage(storage_dir, self.config)
        logger.info(f"PaperToMd 初始化完成，存储目录：{self.storage.base_dir}")

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件不存在：{self.config_path}")
            return self._get_default_config()

        if yaml is None:
            logger.warning("PyYAML 未安装，使用默认配置")
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"成功加载配置文件：{self.config_path}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败：{e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            'paper': {
                'download_pdf': True,
                'cache_dir': '/tmp/paper_cache',
                'retry_times': 3
            },
            'parsing': {
                'default_template': 'default'
            }
        }

    # ========== 准备阶段 API ==========

    def prepare_paper(self, paper_url: str, download_pdf: bool = True) -> tuple:
        """
        准备论文：下载（可选）并获取元数据

        Args:
            paper_url: 论文 URL（arXiv 或 PDF URL）
            download_pdf: 是否下载 PDF（默认 True，推荐下载以获取完整内容）

        Returns:
            (pdf_path, metadata): PDF 路径和元数据

        Raises:
            Exception: 当 download_pdf=True 但 PDF 下载失败时抛出异常

        示例：
            >>> helper = PaperToMd()
            >>> pdf_path, metadata = helper.prepare_paper('https://arxiv.org/abs/2506.13131')
            >>> print(f"论文标题：{metadata['title']}")
            >>> print(f"PDF 路径：{pdf_path}")
        """
        logger.info(f"准备论文：{paper_url}, 下载 PDF: {download_pdf}")

        # 检查是否是 arXiv URL
        if 'arxiv.org' in paper_url:
            match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', paper_url)
            if match:
                arxiv_id = match.group(1)
                pdf_path, metadata = self.downloader.fetch_from_arxiv(arxiv_id, download_pdf)

                # 如果要求下载 PDF 但失败了，抛出异常
                if download_pdf and not pdf_path:
                    raise Exception(f"PDF 下载失败，无法处理论文：{paper_url}")

                return pdf_path, metadata

        # 通用 URL 处理
        if download_pdf:
            pdf_path, metadata = self.downloader.download_from_url(paper_url)
            if not pdf_path:
                raise Exception(f"PDF 下载失败，无法处理论文：{paper_url}")
            return pdf_path, metadata
        else:
            return None, {'url': paper_url}

    def extract_text(self, pdf_path: Optional[str]) -> str:
        """
        从 PDF 提取文本

        Args:
            pdf_path: PDF 文件路径

        Returns:
            论文文本内容

        示例：
            >>> text = helper.extract_text('/tmp/paper.pdf')
            >>> print(f"论文长度：{len(text)} 字符")
        """
        if pdf_path and os.path.exists(pdf_path):
            text = self.downloader.extract_text_from_pdf(pdf_path)
            logger.info(f"提取文本完成，长度：{len(text)} 字符")
            return text
        else:
            logger.warning(f"PDF 路径无效：{pdf_path}")
            return ""

    def get_template(self) -> str:
        """
        获取分析模板内容

        Returns:
            模板的完整内容（包含 role、output_spec、template 等）

        示例：
            >>> template = helper.get_template()
            >>> print(template)
        """
        return self.parser.get_template_content()

    def get_template_structure(self) -> dict:
        """
        获取模板结构（用于程序化访问）

        Returns:
            模板的结构化数据

        示例：
            >>> structure = helper.get_template_structure()
            >>> print(structure['name'])  # "三遍阅读法"
        """
        return self.parser.current_template

    # ========== 写入阶段 API ==========

    def write_analysis(self,
                      analysis_content: str,
                      metadata: dict) -> dict:
        """
        将 LLM 分析结果保存到本地文件

        Args:
            analysis_content: LLM 生成的分析内容
            metadata: 论文元数据

        Returns:
            操作结果，包含 filepath, arxiv_id 等

        示例：
            >>> result = helper.write_analysis(
            ...     analysis_content="# 论文分析\\n\\n...",
            ...     metadata={'title': '...', 'arxiv_id': '2401.xxxxx'}
            ... )
            >>> if result['success']:
            ...     print(f"文件已保存：{result['filepath']}")
        """
        return self._write_local(analysis_content, metadata)

    def _write_local(self, analysis_content: str, metadata: dict) -> dict:
        """写入本地文件"""
        logger.info("写入分析结果到本地文件")

        arxiv_id = metadata.get('arxiv_id')
        title = metadata.get('title', 'Unknown Paper')

        if not arxiv_id:
            # 尝试从 URL 提取
            url = metadata.get('url', '')
            match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', url)
            if match:
                arxiv_id = match.group(1)

        if not arxiv_id:
            return {
                'success': False,
                'error': '无法获取 arXiv ID，请在 metadata 中提供 arxiv_id 或 url'
            }

        # 保存到本地
        filepath = self.storage.save_analysis(arxiv_id, title, analysis_content, metadata)

        # 从未处理列表移除，添加到已处理列表
        url = metadata.get('url', f'https://arxiv.org/abs/{arxiv_id}')
        self.storage.mark_as_processed(url)

        return {
            'success': True,
            'filepath': filepath,
            'arxiv_id': arxiv_id
        }

    # ========== 本地模式专用 API ==========

    def get_pending_papers(self) -> list:
        """
        获取未处理论文 URL 列表

        Returns:
            list: 论文 URL 列表

        示例：
            >>> urls = helper.get_pending_papers()
            >>> print(f"找到 {len(urls)} 篇待处理论文")
        """
        return self.storage.get_unprocessed_urls()


    def add_pending_paper(self, paper_url: str):
        """
        添加新论文到未处理列表

        Args:
            paper_url: 论文 URL

        示例：
            >>> helper.add_pending_paper('https://arxiv.org/abs/2506.13131')
        """
        self.storage.add_unprocessed_url(paper_url)
        logger.info(f"添加论文到未处理列表：{paper_url}")

    def get_analysis_files(self) -> list:
        """
        获取所有已保存的分析文件

        Returns:
            分析文件信息列表
        """
        return self.storage.get_analysis_files()

    def get_analysis_content(self, arxiv_id: str) -> Optional[str]:
        """
        获取指定 arXiv ID 的分析内容

        Args:
            arxiv_id: arXiv ID

        Returns:
            分析内容，如果不存在则返回 None
        """
        return self.storage.get_analysis_content(arxiv_id)
