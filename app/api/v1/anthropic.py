import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.anthropic import (
    AnthropicRequest,
    AnthropicResponse,
    CountTokensRequest,
    CountTokensResponse,
    FileList,
    FilePurpose,
    FileUpload,
    MessageBatch,
    MessageBatchList,
    MessageBatchRequest,
    MessageBatchResults,
    MessageBatchStatus,
    ModelInfo,
    ModelListResponse,
    StopReason,
    TextContent,
    ToolUseContent,
)
from app.services.provider_service import ProviderService
from app.services.translation import TranslationService

router = APIRouter()


async def stream_anthropic_response(
    openai_response: httpx.Response,
) -> AsyncGenerator[str, None]:
    try:
        message_id = str(uuid.uuid4())
        message_started = False

        yield f'event: message_start\ndata: {json.dumps({"type": "message_start", "message": {"id": message_id, "type": "message", "role": "assistant", "content": [], "model": "claude-3-sonnet-20240229", "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0}}})}\n\n'

        async for chunk in openai_response.aiter_text():
            if chunk.strip() and chunk.startswith("data: "):
                data_part = chunk[6:].strip()
                if data_part == "[DONE]":
                    yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'
                    break

                try:
                    openai_chunk = json.loads(data_part)
                    if openai_chunk.get("choices") and len(openai_chunk["choices"]) > 0:
                        delta = openai_chunk["choices"][0].get("delta", {})

                        if "content" in delta and delta["content"]:
                            if not message_started:
                                yield f'event: content_block_start\ndata: {json.dumps({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})}\n\n'
                                message_started = True

                            anthropic_chunk = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {
                                    "type": "text_delta",
                                    "text": delta["content"],
                                },
                            }
                            yield f"event: content_block_delta\ndata: {json.dumps(anthropic_chunk)}\n\n"

                        if openai_chunk.get("usage"):
                            usage = openai_chunk["usage"]
                            yield f'event: message_delta\ndata: {json.dumps({"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}})}\n\n'

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        error_event = {
            "type": "error",
            "error": {"type": "api_error", "message": str(e)},
        }
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"


@router.post("/messages")
async def create_message(request: AnthropicRequest, db: AsyncSession = Depends(get_db)):
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
                        "X-Accel-Buffering": "no",
                    },
                )
            else:
                raise HTTPException(
                    status_code=500, detail="Invalid streaming response"
                )
        else:
            openai_response_data = await ProviderService.try_providers_until_success(
                db, openai_request, stream=False
            )

            content_blocks = []
            if (
                openai_response_data.get("choices")
                and len(openai_response_data["choices"]) > 0
            ):
                message = openai_response_data["choices"][0].get("message", {})
                content_text = message.get("content", "")

                if content_text:
                    content_blocks.append(TextContent(text=content_text))

                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        function = tool_call.get("function", {})
                        content_blocks.append(
                            ToolUseContent(
                                id=tool_call.get("id"),
                                name=function.get("name"),
                                input=json.loads(function.get("arguments", "{}")),
                            )
                        )

            anthropic_response = AnthropicResponse(
                id=openai_response_data.get("id", f"msg_{uuid.uuid4().hex[:8]}"),
                content=content_blocks,
                model=request.model,
                stop_reason=StopReason.end_turn,
                usage={
                    "input_tokens": openai_response_data.get("usage", {}).get(
                        "prompt_tokens", 0
                    ),
                    "output_tokens": openai_response_data.get("usage", {}).get(
                        "completion_tokens", 0
                    ),
                },
            )

            if (
                openai_response_data.get("choices")
                and len(openai_response_data["choices"]) > 0
            ):
                finish_reason = openai_response_data["choices"][0].get("finish_reason")
                if finish_reason:
                    anthropic_response.stop_reason = finish_reason

            return anthropic_response.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/count_tokens")
async def count_tokens(request: CountTokensRequest, db: AsyncSession = Depends(get_db)):
    try:
        openai_request = TranslationService.count_tokens_to_openai_request(request)

        openai_response_data = await ProviderService.try_providers_until_success(
            db, openai_request, stream=False
        )

        return CountTokensResponse(
            input_tokens=openai_response_data.get("usage", {}).get("prompt_tokens", 0)
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    try:
        providers = await ProviderService.get_active_providers(db)

        models = []
        for provider in providers:
            if provider.small_model:
                models.append(
                    ModelInfo(
                        id=provider.small_model,
                        created=int(datetime.now().timestamp()),
                        type="claude",
                        display_name=provider.small_model,
                        max_tokens=8192,
                        context_length=200000,
                        supported_modalities=["text"],
                    )
                )
            if provider.medium_model:
                models.append(
                    ModelInfo(
                        id=provider.medium_model,
                        created=int(datetime.now().timestamp()),
                        type="claude",
                        display_name=provider.medium_model,
                        max_tokens=8192,
                        context_length=200000,
                        supported_modalities=["text"],
                    )
                )
            if provider.big_model:
                models.append(
                    ModelInfo(
                        id=provider.big_model,
                        created=int(datetime.now().timestamp()),
                        type="claude",
                        display_name=provider.big_model,
                        max_tokens=8192,
                        context_length=200000,
                        supported_modalities=["text"],
                    )
                )

        return ModelListResponse(data=models).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    try:
        providers = await ProviderService.get_active_providers(db)

        for provider in providers:
            if model_id in [
                provider.small_model,
                provider.medium_model,
                provider.big_model,
            ]:
                return ModelInfo(
                    id=model_id,
                    created=int(datetime.now().timestamp()),
                    type="claude",
                    display_name=model_id,
                    max_tokens=8192,
                    context_length=200000,
                    supported_modalities=["text"],
                ).model_dump()

        raise HTTPException(status_code=404, detail="Model not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/batches")
async def create_message_batch(
    request: MessageBatchRequest, db: AsyncSession = Depends(get_db)
):
    try:
        batch_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()

        batch = MessageBatch(
            id=batch_id,
            processing_status=MessageBatchStatus.in_progress,
            request_counts={"total": len(request.requests)},
            created_at=current_time,
            updated_at=current_time,
            metadata=request.metadata,
        )

        return batch.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/batches/{batch_id}")
async def get_message_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return MessageBatch(
            id=batch_id,
            processing_status=MessageBatchStatus.succeeded,
            request_counts={"total": 1, "completed": 1},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/batches/{batch_id}/results")
async def get_message_batch_results(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return MessageBatchResults(data=[]).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/batches")
async def list_message_batches(
    limit: int = 20, before_id: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    try:
        return MessageBatchList(data=[]).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/batches/{batch_id}/cancel")
async def cancel_message_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return MessageBatch(
            id=batch_id,
            processing_status=MessageBatchStatus.canceling,
            request_counts={"total": 1},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            cancel_initiated_at=datetime.now().isoformat(),
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages/batches/{batch_id}")
async def delete_message_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return {"id": batch_id, "deleted": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files")
async def create_file(
    file: UploadFile = File(...),
    purpose: FilePurpose = FilePurpose.vision,
    metadata: Optional[str] = Form(None),
):
    try:
        file_id = str(uuid.uuid4())
        file_content = await file.read()

        metadata_dict = {}
        if metadata:
            metadata_dict = json.loads(metadata)

        file_upload = FileUpload(
            id=file_id,
            purpose=purpose,
            filename=file.filename,
            bytes=len(file_content),
            created_at=int(datetime.now().timestamp()),
            content_type=file.content_type,
            content=(
                file_content.decode("utf-8", errors="ignore") if file_content else None
            ),
            metadata=metadata_dict,
        )

        return file_upload.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_files(
    limit: int = 20,
    purpose: Optional[FilePurpose] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        return FileList(data=[]).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}")
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return FileUpload(
            id=file_id,
            purpose=FilePurpose.vision,
            filename="example.jpg",
            bytes=1024,
            created_at=int(datetime.now().timestamp()),
            content_type="image/jpeg",
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/content")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_db)):
    try:
        file_upload = FileUpload(
            id=file_id,
            purpose=FilePurpose.vision,
            filename="example.jpg",
            bytes=1024,
            created_at=int(datetime.now().timestamp()),
            content_type="image/jpeg",
            content="file content here",
        )

        from fastapi.responses import Response

        return Response(
            content=file_upload.content.encode() if file_upload.content else b"",
            media_type=file_upload.content_type or "application/octet-stream",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return {"id": file_id, "deleted": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
