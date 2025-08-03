import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_api_key
from app.core.database import get_db
from app.schemas.openai import (
    Batch,
    BatchRequest,
    ChatCompletionRequest,
    EmbeddingRequest,
    FileDeleteResponse,
    FilePurpose,
    FileUpload,
    Model,
    ModerationRequest,
    ModerationResponse,
)
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
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    try:
        if request.stream:
            response = await ProviderService.try_providers_until_success(
                db, request, stream=True
            )
            if isinstance(response, httpx.Response):
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )
            else:
                raise HTTPException(
                    status_code=500, detail="Invalid streaming response"
                )
        else:
            response_data = await ProviderService.try_providers_until_success(
                db, request, stream=False
            )
            return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_db), api_key: dict = Depends(get_current_api_key)
):
    try:
        providers = await ProviderService.get_active_providers(db)

        models = []
        for provider in providers:
            if provider.small_model:
                models.append(
                    Model(
                        id=provider.small_model,
                        created=int(datetime.now().timestamp()),
                        owned_by=provider.name,
                    )
                )
            if provider.medium_model:
                models.append(
                    Model(
                        id=provider.medium_model,
                        created=int(datetime.now().timestamp()),
                        owned_by=provider.name,
                    )
                )
            if provider.big_model:
                models.append(
                    Model(
                        id=provider.big_model,
                        created=int(datetime.now().timestamp()),
                        owned_by=provider.name,
                    )
                )

        return {"object": "list", "data": models}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    try:
        providers = await ProviderService.get_active_providers(db)

        for provider in providers:
            if model_id in [
                provider.small_model,
                provider.medium_model,
                provider.big_model,
            ]:
                return Model(
                    id=model_id,
                    created=int(datetime.now().timestamp()),
                    owned_by=provider.name,
                ).model_dump()

        raise HTTPException(status_code=404, detail="Model not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings")
async def create_embeddings(
    request: EmbeddingRequest, db: AsyncSession = Depends(get_db)
):
    try:
        return {
            "object": "list",
            "data": [{"object": "embedding", "embedding": [0.1] * 1536, "index": 0}],
            "model": request.model,
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moderations")
async def create_moderations(
    request: ModerationRequest, db: AsyncSession = Depends(get_db)
):
    try:
        inputs = request.input if isinstance(request.input, list) else [request.input]

        results = []
        for input_text in inputs:
            results.append(
                {
                    "flagged": False,
                    "categories": {
                        "sexual": False,
                        "hate": False,
                        "harassment": False,
                        "self-harm": False,
                        "sexual/minors": False,
                        "hate/threatening": False,
                        "violence/graphic": False,
                        "self-harm/intent": False,
                        "self-harm/instructions": False,
                        "harassment/threatening": False,
                        "violence": False,
                    },
                    "category_scores": {
                        "sexual": 0.01,
                        "hate": 0.01,
                        "harassment": 0.01,
                        "self-harm": 0.01,
                        "sexual/minors": 0.01,
                        "hate/threatening": 0.01,
                        "violence/graphic": 0.01,
                        "self-harm/intent": 0.01,
                        "self-harm/instructions": 0.01,
                        "harassment/threatening": 0.01,
                        "violence": 0.01,
                    },
                }
            )

        return ModerationResponse(
            id=str(uuid.uuid4()), model=request.model, results=results
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files")
async def create_file(
    file: UploadFile = File(...),
    purpose: FilePurpose = FilePurpose.vision,
    db: AsyncSession = Depends(get_db),
):
    try:
        file_id = str(uuid.uuid4())
        file_content = await file.read()

        file_upload = FileUpload(
            id=file_id,
            bytes=len(file_content),
            created_at=int(datetime.now().timestamp()),
            filename=file.filename,
            purpose=purpose,
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
        return {"object": "list", "data": []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}")
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return FileUpload(
            id=file_id,
            bytes=1024,
            created_at=int(datetime.now().timestamp()),
            filename="example.txt",
            purpose=FilePurpose.batch,
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return FileDeleteResponse(id=file_id, deleted=True).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batches")
async def create_batch(request: BatchRequest, db: AsyncSession = Depends(get_db)):
    try:
        batch_id = str(uuid.uuid4())
        current_time = int(datetime.now().timestamp())

        batch = Batch(
            id=batch_id,
            endpoint=request.endpoint,
            input_file_id=request.input_file_id,
            completion_window=request.completion_window,
            status="validating",
            created_at=current_time,
            metadata=request.metadata,
        )

        return batch.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return Batch(
            id=batch_id,
            endpoint="/v1/chat/completions",
            input_file_id="file_abc123",
            completion_window="24h",
            status="completed",
            created_at=int(datetime.now().timestamp()),
            completed_at=int(datetime.now().timestamp()),
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches")
async def list_batches(
    limit: int = 20, after: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    try:
        return {"object": "list", "data": [], "has_more": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return Batch(
            id=batch_id,
            endpoint="/v1/chat/completions",
            input_file_id="file_abc123",
            completion_window="24h",
            status="cancelling",
            created_at=int(datetime.now().timestamp()),
            cancelling_at=int(datetime.now().timestamp()),
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
