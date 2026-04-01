"""
LLM 调用模块
直接使用 litellm 调用各种 LLM 模型

支持的免费模型:
- Ollama (本地运行，完全免费): ollama/llama3.1, ollama/llama3.2, ollama/mistral
- OpenRouter 免费模型：openrouter/google/gemma-7b-it:free
- Hugging Face 免费额度

用法:
    # 简单调用 (使用默认配置)
    from scripts.llm_client import chat_completion

    response = chat_completion(
        messages=[{"role": "user", "content": "你好"}],
        system="你是一个助手"
    )

    # 使用 Ollama (免费)
    response = chat_completion(
        model="ollama/llama3.1",
        messages=[...],
        api_base="http://localhost:11434"
    )

    # 流式调用
    for chunk in chat_completion(messages=[...], stream=True):
        print(chunk, end='')
"""

import os
import logging
from typing import Optional, List, Dict, Any, Iterator

logger = logging.getLogger(__name__)

# 免费模型列表
FREE_MODELS = [
    "ollama/llama3.1",
    "ollama/llama3.2",
    "ollama/mistral",
    "ollama/qwen2.5",
    "openrouter/google/gemma-7b-it:free",
    "openrouter/meta-llama/llama-3-8b-instruct:free",
]

# 默认模型 (Ollama - 免费)
DEFAULT_MODEL = "ollama/llama3.1"
DEFAULT_API_BASE = "http://localhost:11434"


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    system: Optional[str] = None,
    stream: bool = False,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    timeout: int = 120,
    **kwargs
) -> str | Iterator[str]:
    """
    调用 LLM 完成聊天任务

    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}, ...]
        model: 模型名称 (默认：ollama/llama3.1)
               免费选项：ollama/llama3.1, ollama/mistral, openrouter/...:free
        system: 系统提示词 (可选)
        stream: 是否流式输出
        api_key: API Key (Ollama 不需要)
        api_base: API Base URL (Ollama: http://localhost:11434)
        max_tokens: 最大输出 token 数
        temperature: 温度参数 (0-2)
        timeout: 请求超时时间 (秒)
        **kwargs: 其他传递给 litellm 的参数

    Returns:
        str | Iterator[str]: 非流式返回完整响应，流式返回生成器

    示例:
        # 使用 Ollama (免费)
        >>> response = chat_completion(
        ...     model="ollama/llama3.1",
        ...     messages=[{"role": "user", "content": "你好"}],
        ...     api_base="http://localhost:11434"
        ... )

        # 使用 OpenRouter 免费模型
        >>> response = chat_completion(
        ...     model="openrouter/google/gemma-7b-it:free",
        ...     messages=[{"role": "user", "content": "你好"}]
        ... )
    """
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("请安装 litellm: pip install litellm")

    # 设置默认模型
    model_id = model or DEFAULT_MODEL

    # 如果不是完整格式，报错
    assert "/" in model_id, f"请确保 model 名称是完整格式，如 ollama/llama3.1"

    # 构建完整的消息列表
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    # 构建请求参数
    request_kwargs = {
        "model": model_id,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "timeout": timeout,
        "api_base": api_base or DEFAULT_API_BASE,  # 确保 api_base 始终设置（Ollama 需要）
    }

    # 添加 API Key (如果有，Ollama 不需要)
    if api_key:
        request_kwargs["api_key"] = api_key

    # 添加额外参数
    request_kwargs.update(kwargs)

    logger.info(f"调用 LLM: model={model_id}, stream={stream}")

    # 流式或非流式调用
    if stream:
        return _stream_completion(completion, request_kwargs)
    else:
        return _non_stream_completion(completion, request_kwargs)


def _non_stream_completion(completion, request_kwargs: Dict[str, Any]) -> str:
    """非流式调用"""
    try:
        response = completion(**request_kwargs)
        content = response.choices[0].message.content
        result = content.strip() if content else ""
        logger.info(f"LLM 响应完成，长度：{len(result)} 字符")
        return result
    except Exception as e:
        logger.error(f"LLM 调用失败：{e}")
        raise


def _stream_completion(completion, request_kwargs: Dict[str, Any]) -> Iterator[str]:
    """流式调用"""
    try:
        response = completion(stream=True, **request_kwargs)
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
    except Exception as e:
        logger.error(f"LLM 流式调用失败：{e}")
        raise


def check_ollama_available(api_base: str = DEFAULT_API_BASE) -> bool:
    """
    检查 Ollama 服务是否可用

    Args:
        api_base: Ollama 服务地址

    Returns:
        bool: Ollama 是否可用
    """
    try:
        import requests
        response = requests.get(f"{api_base}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def list_ollama_models(api_base: str = DEFAULT_API_BASE) -> List[str]:
    """
    列出 Ollama 本地可用模型

    Args:
        api_base: Ollama 服务地址

    Returns:
        模型名称列表
    """
    try:
        import requests
        response = requests.get(f"{api_base}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m.get("name", "") for m in data.get("models", [])]
        return []
    except Exception as e:
        logger.error(f"获取 Ollama 模型列表失败：{e}")
        return []
