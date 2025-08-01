from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import json
import httpx
from app.core.database import get_db
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services.provider_service import ProviderService

router = APIRouter()


async def stream_response(response: httpx.Response) -> AsyncGenerator[str, None]:
    try:
        async for chunk in response.aiter_text():
            if chunk.strip():
                yield f"data: {chunk}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        if request.stream:
            response = await ProviderService.try_providers_until_success(
                db, request, stream=True
            )
            if isinstance(response, httpx.Response):
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/plain",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                raise HTTPException(status_code=500, detail="Invalid streaming response")
        else:
            response_data = await ProviderService.try_providers_until_success(
                db, request, stream=False
            )
            return response_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))