import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from app.schemas.anthropic import (
    AnthropicMessage,
    AnthropicRequest,
    AnthropicResponse,
    CountTokensRequest,
)
from app.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)


class TranslationService:

    @staticmethod
    def map_claude_model_to_provider_model(
        claude_model: str, provider_config: Dict[str, Any]
    ) -> str:
        model_list = provider_config.get("model_list", [])

        # Fallback to old model fields for backward compatibility
        if "haiku" in claude_model.lower():
            return provider_config.get(
                "small_model"
            ) or TranslationService._select_model_from_list(model_list, "small")
        elif "sonnet" in claude_model.lower():
            return provider_config.get(
                "medium_model"
            ) or TranslationService._select_model_from_list(model_list, "medium")
        elif "opus" in claude_model.lower():
            return provider_config.get(
                "big_model"
            ) or TranslationService._select_model_from_list(model_list, "big")
        else:
            return provider_config.get(
                "medium_model"
            ) or TranslationService._select_model_from_list(model_list, "medium")

    @staticmethod
    def _select_model_from_list(model_list: List[str], size_category: str) -> str:
        """Select appropriate model from model_list based on size category"""
        if not model_list:
            # Default fallback models
            defaults = {"small": "gpt-4o-mini", "medium": "gpt-4o", "big": "gpt-4o"}
            return defaults.get(size_category, "gpt-4o")

        # Common model patterns by size
        small_patterns = ["mini", "small", "haiku", "3.5", "4o-mini"]
        medium_patterns = ["4o", "sonnet", "medium", "turbo"]
        big_patterns = ["4", "gpt-4", "opus", "large", "preview"]

        # Filter models by size category
        if size_category == "small":
            candidates = [
                m for m in model_list if any(p in m.lower() for p in small_patterns)
            ]
        elif size_category == "medium":
            candidates = [
                m for m in model_list if any(p in m.lower() for p in medium_patterns)
            ]
        elif size_category == "big":
            candidates = [
                m for m in model_list if any(p in m.lower() for p in big_patterns)
            ]
        else:
            candidates = model_list

        # Return first candidate or fallback to first model in list
        return candidates[0] if candidates else model_list[0]

    @staticmethod
    def openai_to_anthropic(openai_request: ChatCompletionRequest) -> AnthropicRequest:
        messages = []
        system_message = None

        for msg in openai_request.messages:
            if msg.role == "system":
                system_message = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
            elif msg.role in ["user", "assistant"]:
                content = msg.content
                if isinstance(content, list):
                    formatted_content = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                formatted_content.append(
                                    {"type": "text", "text": item.get("text", "")}
                                )
                            elif item.get("type") == "image_url":
                                if "base64" in item.get("image_url", {}).get("url", ""):
                                    base64_data = item["image_url"]["url"].split(
                                        ",", 1
                                    )[1]
                                    media_type = "image/jpeg"
                                    if "data:image/png" in item["image_url"]["url"]:
                                        media_type = "image/png"
                                    formatted_content.append(
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": media_type,
                                                "data": base64_data,
                                            },
                                        }
                                    )
                    content = formatted_content if formatted_content else str(content)

                messages.append(AnthropicMessage(role=str(msg.role), content=content))  # type: ignore

        anthropic_request = AnthropicRequest(
            model=openai_request.model,
            max_tokens=openai_request.max_tokens or 4096,
            messages=messages,
            system=system_message,
            temperature=openai_request.temperature,
            top_p=openai_request.top_p,
            top_k=None,  # Not available in OpenAI request
            stop_sequences=(
                openai_request.stop
                if isinstance(openai_request.stop, list)
                else [openai_request.stop] if openai_request.stop else None
            ),
            stream=openai_request.stream or False,
            tools=openai_request.tools or None,
            tool_choice=openai_request.tool_choice or None,
        )

        return anthropic_request

    @staticmethod
    def anthropic_to_openai_response(
        anthropic_response: AnthropicResponse, original_model: str
    ) -> ChatCompletionResponse:
        content = ""
        tool_calls = None

        if anthropic_response.content:
            content_items = anthropic_response.content
            if isinstance(content_items, list):
                for item in content_items:
                    # Handle both dict and object access
                    if hasattr(item, "get"):
                        item_dict = item
                    else:
                        item_dict = item.__dict__

                    if item_dict.get("type") == "text":
                        content += item_dict.get("text", "")
                    elif item_dict.get("type") == "tool_use":
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append(
                            {
                                "id": item_dict.get("id"),
                                "type": "function",
                                "function": {
                                    "name": item_dict.get("name"),
                                    "arguments": json.dumps(item_dict.get("input", {})),
                                },
                            }
                        )

        message = ChatMessage(role="assistant", content=content, tool_calls=tool_calls)

        choice = Choice(
            index=0, message=message, finish_reason=anthropic_response.stop_reason
        )

        usage = Usage(
            prompt_tokens=anthropic_response.usage.input_tokens,
            completion_tokens=anthropic_response.usage.output_tokens,
            total_tokens=anthropic_response.usage.input_tokens
            + anthropic_response.usage.output_tokens,
        )

        return ChatCompletionResponse(
            id=anthropic_response.id,
            created=int(time.time()),
            model=original_model,
            choices=[choice],
            usage=usage,
        )

    @staticmethod
    def anthropic_to_openai_request(
        anthropic_request: AnthropicRequest,
    ) -> ChatCompletionRequest:
        messages = []

        if anthropic_request.system:
            messages.append(
                ChatMessage(role="system", content=anthropic_request.system)
            )

        for msg in anthropic_request.messages:
            content = msg.content
            if isinstance(content, list):
                formatted_content: List[Dict[str, Any]] = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            formatted_content.append(
                                {"type": "text", "text": item.get("text", "")}
                            )
                        elif item.get("type") == "image":
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                data_url = f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                formatted_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": data_url},
                                    }
                                )
                    else:
                        # Handle Pydantic model objects
                        if hasattr(item, "type") and item.type == "text":
                            formatted_content.append(
                                {"type": "text", "text": getattr(item, "text", "")}
                            )
                        elif hasattr(item, "type") and item.type == "image":
                            # Handle Pydantic model objects
                            source = getattr(item, "source", {})
                            if hasattr(source, "type") and source.type == "base64":
                                data_url = f"data:{getattr(source, 'media_type', 'image/jpeg')};base64,{getattr(source, 'data', '')}"
                                formatted_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": data_url},
                                    }
                                )
                content = formatted_content if formatted_content else str(content)

            messages.append(ChatMessage(role=str(msg.role), content=content))  # type: ignore

        return ChatCompletionRequest(
            model=anthropic_request.model,
            messages=messages,
            temperature=anthropic_request.temperature,
            max_tokens=anthropic_request.max_tokens,
            top_p=anthropic_request.top_p,
            stop=anthropic_request.stop_sequences,
            stream=anthropic_request.stream,
            tools=anthropic_request.tools,
            tool_choice=anthropic_request.tool_choice,
        )

    @staticmethod
    def count_tokens_to_openai_request(
        count_tokens_request: CountTokensRequest,
    ) -> ChatCompletionRequest:
        messages = []

        if count_tokens_request.system:
            messages.append(
                ChatMessage(role="system", content=count_tokens_request.system)
            )

        for msg in count_tokens_request.messages:
            content = msg.content
            if isinstance(content, list):
                formatted_content: List[Dict[str, Any]] = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            formatted_content.append(
                                {"type": "text", "text": item.get("text", "")}
                            )
                        elif item.get("type") == "image":
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                data_url = f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                formatted_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": data_url},
                                    }
                                )
                    else:
                        # Handle Pydantic model objects
                        if hasattr(item, "type") and item.type == "text":
                            formatted_content.append(
                                {"type": "text", "text": getattr(item, "text", "")}
                            )
                        elif hasattr(item, "type") and item.type == "image":
                            # Handle Pydantic model objects
                            source = getattr(item, "source", {})
                            if hasattr(source, "type") and source.type == "base64":
                                data_url = f"data:{getattr(source, 'media_type', 'image/jpeg')};base64,{getattr(source, 'data', '')}"
                                formatted_content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": data_url},
                                    }
                                )
                content = formatted_content if formatted_content else str(content)

            messages.append(ChatMessage(role=str(msg.role), content=content))  # type: ignore

        return ChatCompletionRequest(
            model=count_tokens_request.model,
            messages=messages,
            max_tokens=1,
            stream=False,
        )
