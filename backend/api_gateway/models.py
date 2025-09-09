from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
import base64

# Request Models
class InterviewInitializeRequest(BaseModel):
    role: str = Field(default="interviewee", description="User role: interviewer or interviewee")
    timestamp: Optional[str] = Field(None, description="Initialization timestamp")

class InterviewStartRequest(BaseModel):
    session_id: Optional[str] = None
    interview_style: str = Field(default="formal", description="Interview style: formal, casual, or campus")
    
class AnswerSubmissionRequest(BaseModel):
    question_id: int
    answer: str = Field(..., min_length=1, description="User's answer to the question")
    answer_type: str = Field(default="text", description="Type of answer: text or audio")
    
class AudioTranscriptionRequest(BaseModel):
    audio_format: str = Field(..., description="Audio file format (wav, mp3, etc.)")

class FollowUpRequest(BaseModel):
    question_id: int
    original_answer: str
    context: Optional[str] = None

class JSONWorkflowRequest(BaseModel):
    """JSON workflow request model"""
    json_data: Dict[str, Any] = Field(description="JSON data containing user input and planner suggestions")

class UnifiedInputRequest(BaseModel):
    """Unified input processing request model"""
    text: Optional[str] = Field(None, description="Text input")
    context: Optional[str] = Field(None, description="conversation context")
    original_question: Optional[str] = Field(None, description="original question")
    interview_style: str = Field(default="formal", description="interview style")
    
class UnifiedInputResponse(BaseModel):
    """Unified input processing response model"""
    session_id: str
    input_type: str = Field(description="Input type: text or audio")
    user_input: str = Field(description="User input text")
    ai_response: str = Field(description="AI generated response")
    response_type: str = Field(description="Response type")
    strategy_used: str = Field(description="Strategy used")
    focus_area: str = Field(description="Focus area")
    confidence: float = Field(description="Confidence score")
    processing_time: float = Field(description="Processing time")
    transcription_info: Optional[Dict[str, Any]] = Field(None, description="Transcription info (for audio input)")
    
class JSONWorkflowResponse(BaseModel):
    """JSON workflow response model"""
    session_id: str
    response: str = Field(description="Generated response")
    response_type: str = Field(description="Response type")
    strategy_used: str = Field(description="Strategy used")
    focus_area: str = Field(description="Focus area")
    confidence: float = Field(description="Confidence score")
    processing_time: float = Field(description="Processing time")
    alternatives: List[str] = Field(default_factory=list, description="Alternative responses")

# Response Models
class InterviewQuestion(BaseModel):
    id: int
    question: str
    type: str
    category: str = "behavioral"

class InterviewStartResponse(BaseModel):
    session_id: str
    message: str
    first_question: InterviewQuestion
    total_questions: int
    estimated_duration: str = "5 minutes"

class TranscriptionResponse(BaseModel):
    session_id: str
    transcription: str
    confidence: Optional[float] = None
    processing_time: Optional[float] = None

class FollowUpResponse(BaseModel):
    session_id: str
    followup_question: str
    context_used: bool
    generation_time: Optional[float] = None

class QuestionResponse(BaseModel):
    session_id: str
    question: InterviewQuestion
    question_index: int
    remaining_questions: int
    
class InterviewStatusResponse(BaseModel):
    session_id: str
    current_question_index: int
    total_questions: int
    is_completed: bool
    responses_count: int
    followups_count: int
    session_duration: Optional[str] = None

class InterviewCompletionResponse(BaseModel):
    session_id: str
    message: str
    summary: Dict[str, Any]
    total_questions_answered: int
    total_followups_asked: int
    session_duration: str

class InterviewReportRequest(BaseModel):
    """Interview report generation request"""
    candidate_name: str = Field(default="Anonymous", description="Candidate name")
    
class InterviewReportResponse(BaseModel):
    """Interview report response"""
    session_id: str
    success: bool
    report: Optional[Dict[str, Any]] = Field(None, description="Report content")
    error: Optional[str] = Field(None, description="Error message")
    generated_at: str

# Error Models
class ErrorResponse(BaseModel):
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Internal Models for AI Backend Communication
class AIProcessingRequest(BaseModel):
    """Internal model for AI backend processing"""
    session_id: str
    task_type: str  # "transcription", "followup", "planning"
    input_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    
class AIProcessingResponse(BaseModel):
    """Internal model for AI backend response"""
    session_id: str
    task_type: str
    result: Dict[str, Any]
    processing_time: float
    success: bool
    error_message: Optional[str] = None

# WebSocket Message Models
class WebSocketMessageType:
    """WebSocket message type constants"""
    # Client to Server
    CONNECT = "connect"
    TEXT_INPUT = "text_input"
    AUDIO_INPUT = "audio_input" 
    PING = "ping"
    DISCONNECT = "disconnect"
    
    # Server to Client
    CONNECTED = "connected"
    AI_RESPONSE = "ai_response"
    TRANSCRIPTION = "transcription"
    ERROR = "error"
    PONG = "pong"
    STATUS = "status"

class WebSocketMessage(BaseModel):
    """Base WebSocket message model"""
    type: str = Field(description="Message type")
    session_id: str = Field(description="Session identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")

class ConnectMessage(WebSocketMessage):
    """Connection establishment message"""
    type: Literal["connect"] = "connect"
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "interview_style": "formal",
        "client_info": {}
    })

class TextInputMessage(WebSocketMessage):
    """Text input message from client"""
    type: Literal["text_input"] = "text_input"
    data: Dict[str, Any] = Field(description="Text input data")
    
    def get_text(self) -> str:
        return self.data.get("text", "")
    
    def get_context(self) -> str:
        return self.data.get("context", "")

class AudioInputMessage(WebSocketMessage):
    """Audio input message from client"""
    type: Literal["audio_input"] = "audio_input"
    data: Dict[str, Any] = Field(description="Audio input data")
    
    def get_audio_data(self) -> bytes:
        """Decode base64 audio data"""
        audio_b64 = self.data.get("audio_data", "")
        try:
            return base64.b64decode(audio_b64)
        except Exception:
            return b""
    
    def get_audio_format(self) -> str:
        return self.data.get("audio_format", "wav")
    
    def get_context(self) -> str:
        return self.data.get("context", "")

class ConnectedMessage(WebSocketMessage):
    """Connection confirmation message"""
    type: Literal["connected"] = "connected"
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "status": "connected",
        "server_info": {"version": "2.0.0"}
    })

class AIResponseMessage(WebSocketMessage):
    """AI response message to client"""
    type: Literal["ai_response"] = "ai_response"
    data: Dict[str, Any] = Field(description="AI response data")

class TranscriptionMessage(WebSocketMessage):
    """Transcription result message"""
    type: Literal["transcription"] = "transcription"
    data: Dict[str, Any] = Field(description="Transcription data")

class ErrorMessage(WebSocketMessage):
    """Error message to client"""
    type: Literal["error"] = "error"
    data: Dict[str, Any] = Field(description="Error details")

class StatusMessage(WebSocketMessage):
    """Status update message"""
    type: Literal["status"] = "status"
    data: Dict[str, Any] = Field(description="Status information")

class PingMessage(WebSocketMessage):
    """Ping message for connection health"""
    type: Literal["ping"] = "ping"
    data: Dict[str, Any] = Field(default_factory=dict)

class PongMessage(WebSocketMessage):
    """Pong response message"""
    type: Literal["pong"] = "pong"
    data: Dict[str, Any] = Field(default_factory=dict)

# WebSocket Connection Models
class ConnectionInfo(BaseModel):
    """WebSocket connection information"""
    session_id: str
    client_address: str
    connected_at: datetime
    last_activity: datetime
    interview_style: str = "formal"
    is_active: bool = True
    
class ConnectionStats(BaseModel):
    """Connection statistics"""
    total_connections: int
    active_connections: int
    messages_sent: int
    messages_received: int
    errors_count: int
    uptime_seconds: float