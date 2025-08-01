import json
import uuid
import time
from typing import Dict, Any, List, Optional, Union
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, Choice, Usage
from app.schemas.anthropic import AnthropicRequest, AnthropicMessage, AnthropicResponse, CountTokensRequest


class TranslationService:
    
    @staticmethod
    def map_claude_model_to_provider_model(claude_model: str, provider_config: Dict[str, Any]) -> str:
        if "haiku" in claude_model.lower():
            return provider_config.get("small_model", "gpt-4o-mini")
        elif "sonnet" in claude_model.lower():
            return provider_config.get("medium_model", "gpt-4o")
        elif "opus" in claude_model.lower():
            return provider_config.get("big_model", "gpt-4o")
        else:
            return provider_config.get("medium_model", "gpt-4o")
    
    @staticmethod
    def openai_to_anthropic(openai_request: ChatCompletionRequest) -> AnthropicRequest:
        messages = []
        system_message = None
        
        for msg in openai_request.messages:
            if msg.role == "system":
                system_message = msg.content if isinstance(msg.content, str) else str(msg.content)
            elif msg.role in ["user", "assistant"]:
                content = msg.content
                if isinstance(content, list):
                    formatted_content = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                formatted_content.append({"type": "text", "text": item.get("text", "")})
                            elif item.get("type") == "image_url":
                                if "base64" in item.get("image_url", {}).get("url", ""):
                                    base64_data = item["image_url"]["url"].split(",", 1)[1]
                                    media_type = "image/jpeg"
                                    if "data:image/png" in item["image_url"]["url"]:
                                        media_type = "image/png"
                                    formatted_content.append({
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": base64_data
                                        }
                                    })
                    content = formatted_content if formatted_content else str(content)
                
                messages.append(AnthropicMessage(role=msg.role, content=content))
        
        anthropic_request = AnthropicRequest(
            model=openai_request.model,
            max_tokens=openai_request.max_tokens or 4096,
            messages=messages,
            system=system_message,
            temperature=openai_request.temperature,
            top_p=openai_request.top_p,
            stop_sequences=openai_request.stop if isinstance(openai_request.stop, list) else [openai_request.stop] if openai_request.stop else None,
            stream=openai_request.stream or False,
            tools=openai_request.tools,
            tool_choice=openai_request.tool_choice
        )
        
        return anthropic_request
    
    @staticmethod
    def anthropic_to_openai_response(anthropic_response: AnthropicResponse, original_model: str) -> ChatCompletionResponse:
        content = ""
        tool_calls = None
        
        if anthropic_response.content:
            for item in anthropic_response.content:
                if item.get("type") == "text":
                    content += item.get("text", "")
                elif item.get("type") == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": item.get("id"),
                        "type": "function",
                        "function": {
                            "name": item.get("name"),
                            "arguments": json.dumps(item.get("input", {}))
                        }
                    })
        
        message = ChatMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls
        )
        
        choice = Choice(
            index=0,
            message=message,
            finish_reason=anthropic_response.stop_reason
        )
        
        usage = Usage(
            prompt_tokens=anthropic_response.usage.input_tokens,
            completion_tokens=anthropic_response.usage.output_tokens,
            total_tokens=anthropic_response.usage.input_tokens + anthropic_response.usage.output_tokens
        )
        
        return ChatCompletionResponse(
            id=anthropic_response.id,
            created=int(time.time()),
            model=original_model,
            choices=[choice],
            usage=usage
        )
    
    @staticmethod
    def anthropic_to_openai_request(anthropic_request: AnthropicRequest) -> ChatCompletionRequest:
        messages = []
        
        if anthropic_request.system:
            messages.append(ChatMessage(role="system", content=anthropic_request.system))
        
        for msg in anthropic_request.messages:
            content = msg.content
            if isinstance(content, list):
                formatted_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            formatted_content.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image":
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                data_url = f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                formatted_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": data_url}
                                })
                content = formatted_content if formatted_content else str(content)
            
            messages.append(ChatMessage(role=msg.role, content=content))
        
        return ChatCompletionRequest(
            model=anthropic_request.model,
            messages=messages,
            temperature=anthropic_request.temperature,
            max_tokens=anthropic_request.max_tokens,
            top_p=anthropic_request.top_p,
            stop=anthropic_request.stop_sequences,
            stream=anthropic_request.stream,
            tools=anthropic_request.tools,
            tool_choice=anthropic_request.tool_choice
        )
    
    @staticmethod
    def count_tokens_to_openai_request(count_tokens_request: CountTokensRequest) -> ChatCompletionRequest:
        messages = []
        
        if count_tokens_request.system:
            messages.append(ChatMessage(role="system", content=count_tokens_request.system))
        
        for msg in count_tokens_request.messages:
            content = msg.content
            if isinstance(content, list):
                formatted_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            formatted_content.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image":
                            source = item.get("source", {})
                            if source.get("type") == "base64":
                                data_url = f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                formatted_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": data_url}
                                })
                content = formatted_content if formatted_content else str(content)
            
            messages.append(ChatMessage(role=msg.role, content=content))
        
        return ChatCompletionRequest(
            model=count_tokens_request.model,
            messages=messages,
            max_tokens=1,
            stream=False
        )