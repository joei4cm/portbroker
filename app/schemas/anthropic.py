from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ContentType(str, Enum):
    text = "text"
    image = "image"
    tool_use = "tool_use"
    tool_result = "tool_result"


class ToolChoiceType(str, Enum):
    auto = "auto"
    any = "any"
    tool = "tool"


class StopReason(str, Enum):
    end_turn = "end_turn"
    stop_sequence = "stop_sequence"
    max_tokens = "max_tokens"
    tool_use = "tool_use"


class MessageBatchStatus(str, Enum):
    in_progress = "in_progress"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"
    expired = "expired"
    canceling = "canceling"


class FilePurpose(str, Enum):
    vision = "vision"


class ModelType(str, Enum):
    claude_3_5_sonnet_20241022 = "claude-3-5-sonnet-20241022"
    claude_3_haiku_20240307 = "claude-3-haiku-20240307"
    claude_3_opus_20240229 = "claude-3-opus-20240229"


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageSource(BaseModel):
    type: Literal["base64"] = "base64"
    media_type: str
    data: str


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    source: ImageSource


class ToolInputSchema(BaseModel):
    type: str
    properties: Dict[str, Any]
    required: List[str]


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: ToolInputSchema


class ToolUseContent(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: Optional[bool] = None


class ContentBlock(BaseModel):
    model_config = {"extra": "allow"}
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, dict):
            content_type = v.get("type")
            if content_type == "text":
                return TextContent(**v)
            elif content_type == "image":
                return ImageContent(**v)
            elif content_type == "tool_use":
                return ToolUseContent(**v)
            elif content_type == "tool_result":
                return ToolResultContent(**v)
        return v


class AnthropicMessage(BaseModel):
    role: MessageRole
    content: Union[str, List[Union[TextContent, ImageContent, ToolResultContent]]]
    cache_control: Optional[Dict[str, Any]] = None


class AnthropicRequest(BaseModel):
    model: str
    max_tokens: int = Field(..., gt=0, le=8192)
    messages: List[AnthropicMessage]
    system: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    stop_sequences: Optional[List[str]] = Field(None, max_length=4)
    stream: Optional[bool] = False
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[ToolChoiceType, Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    betas: Optional[List[str]] = None


class AnthropicUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None


class AnthropicResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContent, ToolUseContent]]
    model: str
    stop_reason: Optional[StopReason] = None
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage


class AnthropicStreamEvent(BaseModel):
    type: str
    message: Optional[Dict[str, Any]] = None
    content_block: Optional[Dict[str, Any]] = None
    content_block_delta: Optional[Dict[str, Any]] = None
    message_start: Optional[Dict[str, Any]] = None
    message_delta: Optional[Dict[str, Any]] = None
    message_stop: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    index: Optional[int] = None
    delta: Optional[Dict[str, Any]] = None
    usage: Optional[AnthropicUsage] = None


class CountTokensRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    system: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[ToolChoiceType, Dict[str, Any]]] = None
    betas: Optional[List[str]] = None


class CountTokensResponse(BaseModel):
    input_tokens: int
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    type: str
    display_name: str
    max_tokens: int
    context_length: int
    supported_modalities: List[str]
    

class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelInfo]
    has_more: bool = False


class MessageBatchRequest(BaseModel):
    requests: List[AnthropicRequest]
    metadata: Optional[Dict[str, Any]] = None


class MessageBatch(BaseModel):
    id: str
    object: Literal["message_batch"] = "message_batch"
    processing_status: MessageBatchStatus
    request_counts: Dict[str, int]
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    cancel_initiated_at: Optional[str] = None
    results_url: Optional[str] = None


class MessageBatchResult(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContent, ToolUseContent]]
    model: str
    stop_reason: Optional[StopReason] = None
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage
    custom_id: Optional[str] = None


class MessageBatchResults(BaseModel):
    object: Literal["list"] = "list"
    data: List[MessageBatchResult]
    has_more: bool = False


class MessageBatchList(BaseModel):
    object: Literal["list"] = "list"
    data: List[MessageBatch]
    has_more: bool = False
    first_id: Optional[str] = None
    last_id: Optional[str] = None


class FileUpload(BaseModel):
    id: str
    object: Literal["file"] = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: FilePurpose
    content_type: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileList(BaseModel):
    object: Literal["list"] = "list"
    data: List[FileUpload]
    has_more: bool = False
    first_id: Optional[str] = None
    last_id: Optional[str] = None