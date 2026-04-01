#!/usr/bin/env python3
"""
Paper-to-MD 独立运行入口

在不使用 OpenClaw 的情况下，独立运行论文分析流程。

用法:
    # 分析单篇论文
    python analyze.py --url "https://arxiv.org/abs/2506.13131"

    # 使用快速笔记模板
    python analyze.py --url "https://arxiv.org/abs/2506.13131" --template quick_note

    # 使用其他模型
    python analyze.py --url "https://arxiv.org/abs/2506.13131" --model ollama/qwen2.5

    # 流式输出
    python analyze.py --url "https://arxiv.org/abs/2506.13131" --stream

    # 处理未处理列表中的论文
    python analyze.py --pending

    # 从文件批量处理
    python analyze.py --input-file papers.txt

    # 整理已分析的论文
    python analyze.py --organize
"""

import os
import sys
import time
import argparse
import logging
import json
from pathlib import Path
from typing import Optional, List

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scripts.converter import PaperToMd
from scripts.llm_client import chat_completion, DEFAULT_MODEL, DEFAULT_API_BASE
from scripts.knowledge_organizer import KnowledgeOrganizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_prompt(paper_text: str, template: str, metadata: dict) -> tuple:
    """
    构建 LLM 提示词

    Returns:
        (system_prompt, user_prompt): 系统和用户提示词
    """
    # 从模板提取系统角色和输出规范
    system_prompt = ""
    output_spec = ""

    # 解析模板（简单解析，提取 role 和 output_spec）
    lines = template.split('\n')
    in_role = False
    in_output_spec = False

    for line in lines:
        if line.strip().startswith('【Role】') or line.strip().startswith('[Role]'):
            in_role = True
            in_output_spec = False
            continue
        elif line.strip().startswith('【Output Specification】') or line.strip().startswith('[Output Specification]'):
            in_role = False
            in_output_spec = True
            continue
        elif line.strip().startswith('【') or line.strip().startswith('['):
            in_role = False
            in_output_spec = False

        if in_role:
            system_prompt += line + '\n'
        elif in_output_spec:
            output_spec += line + '\n'

    # 如果没有提取到，使用默认值
    if not system_prompt:
        system_prompt = "你是一位 AI 开发者，精通 LLM、Agent 等领域的知识，擅长深度解析学术论文。"

    # 构建用户提示词
    paper_title = metadata.get('title', '未知论文')
    paper_authors = ', '.join(metadata.get('authors', []))
    arxiv_id = metadata.get('arxiv_id', '未知')

    user_prompt = f"""
## 论文信息
- 标题：{paper_title}
- 作者：{paper_authors}
- arXiv ID: {arxiv_id}

## 论文全文
{paper_text[:150000]}  # 限制长度，避免超出 token 限制

---

请根据上述论文内容，按照以下模板生成分析笔记：

{template}

注意:
1. 请使用中文回答
2. 数学公式请使用 LaTeX 格式
3. 不要使用表格，使用列表格式
4. 保持内容简洁、有条理
"""

    return system_prompt.strip(), user_prompt.strip()


def analyze_paper(
    paper_text: str,
    template: str,
    metadata: dict,
    model: str = None,
    api_base: str = None,
    api_key: str = None,
    stream: bool = False,
) -> str:
    """
    使用 LLM 分析论文

    Args:
        paper_text: 论文全文
        template: 分析模板
        metadata: 论文元数据
        model: 模型名称 (可选，默认使用配置中的模型)
        api_base: API Base URL (可选，默认使用配置中的地址)
        api_key: API Key (可选，默认使用配置中的密钥)
        stream: 是否流式输出

    Returns:
        str: LLM 生成的分析内容
    """
    system_prompt, user_prompt = build_prompt(paper_text, template, metadata)

    messages = [{"role": "user", "content": user_prompt}]

    if stream:
        print("\n=== LLM 分析中 (流式输出) ===\n")
        content = ""
        for chunk in chat_completion(messages=messages, system=system_prompt, model=model, api_base=api_base, api_key=api_key, stream=True):
            print(chunk, end='', flush=True)
            content += chunk
        print("\n")
        return content
    else:
        logger.info("正在调用 LLM 分析论文...")
        content = chat_completion(messages=messages, system=system_prompt, model=model, api_base=api_base, api_key=api_key)
        logger.info("LLM 分析完成")
        return content


def process_single_paper(
    helper: PaperToMd,
    url: str,
    template_name: str,
    model: str = None,
    api_base: str = None,
    api_key: str = None,
    stream: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    处理单篇论文

    Args:
        helper: PaperToMd 实例
        url: 论文 URL
        template_name: 模板名称
        model: 模型名称 (可选)
        api_base: API Base URL (可选)
        api_key: API Key (可选)
        stream: 是否流式输出
        dry_run: 仅测试，不保存结果

    Returns:
        dict: 处理结果
    """
    logger.info(f"开始处理论文：{url}")

    try:
        # 步骤 1: 准备论文
        logger.info("步骤 1: 准备论文（下载 + 元数据）")
        pdf_path, metadata = helper.prepare_paper(url, download_pdf=True)
        logger.info(f"论文标题：{metadata.get('title', 'N/A')}")

        # 步骤 2: 提取文本
        logger.info("步骤 2: 从 PDF 提取文本")
        paper_text = helper.extract_text(pdf_path)
        logger.info(f"论文长度：{len(paper_text)} 字符")

        # 步骤 3: 获取模板
        logger.info(f"步骤 3: 获取模板 ({template_name})")
        template = helper.get_template()

        # 步骤 4: LLM 分析
        logger.info("步骤 4: LLM 分析")
        analysis_content = analyze_paper(
            paper_text=paper_text,
            template=template,
            metadata=metadata,
            model=model,
            api_base=api_base,
            api_key=api_key,
            stream=stream,
        )

        # 步骤 5: 保存结果
        if dry_run:
            logger.info("=== 干运行模式，不保存结果 ===")
            print("\n" + "=" * 60)
            print("分析结果预览:")
            print("=" * 60)
            print(analysis_content[:2000])
            print("...")
            print("=" * 60)
            return {
                'success': True,
                'url': url,
                'metadata': metadata,
                'content': analysis_content,
                'dry_run': True,
            }
        else:
            logger.info("步骤 5: 保存分析结果")
            result = helper.write_analysis(analysis_content, metadata)
            if result.get('success'):
                logger.info(f"结果已保存：{result.get('filepath')}")
            else:
                logger.error(f"保存失败：{result.get('error')}")

            return {
                'success': result.get('success', False),
                'url': url,
                'filepath': result.get('filepath'),
                'metadata': metadata,
            }

    except Exception as e:
        logger.error(f"处理失败：{e}")
        return {
            'success': False,
            'url': url,
            'error': str(e),
        }


def process_batch_papers(
    helper: PaperToMd,
    urls: List[str],
    template_name: str,
    model: str = None,
    api_base: str = None,
    api_key: str = None,
    stream: bool = False,
    delay_between_papers: int = 10,  # 论文间延迟（秒）
) -> dict:
    """
    批量处理论文

    Args:
        helper: PaperToMd 实例
        urls: 论文 URL 列表
        template_name: 模板名称
        model: 模型名称 (可选)
        api_base: API Base URL (可选)
        api_key: API Key (可选)
        stream: 是否流式输出
        delay_between_papers: 论文间延迟秒数（避免触发速率限制）

    Returns:
        dict: 批量处理结果
    """
    results = []
    success_count = 0

    for i, url in enumerate(urls, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"处理论文 {i}/{len(urls)}")
        logger.info(f"{'='*60}\n")

        result = process_single_paper(
            helper=helper,
            url=url,
            template_name=template_name,
            model=model,
            api_base=api_base,
            api_key=api_key,
            stream=stream,
        )

        results.append(result)
        if result.get('success'):
            success_count += 1

        # 如果不是最后一篇，等待一段时间
        if i < len(urls) and delay_between_papers > 0:
            logger.info(f"等待 {delay_between_papers} 秒后处理下一篇论文...")
            time.sleep(delay_between_papers)

    return {
        'total': len(urls),
        'success': success_count,
        'failed': len(urls) - success_count,
        'results': results,
    }


def organize_papers(helper: PaperToMd, model: str = None, api_base: str = None, api_key: str = None) -> dict:
    """
    整理已分析的论文

    Args:
        helper: PaperToMd 实例
        model: 模型名称 (可选)
        api_base: API Base URL (可选)
        api_key: API Key (可选)

    Returns:
        dict: 整理结果
    """
    logger.info("开始整理论文...")

    organizer = KnowledgeOrganizer()
    result = organizer.prepare_organize()

    if not result.get('success'):
        logger.error(f"准备整理失败：{result.get('error')}")
        return result

    if not result['docs']:
        logger.info("没有找到已分析的论文")
        return result

    # 使用 LLM 生成整理报告
    prompt = result['prompt']
    system_prompt = "你是一位学术整理助手，擅长总结和分析多篇论文的共同主题和关联关系。"

    user_prompt = f"""
请根据以下数据生成一份简洁的整理报告（使用中文）：

{prompt}

报告要求:
1. 研究主题总结（200-300 字）
2. 标签分类汇总
3. 值得关注的推荐论文
4. 未来研究方向建议
"""

    logger.info("正在调用 LLM 生成整理报告...")
    report = chat_completion(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        model=model,
        api_base=api_base,
        api_key=api_key,
    )

    # 保存整理报告
    write_result = organizer.write_organized_content(report)

    if write_result.get('success'):
        logger.info(f"整理报告已保存：{write_result.get('filepath')}")
    else:
        logger.error(f"保存整理报告失败：{write_result.get('error')}")

    return {
        'success': True,
        'report': report,
        'filepath': write_result.get('filepath'),
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Paper-to-MD 独立运行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 分析单篇论文
  python analyze.py --url "https://arxiv.org/abs/2506.13131"

  # 使用快速笔记模板
  python analyze.py --url "https://arxiv.org/abs/2506.13131" --template quick_note

  # 使用其他模型
  python analyze.py --url "https://arxiv.org/abs/2506.13131" --model ollama/qwen2.5

  # 流式输出
  python analyze.py --url "https://arxiv.org/abs/2506.13131" --stream

  # 干运行（预览结果，不保存）
  python analyze.py --url "https://arxiv.org/abs/2506.13131" --dry-run

  # 处理未处理列表中的论文
  python analyze.py --pending

  # 从文件批量处理
  python analyze.py --input-file papers.txt

  # 整理已分析的论文
  python analyze.py --organize
        """
    )

    # 输入选项
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--url', help='论文 URL')
    input_group.add_argument('--input-file', help='包含论文 URL 列表的文件路径')
    input_group.add_argument('--pending', action='store_true', help='处理未处理列表中的论文')
    input_group.add_argument('--organize', action='store_true', help='整理已分析的论文')

    # LLM 选项
    parser.add_argument('--model', help='模型名称 (默认：ollama/llama3.1)')
    parser.add_argument('--base-url', help='API Base URL (默认：http://localhost:11434)')

    # 处理选项
    parser.add_argument('--template', default='default',
                       choices=['default', 'quick_note', 'literature_review'],
                       help='分析模板 (默认：default)')
    parser.add_argument('--stream', action='store_true', help='流式输出')
    parser.add_argument('--dry-run', action='store_true', help='干运行（预览结果，不保存）')
    parser.add_argument('--storage-dir', help='存储目录 (可选)')
    parser.add_argument('--config', help='配置文件路径 (可选)')
    parser.add_argument('--delay', type=int, default=10,
                       help='批量处理时论文间的延迟秒数 (默认：10，避免触发速率限制)')

    # 日志选项
    parser.add_argument('--verbose', '-v', action='store_true', help='详细日志输出')

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 检查输入
    if not any([args.url, args.input_file, args.pending, args.organize]):
        parser.print_help()
        print("\n错误：请指定输入来源 (--url, --input-file, --pending, 或 --organize)")
        sys.exit(1)

    # 加载配置
    # 优先级：1. 用户传入的 --config 2. skill 目录下的 config.yaml 3. 空配置（使用默认值）
    config = {}
    config_path = args.config

    # 如果没有传入 --config，尝试使用 skill 目录下的 config.yaml
    if not config_path:
        skill_config = os.path.join(os.path.dirname(__file__), 'config.yaml')
        if os.path.exists(skill_config):
            config_path = skill_config

    if config_path and os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"已加载配置文件：{config_path}")
        except Exception as e:
            logger.warning(f"加载配置文件失败：{e}，使用默认配置")
    else:
        logger.info("未找到配置文件，使用默认配置")

    # 从配置获取 LLM 设置 (命令行参数优先)
    llm_config = config.get('llm', {})
    model = args.model or llm_config.get('model', DEFAULT_MODEL)
    api_base = args.base_url or llm_config.get('api_base', DEFAULT_API_BASE)
    api_key = llm_config.get('api_key')  # 从配置文件读取 api_key（可选）

    # 初始化 PaperToMd
    logger.info(f"初始化 PaperToMd: storage_dir={args.storage_dir or 'default'}")
    helper = PaperToMd(
        template=args.template,
        config_path=args.config,
        storage_dir=args.storage_dir,
    )

    # 执行任务
    if args.organize:
        # 整理已分析的论文
        result = organize_papers(helper, model=model, api_base=api_base, api_key=api_key)
    elif args.input_file:
        # 批量处理
        with open(args.input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"从文件读取到 {len(urls)} 篇论文")
        result = process_batch_papers(helper, urls, args.template, model=model, api_base=api_base, api_key=api_key, stream=args.stream, delay_between_papers=args.delay)
    elif args.pending:
        # 处理未处理列表
        urls = helper.get_pending_papers()
        logger.info(f"未处理列表中有 {len(urls)} 篇论文")
        result = process_batch_papers(helper, urls, args.template, model=model, api_base=api_base, api_key=api_key, stream=args.stream, delay_between_papers=args.delay)
    else:
        # 处理单篇论文
        result = process_single_paper(
            helper=helper,
            url=args.url,
            template_name=args.template,
            model=model,
            api_base=api_base,
            api_key=api_key,
            stream=args.stream,
            dry_run=args.dry_run,
        )

    # 输出结果
    print("\n" + "=" * 60)
    if result.get('success'):
        print("✅ 处理完成!")
        if result.get('filepath'):
            print(f"   文件路径：{result['filepath']}")
        if result.get('report'):
            print(f"   整理报告:\n{result['report']}")
    else:
        print("❌ 处理失败!")
        if result.get('error'):
            print(f"   错误：{result['error']}")
        sys.exit(1)

    print("=" * 60)


if __name__ == '__main__':
    main()
