import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_api_key
from app.core.database import get_db
from app.models.strategy import Provider
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
from app.services.strategy_service import StrategyService
from app.schemas.strategy import ModelMappingRequest

# Configure logging
logger = logging.getLogger(__name__)


async def get_provider_for_model(db: AsyncSession, model: str, strategy_type: str = "openai") -> Provider:
    """Get the appropriate provider for a model using strategy service"""
    try:
        logger.info(f"=== MODEL MAPPING DEBUG ===")
        logger.info(f"Requested model: {model}")
        logger.info(f"Strategy type: {strategy_type}")
        
        # Use strategy service to map the model
        mapping_request = ModelMappingRequest(
            requested_model=model,
            strategy_type=strategy_type
        )
        
        logger.info(f"Mapping request: {mapping_request}")
        
        mapping_response = await StrategyService.map_model(db, mapping_request)
        
        logger.info(f"Mapping response: {mapping_response}")
        
        # Get the provider from the mapping response
        provider = await ProviderService.get_provider_by_id(db, mapping_response.provider_id)
        if not provider:
            raise Exception(f"Provider not found for ID: {mapping_response.provider_id}")
        
        # Update the requested model with the mapped model
        logger.info(f"Model mapping: {model} -> {mapping_response.mapped_model} (Provider: {provider.name})")
        
        return provider, mapping_response.mapped_model
        
    except Exception as e:
        logger.error(f"Strategy mapping failed for model {model}: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        # Fallback to old behavior
        providers = await ProviderService.get_active_providers(db)
        if not providers:
            raise Exception("No active providers available")
        
        # Use the first provider and try to map the model
        provider = providers[0]
        mapped_model = model  # Use the requested model as-is
        
        logger.info(f"Fallback mapping: {model} -> {mapped_model} (Provider: {provider.name})")
        return provider, mapped_model

router = APIRouter()


async def stream_response(response: httpx.Response) -> AsyncGenerator[str, None]:
    total_chunks = 0
    total_characters = 0
    
    logger.info("=== STREAMING RESPONSE START ===")
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response headers: {dict(response.headers)}")
    
    try:
        async for chunk in response.aiter_text():
            total_chunks += 1
            chunk_length = len(chunk)
            total_characters += chunk_length
            
            logger.info(f"=== CHUNK {total_chunks} ===")
            logger.info(f"Chunk length: {chunk_length} characters")
            logger.info(f"Chunk content: {repr(chunk)}")
            
            if chunk.strip():
                # Check if chunk already starts with 'data: ' or is a proper SSE chunk
                if chunk.strip().startswith('data: ') or chunk.strip().startswith('event: '):
                    yield chunk
                else:
                    formatted_chunk = f"data: {chunk}\n\n"
                    logger.info(f"Formatted chunk: {repr(formatted_chunk)}")
                    yield formatted_chunk
            else:
                logger.info("Empty chunk received")
    except Exception as e:
        logger.error(f"=== STREAMING ERROR ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Total chunks before error: {total_chunks}")
        logger.error(f"Total characters before error: {total_characters}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        logger.info("=== STREAMING RESPONSE END ===")
        logger.info(f"Total chunks processed: {total_chunks}")
        logger.info(f"Total characters processed: {total_characters}")
        yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    fastapi_request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: dict = Depends(get_current_api_key),
):
    try:
        print(f"=== CHAT COMPLETION REQUEST ===")
        print(f"Request model: {request.model}")
        print(f"Request messages: {request.messages}")
        print(f"Request temperature: {request.temperature}")
        print(f"Request max_tokens: {request.max_tokens}")
        
        # Use strategy-based model mapping
        provider, mapped_model = await get_provider_for_model(db, request.model, "openai")
        
        # Update request with mapped model
        original_model = request.model
        request.model = mapped_model
        
        # Store provider and model info in FastAPI request state for tracking
        if fastapi_request:
            fastapi_request.state.provider_info = {
                "id": provider.id,
                "name": provider.name
            }
            fastapi_request.state.model_info = {
                "requested": original_model,
                "actual": mapped_model,
                "tier": "strategy"
            }
        
        if request.stream:
            # Use the specific provider for streaming
            streaming_info = await ProviderService.call_provider_api(
                provider, request, stream=True
            )
            
            if isinstance(streaming_info, dict) and streaming_info.get("stream"):
                # Create the actual streaming response
                stream_provider = streaming_info["provider"]
                headers = streaming_info["headers"]
                request_data = streaming_info["request_data"]
                
                async def generate_stream():
                    total_chunks = 0
                    total_characters = 0
                    
                    logger.info("=== STREAMING GENERATOR START ===")
                    logger.info(f"Provider: {stream_provider.name} (ID: {stream_provider.id})")
                    logger.info(f"Request URL: {stream_provider.base_url.rstrip('/')}/chat/completions")
                    
                    try:
                        async with httpx.AsyncClient(
                            timeout=300.0, verify=stream_provider.verify_ssl
                        ) as client:
                            logger.info("=== SENDING STREAMING REQUEST TO PROVIDER ===")
                            async with client.stream(
                                "POST",
                                f"{stream_provider.base_url.rstrip('/')}/chat/completions",
                                headers=headers,
                                json=request_data,
                            ) as response:
                                logger.info(f"=== STREAMING RESPONSE RECEIVED ===")
                                logger.info(f"Response status: {response.status_code}")
                                logger.info(f"Response headers: {dict(response.headers)}")
                                
                                # Buffer for handling incomplete SSE events
                                buffer = ""
                                
                                async for chunk in response.aiter_text():
                                    total_chunks += 1
                                    chunk_length = len(chunk)
                                    total_characters += chunk_length
                                    
                                    logger.info(f"=== CHUNK {total_chunks} ===")
                                    logger.info(f"Chunk length: {chunk_length} characters")
                                    logger.info(f"Raw chunk content: {repr(chunk)}")
                                    
                                    if chunk.strip():
                                        # Add chunk to buffer
                                        buffer += chunk
                                        
                                        # Process complete SSE events from buffer
                                        # SSE events are separated by \n\n
                                        while '\n\n' in buffer:
                                            # Split at the first \n\n
                                            event_end = buffer.find('\n\n')
                                            event_text = buffer[:event_end]
                                            buffer = buffer[event_end + 2:]  # Remove the event and \n\n
                                            
                                            if event_text.strip():
                                                logger.info(f"Yielding SSE event: {repr(event_text)}")
                                                yield f"{event_text}\n\n"
                                    else:
                                        logger.info("Empty chunk received, skipping")
                            
                                # Process any remaining data in buffer
                                if buffer.strip():
                                    logger.info(f"Yielding final SSE event: {repr(buffer)}")
                                    yield f"{buffer}\n\n"
                    except Exception as e:
                        logger.error(f"=== STREAMING GENERATOR ERROR ===")
                        logger.error(f"Error: {str(e)}")
                        logger.error(f"Total chunks before error: {total_chunks}")
                        logger.error(f"Total characters before error: {total_characters}")
                        error_chunk = f"data: {json.dumps({'error': str(e)})}\n\n"
                        logger.error(f"Yielding error chunk: {repr(error_chunk)}")
                        yield error_chunk
                    finally:
                        logger.info("=== STREAMING GENERATOR END ===")
                        logger.info(f"Total chunks processed: {total_chunks}")
                        logger.info(f"Total characters processed: {total_characters}")
                        done_chunk = "data: [DONE]\n\n"
                        logger.info(f"Yielding DONE chunk: {repr(done_chunk)}")
                        yield done_chunk
                
                return StreamingResponse(
                    generate_stream(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )
            else:
                raise HTTPException(
                    status_code=500, detail="Invalid streaming response"
                )
        else:
            # Use the specific provider for non-streaming
            response_data = await ProviderService.call_provider_api(
                provider, request, stream=False
            )
            return response_data

    except Exception as e:
        logger.error(f"=== CHAT COMPLETION ERROR ===")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
