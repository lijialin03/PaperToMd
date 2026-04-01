"""
本地 Markdown 文件存储模块
将论文分析结果保存到本地 Markdown 文件

目录结构：
paperstorge/
├── unprocessed.md    # 未处理论文 URL 列表
├── processed.md      # 已处理论文 URL 列表
├── analysis/         # 论文分析结果
└── summary/          # 整理结果
"""

import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalStorage:
    """本地 Markdown 文件存储管理器"""

    def __init__(self, base_dir: str = None, config: dict = None):
        """
        初始化本地存储

        Args:
            base_dir: 基础目录，优先使用此参数
            config: 配置字典，可从中读取 storage.base_dir
        """
        # 优先级：1. 传入的 base_dir 2. 配置中的 storage.base_dir 3. 环境变量 4. 默认值
        if base_dir is None:
            if config and 'storage' in config:
                base_dir = config['storage'].get('base_dir', '~/paperstorge')
            else:
                base_dir = os.environ.get('PAPER_STORAGE_DIR', '~/paperstorge')

        # 展开环境变量和 ~
        base_dir = os.path.expanduser(os.path.expandvars(base_dir))

        # 检查并使用现有的 paperstorge 目录
        if not os.path.exists(base_dir):
            # 尝试使用 openclaw 目录下的 paperstorge
            alt_base_dir = "/home/ssd2/openclaw/paperstorge"
            if os.path.exists(alt_base_dir):
                base_dir = alt_base_dir
                logger.info(f"使用现有目录：{base_dir}")
            else:
                logger.info(f"创建新目录：{base_dir}")
                os.makedirs(base_dir, exist_ok=True)

        self.base_dir = base_dir
        self.unprocessed_path = os.path.join(base_dir, "unprocessed.md")
        self.processed_path = os.path.join(base_dir, "processed.md")
        self.analysis_dir = os.path.join(base_dir, "analysis")
        self.summary_dir = os.path.join(base_dir, "summary")

        # 确保目录存在
        os.makedirs(self.analysis_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)

        # 初始化文件
        self._init_files()

        logger.info(f"LocalStorage 初始化完成：{base_dir}")

    def _init_files(self):
        """初始化 Markdown 文件（如果不存在）"""
        if not os.path.exists(self.unprocessed_path):
            with open(self.unprocessed_path, 'w', encoding='utf-8') as f:
                f.write("# 未处理论文列表\n\n")
            logger.info(f"创建未处理列表：{self.unprocessed_path}")

        if not os.path.exists(self.processed_path):
            with open(self.processed_path, 'w', encoding='utf-8') as f:
                f.write("# 已处理论文列表\n\n")
            logger.info(f"创建已处理列表：{self.processed_path}")

    def get_unprocessed_urls(self) -> List[str]:
        """
        获取未处理论文 URL 列表

        Returns:
            未处理论文 URL 列表
        """
        if not os.path.exists(self.unprocessed_path):
            return []

        with open(self.unprocessed_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取所有 arXiv URL
        pattern = r'https?://arxiv\.org/(?:abs|pdf)/[\d\.]+v?\d*'
        urls = re.findall(pattern, content)

        # 规范化 URL（统一为 abs 格式）
        normalized = []
        seen = set()
        for url in urls:
            # 将 pdf 格式转为 abs 格式
            if '/pdf/' in url:
                arxiv_id = url.split('/pdf/')[-1].replace('.pdf', '')
                url = f'https://arxiv.org/abs/{arxiv_id}'
            if url not in seen:
                seen.add(url)
                normalized.append(url)

        return normalized

    def get_processed_urls(self) -> List[str]:
        """
        获取已处理论文 URL 列表

        Returns:
            已处理论文 URL 列表
        """
        if not os.path.exists(self.processed_path):
            return []

        with open(self.processed_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'https?://arxiv\.org/(?:abs|pdf)/[\d\.]+v?\d*'
        urls = re.findall(pattern, content)

        normalized = []
        seen = set()
        for url in urls:
            if '/pdf/' in url:
                arxiv_id = url.split('/pdf/')[-1].replace('.pdf', '')
                url = f'https://arxiv.org/abs/{arxiv_id}'
            if url not in seen:
                seen.add(url)
                normalized.append(url)

        return normalized

    def add_unprocessed_url(self, url: str):
        """
        添加论文到未处理列表

        Args:
            url: 论文 URL
        """
        # 规范化 URL
        if '/pdf/' in url:
            arxiv_id = url.split('/pdf/')[-1].replace('.pdf', '')
            url = f'https://arxiv.org/abs/{arxiv_id}'

        # 检查是否已存在
        current_urls = self.get_unprocessed_urls() + self.get_processed_urls()
        if url in current_urls:
            logger.warning(f"论文已存在：{url}")
            return

        # 添加到今天的部分
        today = datetime.now().strftime('%m%d')
        self._add_url_to_file(self.unprocessed_path, url, today)
        logger.info(f"添加未处理论文：{url}")

    def _add_url_to_file(self, file_path: str, url: str, section: str):
        """添加 URL 到指定文件的 section 中"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# 论文列表\n\n"

        # 检查是否有今天的 section
        section_header = f"# {section}"
        if section_header in content:
            # 添加到现有 section
            lines = content.split('\n')
            new_lines = []
            added = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == section_header and not added:
                    new_lines.append(url)
                    added = True
            content = '\n'.join(new_lines)
        else:
            # 添加新 section
            content = content.rstrip() + f"\n\n# {section}\n{url}\n"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def mark_as_processed(self, url: str):
        """
        标记论文为已处理（从 unprocessed 移除，添加到 processed）

        Args:
            url: 论文 URL
        """
        # 提取 arXiv ID
        arxiv_id = self._extract_arxiv_id(url)
        if not arxiv_id:
            logger.error(f"无法从 URL 提取 arXiv ID: {url}")
            return

        # 规范化 URL 为 abs 格式
        normalized_url = f'https://arxiv.org/abs/{arxiv_id}'

        # 添加到 processed
        today = datetime.now().strftime('%m%d')
        self._add_url_to_file(self.processed_path, normalized_url, today)

        # 从 unprocessed 移除（通过 arXiv ID 匹配）
        self._remove_url_from_file(self.unprocessed_path, arxiv_id)
        logger.info(f"标记为已处理：{normalized_url}")

    def _extract_arxiv_id(self, url: str) -> str:
        """从 URL 中提取 arXiv ID"""
        match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', url)
        if match:
            return match.group(1)
        return None

    def _remove_url_from_file(self, file_path: str, arxiv_id: str):
        """从文件中移除 URL（通过 arXiv ID 匹配）"""
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 保留不包含该 arXiv ID 的行
        new_lines = []
        for line in lines:
            # 检查行中是否包含该 arXiv ID
            if arxiv_id not in line:
                new_lines.append(line)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    def save_analysis(self, arxiv_id: str, title: str, content: str,
                      metadata: dict = None) -> str:
        """
        保存论文分析结果

        Args:
            arxiv_id: arXiv ID（例如 2401.12345）
            title: 论文标题
            content: 分析内容（Markdown 格式）
            metadata: 论文元数据（可选）

        Returns:
            保存的文件路径
        """
        # 生成文件名
        filename = f"{arxiv_id}.md"
        filepath = os.path.join(self.analysis_dir, filename)

        # 构建完整内容
        full_content = self._build_analysis_content(arxiv_id, title, content, metadata)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)

        logger.info(f"保存分析结果：{filepath}")
        return filepath

    def _build_analysis_content(self, arxiv_id: str, title: str,
                                 content: str, metadata: dict = None) -> str:
        """构建分析文件内容"""
        lines = [
            f"# [{arxiv_id}] {title}",
            "",
            f"**arXiv ID**: {arxiv_id}",
            f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        if metadata:
            if 'authors' in metadata and metadata['authors']:
                lines.append(f"**作者**: {', '.join(metadata['authors'][:5])}")
            if 'published' in metadata:
                lines.append(f"**发表日期**: {metadata['published']}")
            if 'categories' in metadata and metadata['categories']:
                lines.append(f"**分类**: {', '.join(metadata['categories'][:5])}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(content)

        return '\n'.join(lines)

    def save_summary(self, content: str, title: str = None) -> str:
        """
        保存整理结果

        Args:
            content: 整理内容（Markdown 格式）
            title: 标题（可选，用于内容开头，不影响文件名）

        Returns:
            保存的文件路径
        """
        # 使用日期生成文件名，避免覆盖
        date_str = datetime.now().strftime('论文整理-%Y-%m-%d')
        filename = f"{date_str}.md"
        filepath = os.path.join(self.summary_dir, filename)

        # 构建完整内容（标题放在内容开头）
        lines = []
        if title:
            lines.append(f"# {title}")
            lines.append("")
        lines.append(content)
        full_content = '\n'.join(lines)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)

        logger.info(f"保存整理结果：{filepath}")
        return filepath

    def get_analysis_files(self) -> List[Dict]:
        """
        获取所有分析文件

        Returns:
            分析文件信息列表，每个包含：{'filepath': str, 'arxiv_id': str, 'title': str}
        """
        files = []
        if not os.path.exists(self.analysis_dir):
            return files

        for filename in os.listdir(self.analysis_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.analysis_dir, filename)
                arxiv_id = filename[:-3]  # 移除 .md
                title = self._extract_title(filepath)
                files.append({
                    'filepath': filepath,
                    'arxiv_id': arxiv_id,
                    'title': title
                })

        return files

    def _extract_title(self, filepath: str) -> str:
        """从分析文件中提取标题"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # 移除 # 和 arXiv ID
                if first_line.startswith('# '):
                    return first_line[2:].strip()
                return first_line
        except:
            return "未知标题"

    def get_analysis_content(self, arxiv_id: str) -> Optional[str]:
        """
        获取指定 arXiv ID 的分析内容

        Args:
            arxiv_id: arXiv ID

        Returns:
            分析内容，如果不存在则返回 None
        """
        filepath = os.path.join(self.analysis_dir, f"{arxiv_id}.md")
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def get_summary_files(self) -> List[Dict]:
        """
        获取所有整理文件

        Returns:
            整理文件信息列表
        """
        files = []
        if not os.path.exists(self.summary_dir):
            return files

        for filename in os.listdir(self.summary_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(self.summary_dir, filename)
                files.append({
                    'filepath': filepath,
                    'filename': filename,
                    'title': self._extract_title(filepath)
                })

        return sorted(files, key=lambda x: x['filename'], reverse=True)
