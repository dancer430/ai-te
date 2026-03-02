"""
AI 客户端抽象层

支持多个 AI 提供商：Anthropic、GLM（智谱AI）等
"""

import os
import json
import base64
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class AIResponse:
    """AI 响应"""
    content: str  # 文本内容
    tool_calls: List[ToolCall]  # 工具调用列表
    stop_reason: str  # 停止原因: end_turn, tool_use, max_tokens
    raw_response: Any  # 原始响应对象


class AIClient(ABC):
    """AI 客户端抽象基类"""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict],
        system: str,
        tools: List[Dict],
        max_tokens: int = 4096
    ) -> AIResponse:
        """
        发送对话请求

        Args:
            messages: 对话消息列表
            system: 系统提示词
            tools: 工具定义列表
            max_tokens: 最大输出 token 数

        Returns:
            AIResponse 对象
        """
        pass

    @abstractmethod
    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_image: bool = False,
        image_base64: Optional[str] = None
    ) -> Dict:
        """
        格式化工具执行结果

        Args:
            tool_call_id: 工具调用 ID
            result: 执行结果
            is_image: 是否包含图片
            image_base64: 图片 base64 数据

        Returns:
            格式化后的消息字典
        """
        pass

    @abstractmethod
    def format_assistant_message(self, response: AIResponse) -> Dict:
        """
        格式化助手消息（用于添加到消息历史）

        Args:
            response: AI 响应

        Returns:
            格式化后的消息字典
        """
        pass


class AnthropicClient(AIClient):
    """Anthropic Claude 客户端"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def chat(
        self,
        messages: List[Dict],
        system: str,
        tools: List[Dict],
        max_tokens: int = 4096
    ) -> AIResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages
        )

        # 解析响应
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))

        return AIResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_response=response
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_image: bool = False,
        image_base64: Optional[str] = None
    ) -> Dict:
        """Anthropic 格式的工具结果"""
        if is_image and image_base64:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False)},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }
        else:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": json.dumps(result, ensure_ascii=False)
            }

    def format_assistant_message(self, response: AIResponse) -> Dict:
        """Anthropic 格式的助手消息"""
        content = []
        if response.content:
            content.append({"type": "text", "text": response.content})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input
            })
        return {"role": "assistant", "content": content}


class GLMClient(AIClient):
    """智谱 AI GLM 客户端"""

    def __init__(self, api_key: Optional[str] = None, model: str = "glm-4-plus"):
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=api_key or os.environ.get("ZHIPUAI_API_KEY"))
        except ImportError:
            raise ImportError("请安装 zhipuai: pip install zhipuai")
        self.model = model

    def _convert_tools_to_openai_format(self, tools: List[Dict]) -> List[Dict]:
        """将 Anthropic 格式的工具定义转换为 OpenAI/GLM 格式"""
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {})
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def _convert_messages_to_glm_format(self, messages: List[Dict], system: str) -> List[Dict]:
        """将 Anthropic 格式的消息转换为 GLM 格式"""
        glm_messages = []

        # 添加系统消息
        if system:
            glm_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            if role == "user":
                # 处理用户消息
                if isinstance(content, str):
                    glm_messages.append({"role": "user", "content": content})
                elif isinstance(content, list):
                    # 处理包含工具结果的消息
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "tool_result":
                                # 之前尝试将工具结果转换为 role=tool 的消息，
                                # 但部分 GLM 接口对 messages 要求较严格，可能不接受该角色。
                                # 这里改为将工具结果直接串联为普通文本，作为 user 消息的一部分，
                                # 既能让模型看到工具输出，又能避免 messages 参数非法。
                                tool_content = item.get("content", "")
                                if isinstance(tool_content, list):
                                    # 提取文本内容
                                    for c in tool_content:
                                        if c.get("type") == "text":
                                            tool_content = c.get("text", "")
                                            break
                                if not isinstance(tool_content, str):
                                    tool_content = json.dumps(
                                        tool_content,
                                        ensure_ascii=False
                                    )
                                text_parts.append(
                                    f"[工具结果] {tool_content}"
                                )
                            elif item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "image":
                                # GLM 支持图片，但格式不同，这里简化处理
                                text_parts.append("[图片内容]")
                    if text_parts:
                        glm_messages.append({"role": "user", "content": "\n".join(text_parts)})

            elif role == "assistant":
                # 处理助手消息
                if isinstance(content, str):
                    glm_messages.append({"role": "assistant", "content": content})
                elif isinstance(content, list):
                    text_content = ""
                    tool_calls = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_content = item.get("text", "")
                            elif item.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": item.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": item.get("name", ""),
                                        "arguments": json.dumps(item.get("input", {}), ensure_ascii=False)
                                    }
                                })

                    assistant_msg = {"role": "assistant"}
                    if text_content:
                        assistant_msg["content"] = text_content
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    if text_content or tool_calls:
                        glm_messages.append(assistant_msg)

        return glm_messages

    def chat(
        self,
        messages: List[Dict],
        system: str,
        tools: List[Dict],
        max_tokens: int = 4096
    ) -> AIResponse:
        # 转换格式
        glm_messages = self._convert_messages_to_glm_format(messages, system)
        glm_tools = self._convert_tools_to_openai_format(tools)

        # 调用 GLM API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=glm_messages,
            tools=glm_tools if glm_tools else None,
            max_tokens=max_tokens
        )

        # 解析响应
        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments) if tc.function.arguments else {}
                ))

        # 映射停止原因
        stop_reason_map = {
            "stop": "end_turn",
            "tool_calls": "tool_use",
            "length": "max_tokens"
        }
        stop_reason = stop_reason_map.get(choice.finish_reason, choice.finish_reason)

        return AIResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_response=response
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_image: bool = False,
        image_base64: Optional[str] = None
    ) -> Dict:
        """GLM 格式的工具结果

        注意：GLM 的上下文长度有限，这里对工具结果做必要裁剪，
        例如移除截图的 base64 数据，防止请求因为输入过长而失败。
        """
        # 移除截图的 base64 数据，避免占用大量 token
        result_copy = dict(result) if isinstance(result, dict) else result
        if isinstance(result_copy, dict) and "screenshot_base64" in result_copy:
            result_copy = {
                k: v for k, v in result_copy.items() if k != "screenshot_base64"
            }
            # 为了让模型仍然知道有截图，可以追加简短说明
            message = result_copy.get("message") or ""
            extra_note = "截图已获取，请结合上下文理解页面状态"
            if message:
                result_copy["message"] = f"{message}（{extra_note}）"
            else:
                result_copy["message"] = extra_note

        # 对特别长的字符串字段做简单截断，进一步降低超长风险
        if isinstance(result_copy, dict):
            truncated: Dict[str, Any] = {}
            for key, value in result_copy.items():
                if isinstance(value, str) and len(value) > 4000:
                    truncated[key] = value[:4000] + "...（内容已截断）"
                else:
                    truncated[key] = value
            result_copy = truncated

        result_text = json.dumps(result_copy, ensure_ascii=False)
        if is_image and image_base64:
            result_text += "\n[截图已获取，请根据结果继续操作]"

        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result_text
        }

    def format_assistant_message(self, response: AIResponse) -> Dict:
        """GLM 格式的助手消息（转换为统一格式存储）"""
        content = []
        if response.content:
            content.append({"type": "text", "text": response.content})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input
            })
        return {"role": "assistant", "content": content}


def create_ai_client(
    provider: str = "anthropic",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> AIClient:
    """
    创建 AI 客户端

    Args:
        provider: AI 提供商 (anthropic, glm)
        api_key: API 密钥
        model: 模型名称

    Returns:
        AIClient 实例
    """
    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514"
        )
    elif provider == "glm":
        return GLMClient(
            api_key=api_key,
            model=model or "glm-4-plus"
        )
    else:
        raise ValueError(f"不支持的 AI 提供商: {provider}")
