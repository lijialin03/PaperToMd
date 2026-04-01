"""
论文整理器
提取标签和相关推荐，由 LLM 分析后生成整理报告

从 analysis 目录读取论文，整理结果保存到 summary/
"""

import os
import logging
import re
import yaml
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeOrganizer:
    """论文整理器 - 提取数据，由 LLM 分析"""

    def __init__(self, config_path: str = None, storage_dir: str = None):
        """
        初始化整理器

        Args:
            config_path: 配置文件路径
            storage_dir: 本地存储目录（可选）
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

        self.config = self._load_config(config_path)

        # 导入 LocalStorage
        from .local_storage import LocalStorage
        self.storage = LocalStorage(storage_dir, self.config)
        logger.info(f"KnowledgeOrganizer 初始化完成，存储目录：{self.storage.base_dir}")

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def prepare_organize(self) -> dict:
        """
        准备整理：提取标签和相关推荐数据

        Returns:
            {
                'success': True,
                'docs': [...],           # 文档列表
                'tags': {...},           # 标签字典
                'recommendations': [...], # 推荐列表
                'prompt': '...'          # 分析提示词
            }
        """
        return self._prepare_organize_local()

    def _prepare_organize_local(self) -> dict:
        """本地模式：从 analysis 目录读取论文"""
        logger.info("准备整理（本地模式）")

        try:
            # 获取所有分析文件
            analysis_files = self.storage.get_analysis_files()

            if not analysis_files:
                return {
                    'success': True,
                    'docs': [],
                    'tags': {},
                    'recommendations': [],
                    'prompt': '没有找到分析文件。'
                }

            # 提取标签和推荐
            all_tags = {}
            all_recommendations = []
            docs = []

            for file_info in analysis_files:
                filepath = file_info['filepath']
                arxiv_id = file_info['arxiv_id']
                title = file_info['title']

                docs.append({
                    'doc_id': arxiv_id,
                    'title': title,
                    'filepath': filepath
                })

                # 读取文件内容
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取标签
                tags = self._extract_tags(content)
                for tag in tags:
                    if tag not in all_tags:
                        all_tags[tag] = []
                    all_tags[tag].append({
                        'doc_id': arxiv_id,
                        'doc_name': title
                    })

                # 提取相关推荐
                recs = self._extract_recommendations(content)
                for rec in recs:
                    rec['source_doc_id'] = arxiv_id
                    rec['source_doc_name'] = title
                all_recommendations.extend(recs)

            # 生成分析提示词
            prompt = self._build_prompt(docs, all_tags, all_recommendations)

            logger.info(f"提取完成：{len(docs)} 文档，{len(all_tags)} 标签，{len(all_recommendations)} 推荐")

            return {
                'success': True,
                'docs': docs,
                'tags': all_tags,
                'recommendations': all_recommendations,
                'prompt': prompt
            }

        except Exception as e:
            logger.error(f"准备整理失败：{e}")
            return {'success': False, 'error': str(e)}

    def _extract_tags(self, content: str) -> List[str]:
        """从内容中提取标签"""
        tags = []
        in_section = False

        for line in content.split('\n'):
            if '🏷️' in line or line.strip() in ['标签', 'Tags', '关键词', 'Keywords']:
                in_section = True
                continue
            if in_section:
                # 如果是 Markdown 标题（### 格式）且不是标签行，则退出
                # 标签行可能以#开头（如 #标签名），所以需要区分
                if re.match(r'^#{1,6}\s+\w', line) and '🏷️' not in line:
                    break
                # 提取 #标签 格式
                matches = re.findall(r'#([\w\u4e00-\u9fff]+)', line)
                tags.extend(matches)

        return list(set(tags))

    def _extract_recommendations(self, content: str) -> List[dict]:
        """从内容中提取相关推荐"""
        recs = []
        in_section = False

        for line in content.split('\n'):
            if '📚相关推荐' in line or '相关推荐' in line:
                in_section = True
                continue
            if in_section:
                if line.startswith('#') and '📚' not in line:
                    break
                # 提取 **标题**
                match = re.search(r'\*\*(.+?)\*\*', line)
                if match:
                    title = match.group(1).strip()
                    if len(title) > 5 and 'arXiv' not in title:
                        recs.append({'title': title})

        return recs

    def _build_prompt(self, docs: List, tags: Dict, recommendations: List[dict]) -> str:
        """构建分析提示词"""
        lines = ["请根据以下数据生成一份整理报告。", ""]

        # 文档列表
        lines.append("## 文档列表")
        for d in docs:
            doc_title = d.get('title', '未知')
            lines.append(f"- {doc_title}")
        lines.append("")

        # 标签
        lines.append("## 标签统计")
        sorted_tags = sorted(tags.items(), key=lambda x: len(x[1]), reverse=True)
        for tag, doc_list in sorted_tags:
            doc_names = [d['doc_name'] for d in doc_list]
            lines.append(f"- **{tag}**: {len(doc_list)} 篇 ({', '.join(doc_names)})")
        lines.append("")

        # 相关推荐
        if recommendations:
            lines.append("## 相关推荐")
            seen = set()
            for rec in recommendations:
                title = rec.get('title', '')
                if title and title not in seen:
                    seen.add(title)
                    source = rec.get('source_doc_name', '未知')
                    lines.append(f"- {title} (来自：{source})")
            lines.append("")

        lines.append("---")
        lines.append("请生成一份简洁的整理报告，包含：")
        lines.append("1. 研究主题总结")
        lines.append("2. 标签分类（按主题归类）")
        lines.append("3. 值得关注的推荐论文（如果有）")

        return '\n'.join(lines)

    def write_organized_content(self, content: str, title: str = None) -> dict:
        """
        将整理报告写入存储

        Args:
            content: LLM 生成的整理报告
            title: 文档标题

        Returns:
            写入结果
        """
        return self._write_organized_content_local(content, title)

    def _write_organized_content_local(self, content: str, title: str = None) -> dict:
        """本地模式：保存到 summary 目录"""
        try:
            filepath = self.storage.save_summary(content, title)
            return {
                'success': True,
                'filepath': filepath
            }
        except Exception as e:
            logger.error(f"保存整理结果失败：{e}")
            return {
                'success': False,
                'error': str(e)
            }
