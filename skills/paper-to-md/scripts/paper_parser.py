"""
论文模板管理器
负责加载和提供分析模板

⚠️ 注意：此类不进行论文分析，只提供模板
真正的分析必须由会话 LLM 完成
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


class PaperParser:
    """
    论文模板管理器
    
    只负责加载和管理模板，不进行实际的论文分析。
    真正的论文深度分析必须由会话 LLM 完成。
    
    使用示例：
        >>> from scripts import PaperParser
        >>> parser = PaperParser(template_name='default')
        >>> 
        >>> # 获取模板内容
        >>> template = parser.get_template_content()
        >>> print(template)
        >>> 
        >>> # 获取模板信息
        >>> info = parser.get_template_info()
        >>> print(info['name'])  # "三遍阅读法"
    """
    
    def __init__(self, template_dir: str = None, template_name: str = "default"):
        """
        初始化模板管理器
        
        Args:
            template_dir: 模板目录路径
            template_name: 模板名称
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent
        
        self.template_dir = Path(template_dir)
        self.template_name = template_name
        
        # 加载模板配置
        self.templates_config = self._load_templates_config()
        self.current_template = self._get_template(template_name)
    
    def _load_templates_config(self) -> dict:
        """加载模板配置文件"""
        if yaml is None:
            logger.warning("PyYAML未安装，使用默认配置")
            return {}
        
        template_file = self.template_dir / "templates.yaml"
        
        if not template_file.exists():
            logger.warning(f"模板配置文件不存在: {template_file}")
            return {}
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"成功加载模板配置，包含 {len(config)} 个模板")
                return config
        except Exception as e:
            logger.error(f"加载模板配置失败: {e}")
            return {}
    
    def _get_template(self, template_name: str) -> dict:
        """获取指定模板"""
        if not self.templates_config:
            logger.warning("模板配置为空，使用硬编码默认模板")
            return self._get_fallback_template()
        
        if template_name not in self.templates_config:
            logger.warning(f"模板 '{template_name}' 不存在，使用默认模板")
            template_name = "default"
        
        template = self.templates_config.get(template_name, {})
        logger.info(f"使用模板: {template.get('name', template_name)}")
        
        return template
    
    def _get_fallback_template(self) -> dict:
        """获取备用模板（当YAML加载失败时）"""
        return {
            'name': '默认模板',
            'role': '你是一位研究助手，擅长解析学术论文。',
            'template': """## 论文基本信息
>列出论文信息标题、作者、提交时间、arXiv编号、领域等

## 摘要
{abstract}

## 核心内容
{content}

## 📚相关推荐
> Top3 推荐阅读的相关论文"""
        }
    
    def get_template_content(self) -> str:
        """
        获取完整的模板内容
        
        这个内容应该作为 LLM 的 prompt 的一部分。
        
        Returns:
            str: 完整的模板内容
        """
        if not self.current_template:
            return ""
        
        # 组合模板内容
        parts = []
        
        if self.current_template.get('role'):
            parts.append(f"【Role】\n{self.current_template['role']}\n")
        
        if self.current_template.get('output_spec'):
            parts.append(f"【Output Specification】\n{self.current_template['output_spec']}\n")
        
        if self.current_template.get('reference'):
            parts.append(f"【Reference】\n{self.current_template['reference']}\n")
        
        if self.current_template.get('rules'):
            rules = self.current_template['rules']
            rules_text = '\n'.join([f"{i+1}. {rule}" for i, rule in enumerate(rules)])
            parts.append(f"【Rules】\n{rules_text}\n")
        
        if self.current_template.get('template'):
            parts.append(f"【Template】\n{self.current_template['template']}\n")
        
        return '\n'.join(parts)
    
    def get_template_info(self) -> dict:
        """
        获取模板信息（名称、描述等）
        
        Returns:
            dict: 模板信息
        """
        return {
            'name': self.current_template.get('name', 'Unknown'),
            'description': self.current_template.get('description', ''),
            'template_name': self.template_name
        }
