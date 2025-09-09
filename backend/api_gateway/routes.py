from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging
from typing import Dict, List
import asyncio

from .models import (
    InterviewInitializeRequest, InterviewStartRequest, InterviewStartResponse,
    AnswerSubmissionRequest, TranscriptionResponse, 
    FollowUpRequest, FollowUpResponse,
    JSONWorkflowRequest, JSONWorkflowResponse,
    UnifiedInputRequest, UnifiedInputResponse,
    InterviewStatusResponse, InterviewCompletionResponse,
    InterviewReportRequest, InterviewReportResponse,
    ErrorResponse, InterviewQuestion,
    WebSocketMessage, ErrorMessage, StatusMessage
)
from .websocket_manager import connection_manager
from core.utils import InterviewSession, ResponseFormatter, task_manager
from core.config import settings

logger = logging.getLogger(__name__)

# AI Coordinator will be accessed from app state
def get_ai_coordinator(request):
    """Get AI Coordinator from app state"""
    return request.app.state.ai_coordinator

router = APIRouter()

# Store active interview sessions - now shared with WebSocket connection manager
# This ensures HTTP API and WebSocket API use the same session storage
def get_active_sessions():
    """Get active session storage, shared with WebSocket manager"""
    return connection_manager.interview_sessions

active_sessions = get_active_sessions()

# Predefined interview questions
INTERVIEW_QUESTIONS = [
    {
        "id": 1,
        "question": "Please introduce yourself briefly, including your background, key experiences, and what you're looking for in your next role.",
        "type": "introduction",
        "category": "self_introduction"
    },
    {
        "id": 2,
        "question": "Tell me about a recent achievement you are most proud of. What role did you play?",
        "type": "behavioral",
        "category": "achievement"
    },
    {
        "id": 3,
        "question": "Describe a time when you overcame a conflict or challenge.",
        "type": "behavioral", 
        "category": "conflict_resolution"
    },
    {
        "id": 4,
        "question": "How do you approach joining a new team and integrating with existing team members?",
        "type": "behavioral",
        "category": "team_integration"
    }
]

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return ResponseFormatter.success_response({
        "service": "AI Interviewer API Gateway",
        "status": "healthy",
        "version": "1.0.0"
    })

@router.post("/interview/initialize")
async def initialize_interview_session(request: InterviewInitializeRequest):
    """Initialize interview session connection"""
    try:
        role = request.role
        timestamp = request.timestamp
        
        # Generate new Session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create new session (but don't start interview process)
        session = InterviewSession(session_id)
        session.role = role
        session.initialized_at = timestamp
        
        # Store session
        get_active_sessions()[session_id] = session
        
        logger.info(f"Initialized interview session: {session_id} for role: {role}")
        
        return ResponseFormatter.success_response({
            "session_id": session_id,
            "role": role,
            "status": "initialized",
            "message": f"Interview session initialized for {role}"
        })
        
    except Exception as e:
        logger.error(f"Failed to initialize interview session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize interview session: {str(e)}"
        )

@router.post("/interview/start", response_model=InterviewStartResponse)
async def start_interview(request: InterviewStartRequest):
    """Start new interview session"""
    try:
        # Create new session
        session = InterviewSession(request.session_id)
        # Use dynamic session storage to ensure sharing with WebSocket
        get_active_sessions()[session.session_id] = session
        
        logger.info(f"Started new interview session: {session.session_id}")
        
        # Return first question
        first_question = InterviewQuestion(**INTERVIEW_QUESTIONS[0])
        
        response = InterviewStartResponse(
            session_id=session.session_id,
            message="Interview session started successfully",
            first_question=first_question,
            total_questions=len(INTERVIEW_QUESTIONS)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to start interview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start interview session: {str(e)}"
        )

@router.get("/interview/{session_id}/status", response_model=InterviewStatusResponse)
async def get_interview_status(session_id: str):
    """Get interview session status"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return InterviewStatusResponse(
        session_id=session_id,
        current_question_index=session.current_question_index,
        total_questions=len(INTERVIEW_QUESTIONS),
        is_completed=session.is_completed,
        responses_count=len(session.user_responses),
        followups_count=len(session.followup_questions)
    )

@router.get("/interview/{session_id}/question")
async def get_current_question(session_id: str):
    """Get current question"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if session.current_question_index >= len(INTERVIEW_QUESTIONS):
        return ResponseFormatter.success_response({
            "message": "Interview completed",
            "is_completed": True
        })
    
    current_question = INTERVIEW_QUESTIONS[session.current_question_index]
    
    return ResponseFormatter.success_response({
        "question": current_question,
        "question_index": session.current_question_index,
        "remaining_questions": len(INTERVIEW_QUESTIONS) - session.current_question_index - 1
    })

@router.post("/interview/{session_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(session_id: str, file: UploadFile = File(...), request: Request = None):
    """Transcribe audio file"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    
    try:
        # Check file format
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported audio format. Supported: {settings.SUPPORTED_AUDIO_FORMATS}"
            )
        
        # Read file content
        content = await file.read()
        if len(content) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Call AI Backend's speech recognition module
        transcription_result = await ai_coordinator.transcribe_audio(
            content, file_extension, session_id
        )
        
        if not transcription_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {transcription_result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"Transcription completed for session {session_id}")
        
        return TranscriptionResponse(
            session_id=session_id,
            transcription=transcription_result["transcription"],
            confidence=transcription_result["confidence"],
            processing_time=transcription_result["processing_time"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

@router.post("/interview/{session_id}/submit-answer")
async def submit_answer(session_id: str, request: AnswerSubmissionRequest):
    """Submit user answer"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    try:
        # Get current question
        if session.current_question_index >= len(INTERVIEW_QUESTIONS):
            raise HTTPException(status_code=400, detail="No more questions available")
        
        current_question = INTERVIEW_QUESTIONS[session.current_question_index]
        
        # Record user answer
        session.add_response(
            question_id=current_question["id"],
            question=current_question["question"],
            answer=request.answer
        )
        
        logger.info(f"Answer submitted for session {session_id}, question {current_question['id']}")
        
        return ResponseFormatter.success_response({
            "message": "Answer submitted successfully",
            "question_id": current_question["id"],
            "next_step": "generate_followup"
        })
        
    except Exception as e:
        logger.error(f"Failed to submit answer for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit answer: {str(e)}"
        )

@router.post("/interview/{session_id}/process-unified", response_model=UnifiedInputResponse)
async def process_unified_input(session_id: str, unified_request: UnifiedInputRequest, request: Request):
    """
    Unified input processing endpoint: process text input, automatically route to planner and chatbot
    """
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    session = sessions[session_id]
    
    try:
        logger.info(f"Processing unified text input for session {session_id}")
        
        # Prepare input data
        input_data = {
            "text": unified_request.text,
            "context": unified_request.context or session.get_context(),
            "original_question": unified_request.original_question,
            "interview_style": unified_request.interview_style
        }
        
        # Call AI Coordinator's unified processing method
        result = await ai_coordinator.process_unified_input(
            input_data=input_data,
            session_id=session_id
        )
        
        if not result.get("success", True):
            raise HTTPException(
                status_code=500,
                detail=f"Unified processing failed: {result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"Unified processing completed for session {session_id}")
        
        # Record AI interaction in session
        session.add_ai_interaction(
            input_type=result["input_type"],
            user_input=result["user_input"],
            ai_response=result["ai_response"],
            processing_time=result.get("processing_time", 0.0),
            strategy_used=result.get("strategy_used", "unknown"),
            transcription_info=result.get("transcription_info")
        )
        
        return UnifiedInputResponse(
            session_id=session_id,
            input_type=result["input_type"],
            user_input=result["user_input"],
            ai_response=result["ai_response"],
            response_type=result.get("response_type", "question"),
            strategy_used=result.get("strategy_used", "unknown"),
            focus_area=result.get("focus_area", "general"),
            confidence=result.get("confidence", 0.5),
            processing_time=result.get("processing_time", 0.0),
            transcription_info=result.get("transcription_info")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified processing failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unified processing failed: {str(e)}"
        )

@router.post("/interview/{session_id}/process-unified-audio", response_model=UnifiedInputResponse)
async def process_unified_audio(
    session_id: str, 
    file: UploadFile = File(...), 
    context: str = None,
    original_question: str = None,
    interview_style: str = "formal",
    request: Request = None
):
    """
    Unified audio processing endpoint: process audio files, transcribe and route to planner and chatbot
    """
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    session = sessions[session_id]
    
    try:
        # Check file format
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported audio format. Supported: {settings.SUPPORTED_AUDIO_FORMATS}"
            )
        
        # Read file content
        content = await file.read()
        if len(content) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        logger.info(f"Processing unified audio input for session {session_id}")
        
        # Prepare input data
        input_data = {
            "audio_content": content,
            "audio_format": file_extension,
            "context": context or session.get_context(),
            "original_question": original_question,
            "interview_style": interview_style
        }
        
        # Call AI Coordinator's unified processing method
        result = await ai_coordinator.process_unified_input(
            input_data=input_data,
            session_id=session_id
        )
        
        if not result.get("success", True):
            raise HTTPException(
                status_code=500,
                detail=f"Unified audio processing failed: {result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"Unified audio processing completed for session {session_id}")
        
        # Record AI interaction in session
        session.add_ai_interaction(
            input_type=result["input_type"],
            user_input=result["user_input"],
            ai_response=result["ai_response"],
            processing_time=result.get("processing_time", 0.0),
            strategy_used=result.get("strategy_used", "unknown"),
            transcription_info=result.get("transcription_info")
        )
        
        return UnifiedInputResponse(
            session_id=session_id,
            input_type=result["input_type"],
            user_input=result["user_input"],
            ai_response=result["ai_response"],
            response_type=result.get("response_type", "question"),
            strategy_used=result.get("strategy_used", "unknown"),
            focus_area=result.get("focus_area", "general"),
            confidence=result.get("confidence", 0.5),
            processing_time=result.get("processing_time", 0.0),
            transcription_info=result.get("transcription_info")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified audio processing failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unified audio processing failed: {str(e)}"
        )

@router.post("/interview/{session_id}/process-json", response_model=JSONWorkflowResponse)
async def process_json_workflow(session_id: str, json_request: JSONWorkflowRequest, request: Request):
    """
    Process JSON workflow: receive JSON data containing user input and planner suggestions, generate response
    """
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    
    try:
        logger.info(f"Processing JSON workflow for session {session_id}")
        
        # Call AI Coordinator's JSON workflow processing
        result = await ai_coordinator.process_json_workflow(
            json_data=json_request.json_data,
            session_id=session_id
        )
        
        if not result.get("success", True):
            raise HTTPException(
                status_code=500,
                detail=f"JSON workflow failed: {result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"JSON workflow completed for session {session_id}")
        
        return JSONWorkflowResponse(
            session_id=session_id,
            response=result["question"],
            response_type=result.get("response_type", "question"),
            strategy_used=result.get("strategy_used", "unknown"),
            focus_area=result.get("focus_area", "general"),
            confidence=result.get("confidence", 0.5),
            processing_time=result.get("processing_time", 0.0),
            alternatives=result.get("alternatives", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON workflow failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"JSON workflow failed: {str(e)}"
        )

@router.post("/interview/{session_id}/generate-followup", response_model=FollowUpResponse)
async def generate_followup(session_id: str, followup_request: FollowUpRequest, request: Request):
    """Generate follow-up question"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    
    try:
        # Get current question information
        current_question = INTERVIEW_QUESTIONS[session.current_question_index]["question"]
        
        # Call AI Backend's chatbot and planning modules
        followup_result = await ai_coordinator.generate_followup_question(
            user_answer=followup_request.original_answer,
            original_question=current_question,
            conversation_context=session.get_context(),
            session_id=session_id,
            interview_style="formal"  # Can be obtained from session
        )
        
        if not followup_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Followup generation failed: {followup_result.get('error', 'Unknown error')}"
            )
        
        followup = followup_result["followup_question"]
        
        # Update last answer in session, add follow-up question
        if session.user_responses:
            session.user_responses[-1]["followup"] = followup
            session.followup_questions.append(followup)
        
        logger.info(f"Followup generated for session {session_id}: {followup[:50]}...")
        
        return FollowUpResponse(
            session_id=session_id,
            followup_question=followup,
            context_used=True,
            generation_time=followup_result["processing_time"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate followup for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate followup: {str(e)}"
        )

@router.post("/interview/{session_id}/next-question")
async def move_to_next_question(session_id: str):
    """Move to next question"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    try:
        session.next_question()
        
        # Check if there are more questions
        if session.current_question_index >= len(INTERVIEW_QUESTIONS):
            session.complete()
            return ResponseFormatter.success_response({
                "message": "Interview completed",
                "is_completed": True,
                "next_step": "show_completion"
            })
        
        # Return next question
        next_question = INTERVIEW_QUESTIONS[session.current_question_index]
        
        return ResponseFormatter.success_response({
            "question": next_question,
            "question_index": session.current_question_index,
            "remaining_questions": len(INTERVIEW_QUESTIONS) - session.current_question_index - 1,
            "next_step": "answer_question"
        })
        
    except Exception as e:
        logger.error(f"Failed to move to next question for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to move to next question: {str(e)}"
        )

@router.get("/interview/{session_id}/complete", response_model=InterviewCompletionResponse)
async def complete_interview(session_id: str):
    """Complete interview and return summary"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    session.complete()
    
    # Generate interview summary
    summary = {
        "questions_answered": len(session.user_responses),
        "followups_generated": len(session.followup_questions),
        "session_duration": str(datetime.now() - session.created_at),
        "responses": session.user_responses
    }
    
    # Note: No longer deleting session, maintain session memory until service shutdown
    # This ensures conversation memory is maintained throughout service lifecycle
    
    return InterviewCompletionResponse(
        session_id=session_id,
        message="Interview completed successfully",
        summary=summary,
        total_questions_answered=len(session.user_responses),
        total_followups_asked=len(session.followup_questions),
        session_duration=str(datetime.now() - session.created_at)
    )

@router.post("/interview/{session_id}/generate-report", response_model=InterviewReportResponse)
async def generate_interview_report(session_id: str, report_request: InterviewReportRequest, request: Request):
    """Generate interview report"""
    sessions = get_active_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get AI coordinator
    ai_coordinator = get_ai_coordinator(request)
    
    try:
        logger.info(f"Generating interview report for session {session_id}")
        
        # Call AI Coordinator to generate report
        report_result = await ai_coordinator.generate_interview_report(
            session_id=session_id,
            candidate_name=report_request.candidate_name
        )
        
        if not report_result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"Report generation failed: {report_result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"Interview report generated successfully for session {session_id}")
        
        return InterviewReportResponse(
            session_id=session_id,
            success=True,
            report=report_result["report"],
            generated_at=report_result["generated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate interview report for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate interview report: {str(e)}"
        )

# Error handling function (will be registered to FastAPI application in main.py)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseFormatter.error_response(
            error=exc.detail,
            code=exc.status_code
        )
    )

from datetime import datetime

# ==============================================================================
# WebSocket Routes for Real-time Communication
# ==============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint - main long-connection communication interface
    Supports real-time text and audio input processing
    """
    actual_session_id = None
    
    try:
        # Establish connection
        actual_session_id = await connection_manager.connect(websocket, session_id)
        logger.info(f"WebSocket connection established: {actual_session_id}")
        
        # Get AI coordinator (needs to be obtained from app state)
        ai_coordinator = websocket.app.state.ai_coordinator
        
        while True:
            try:
                # Receive message
                raw_message = await websocket.receive_text()
                
                # Process message
                response_message = await connection_manager.handle_message(
                    actual_session_id, raw_message, ai_coordinator
                )
                
                # Send response (if any)
                if response_message:
                    await connection_manager.send_message(actual_session_id, response_message)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {actual_session_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in WebSocket message loop for {actual_session_id}: {e}")
                
                # Send error message
                error_msg = ErrorMessage(
                    session_id=actual_session_id,
                    data={
                        "error": "message_processing_error",
                        "message": "An error occurred while processing your message",
                        "details": str(e) if settings.DEBUG else "Internal error"
                    }
                )
                
                try:
                    await connection_manager.send_message(actual_session_id, error_msg)
                except:
                    # If error message cannot be sent, connection may be broken
                    break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        
    finally:
        # Clean up connection
        if actual_session_id:
            await connection_manager.disconnect(actual_session_id, "connection_ended")

@router.websocket("/ws")
async def websocket_endpoint_auto_session(websocket: WebSocket):
    """
    WebSocket endpoint - automatically generate Session ID
    """
    return await websocket_endpoint(websocket, None)

# ==============================================================================
# WebSocket Management API Routes
# ==============================================================================

@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = connection_manager.get_connection_stats()
        return ResponseFormatter.success_response({
            "websocket_stats": stats.model_dump(),
            "active_sessions": connection_manager.get_active_sessions()
        })
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve WebSocket statistics")

@router.get("/websocket/sessions")
async def get_active_websocket_sessions():
    """Get all active WebSocket sessions"""
    try:
        active_sessions = connection_manager.get_active_sessions()
        session_details = []
        
        for session_id in active_sessions:
            session_info = connection_manager.get_session_info(session_id)
            if session_info:
                session_details.append({
                    "session_id": session_id,
                    "client_address": session_info.client_address,
                    "connected_at": session_info.connected_at.isoformat(),
                    "last_activity": session_info.last_activity.isoformat(),
                    "interview_style": session_info.interview_style,
                    "is_active": session_info.is_active
                })
        
        return ResponseFormatter.success_response({
            "active_sessions_count": len(active_sessions),
            "sessions": session_details
        })
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active sessions")

@router.get("/websocket/sessions/{session_id}")
async def get_websocket_session_info(session_id: str):
    """Get information for specified WebSocket session"""
    try:
        session_info = connection_manager.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get interview session information (if exists)
        interview_session = connection_manager.interview_sessions.get(session_id)
        interview_data = None
        
        if interview_session:
            interview_data = {
                "session_id": interview_session.session_id,
                "created_at": interview_session.created_at.isoformat(),
                "is_completed": interview_session.is_completed,
                "current_question_index": interview_session.current_question_index,
                "responses_count": len(interview_session.user_responses),
                "ai_interactions_count": len(interview_session.ai_interactions)
            }
        
        return ResponseFormatter.success_response({
            "connection_info": {
                "session_id": session_info.session_id,
                "client_address": session_info.client_address,
                "connected_at": session_info.connected_at.isoformat(),
                "last_activity": session_info.last_activity.isoformat(),
                "interview_style": session_info.interview_style,
                "is_active": session_info.is_active
            },
            "interview_session": interview_data,
            "is_websocket_active": connection_manager.is_session_active(session_id)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session information")

@router.post("/websocket/sessions/{session_id}/message")
async def send_message_to_websocket_session(session_id: str, message: Dict):
    """Send message to specified WebSocket session (management interface)"""
    try:
        if not connection_manager.is_session_active(session_id):
            raise HTTPException(status_code=404, detail="Session not active")
        
        # Create status message
        status_message = StatusMessage(
            session_id=session_id,
            data=message
        )
        
        success = await connection_manager.send_message(session_id, status_message)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message")
        
        return ResponseFormatter.success_response({
            "message": "Message sent successfully",
            "session_id": session_id,
            "message_type": "status"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.post("/websocket/broadcast")
async def broadcast_message_to_all_sessions(message: Dict, exclude_sessions: List[str] = None):
    """Broadcast message to all WebSocket sessions (management interface)"""
    try:
        # Create status message
        broadcast_message = StatusMessage(
            session_id="broadcast",
            data=message
        )
        
        exclude_set = set(exclude_sessions) if exclude_sessions else set()
        
        await connection_manager.broadcast_message(broadcast_message, exclude_set)
        
        active_sessions = connection_manager.get_active_sessions()
        target_sessions = [s for s in active_sessions if s not in exclude_set]
        
        return ResponseFormatter.success_response({
            "message": "Broadcast completed",
            "target_sessions_count": len(target_sessions),
            "excluded_sessions_count": len(exclude_set),
            "message_type": "status"
        })
        
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")