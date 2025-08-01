from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum


class FilePurpose(str, Enum):
    """Purpose of a file upload"""
    vision = "vision"
    batch = "batch"
    fine_tune = "fine_tune"
    assistants = "assistants"


class ModerationCategory(str, Enum):
    """Content moderation categories"""
    sexual = "sexual"
    hate = "hate"
    harassment = "harassment"
    self_harm = "self-harm"
    sexual_minors = "sexual/minors"
    hate_threatening = "hate/threatening"
    violence_graphic = "violence/graphic"
    self_harm_intent = "self-harm/intent"
    self_harm_instructions = "self-harm/instructions"
    harassment_threatening = "harassment/threatening"
    violence = "violence"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, List[Dict[str, Any]]]
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    n: Optional[int] = 1
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str]
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    system_fingerprint: Optional[str] = None


class ChatCompletionStreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]
    system_fingerprint: Optional[str] = None


class Model(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str
    permission: Optional[List[Dict[str, Any]]] = None
    root: Optional[str] = None
    parent: Optional[str] = None


class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str], List[int], List[List[int]]]
    encoding_format: Optional[Literal["float", "base64"]] = "float"
    dimensions: Optional[int] = None
    user: Optional[str] = None


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: EmbeddingUsage


class ModerationRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = "text-moderation-latest"


class ModerationResult(BaseModel):
    flagged: bool
    categories: Dict[str, bool]
    category_scores: Dict[str, float]


class ModerationResponse(BaseModel):
    id: str
    model: str
    results: List[ModerationResult]


class FileUpload(BaseModel):
    id: str
    object: str = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: FilePurpose
    status: Optional[str] = None
    status_details: Optional[Dict[str, Any]] = None


class FileDeleteResponse(BaseModel):
    id: str
    object: str = "file"
    deleted: bool


class BatchStatus(str, Enum):
    validating = "validating"
    failed = "failed"
    in_progress = "in_progress"
    finalizing = "finalizing"
    completed = "completed"
    expired = "expired"
    cancelling = "cancelling"
    cancelled = "cancelled"


class BatchRequest(BaseModel):
    input_file_id: str
    endpoint: str
    completion_window: str
    metadata: Optional[Dict[str, Any]] = None


class Batch(BaseModel):
    id: str
    object: str = "batch"
    endpoint: str
    errors: Optional[Dict[str, Any]] = None
    input_file_id: str
    completion_window: str
    status: BatchStatus
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None
    created_at: int
    in_progress_at: Optional[int] = None
    expires_at: Optional[int] = None
    finalizing_at: Optional[int] = None
    completed_at: Optional[int] = None
    failed_at: Optional[int] = None
    expiring_at: Optional[int] = None
    cancelling_at: Optional[int] = None
    cancelled_at: Optional[int] = None
    request_counts: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None