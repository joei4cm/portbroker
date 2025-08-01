from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import json
import httpx
from app.core.database import get_db
from app.schemas.anthropic import AnthropicRequest, AnthropicResponse
from app.schemas.openai import ChatCompletionRequest
from app.services.provider_service import ProviderService
from app.services.translation import TranslationService

router = APIRouter()


async def stream_anthropic_response(openai_response: httpx.Response) -> AsyncGenerator[str, None]:
    try:
        async for chunk in openai_response.aiter_text():
            if chunk.strip() and chunk.startswith("data: "):
                data_part = chunk[6:].strip()
                if data_part == "[DONE]":
                    yield 'event: message_stop\ndata: {}\n\n'
                    break
                
                try:
                    openai_chunk = json.loads(data_part)
                    if openai_chunk.get("choices") and len(openai_chunk["choices"]) > 0:
                        delta = openai_chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            anthropic_chunk = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": delta["content"]}
                            }
                            yield f'event: content_block_delta\ndata: {json.dumps(anthropic_chunk)}\n\n'
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        error_event = {
            "type": "error",
            "error": {"type": "api_error", "message": str(e)}
        }
        yield f'event: error\ndata: {json.dumps(error_event)}\n\n'


@router.post("/messages")
async def create_message(
    request: AnthropicRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        openai_request = TranslationService.anthropic_to_openai_request(request)
        
        if request.stream:
            openai_response = await ProviderService.try_providers_until_success(
                db, openai_request, stream=True
            )
            if isinstance(openai_response, httpx.Response):
                return StreamingResponse(
                    stream_anthropic_response(openai_response),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="Invalid streaming response")
        else:
            openai_response_data = await ProviderService.try_providers_until_success(
                db, openai_request, stream=False
            )
            
            anthropic_response = {
                "id": openai_response_data.get("id", "msg_unknown"),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": request.model,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": openai_response_data.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": openai_response_data.get("usage", {}).get("completion_tokens", 0)
                }
            }
            
            if openai_response_data.get("choices") and len(openai_response_data["choices"]) > 0:
                message = openai_response_data["choices"][0].get("message", {})
                content_text = message.get("content", "")
                
                if content_text:
                    anthropic_response["content"].append({
                        "type": "text",
                        "text": content_text
                    })
                
                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        function = tool_call.get("function", {})
                        anthropic_response["content"].append({
                            "type": "tool_use",
                            "id": tool_call.get("id"),
                            "name": function.get("name"),
                            "input": json.loads(function.get("arguments", "{}"))
                        })
                
                finish_reason = openai_response_data["choices"][0].get("finish_reason")
                if finish_reason:
                    anthropic_response["stop_reason"] = finish_reason
            
            return anthropic_response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))