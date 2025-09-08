import asyncio
import tempfile
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterviewSession:
    """Manage interview session state (enhanced version)"""
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.current_question_index = 0
        self.conversation_history = []
        self.user_responses = []
        self.followup_questions = []
        self.ai_interactions = []  # Record all AI interactions
        self.is_completed = False
        self.interview_style = "formal"
        self.session_metadata = {}  # Store additional session information
        
    def add_response(self, question_id: int, question: str, answer: str, followup: str = None):
        """Add user answer and follow-up question"""
        self.last_activity = datetime.now()
        
        response_data = {
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "followup": followup,
            "timestamp": datetime.now().isoformat(),
            "input_type": "text"  # Default to text, can be specified when calling
        }
        self.user_responses.append(response_data)
        
        # Update conversation history for AI context
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        if followup:
            self.followup_questions.append({
                "question": followup,
                "timestamp": datetime.now().isoformat()
            })
    
    def add_ai_interaction(self, input_type: str, user_input: str, ai_response: str, 
                          processing_time: float, strategy_used: str = "unknown",
                          transcription_info: Dict = None):
        """Record AI interaction"""
        self.last_activity = datetime.now()
        
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "input_type": input_type,
            "user_input": user_input,
            "ai_response": ai_response,
            "processing_time": processing_time,
            "strategy_used": strategy_used
        }
        
        if transcription_info:
            interaction["transcription_info"] = transcription_info
            
        self.ai_interactions.append(interaction)
    
    def get_context(self, max_interactions: int = 3) -> str:
        """Get conversation context for AI processing (enhanced version)"""
        context = ""
        
        # Use recent AI interaction records
        recent_interactions = self.ai_interactions[-max_interactions:]
        
        for interaction in recent_interactions:
            context += f"User: {interaction['user_input']}\n"
            context += f"AI: {interaction['ai_response']}\n\n"
        
        return context.strip()
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get complete session context information"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "duration": str(datetime.now() - self.created_at),
            "total_interactions": len(self.ai_interactions),
            "current_question_index": self.current_question_index,
            "interview_style": self.interview_style,
            "is_completed": self.is_completed,
            "recent_context": self.get_context(),
            "session_metadata": self.session_metadata
        }
    
    def update_metadata(self, key: str, value: Any):
        """Update session metadata"""
        self.session_metadata[key] = value
        self.last_activity = datetime.now()
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if session is still active"""
        time_since_activity = datetime.now() - self.last_activity
        return time_since_activity.total_seconds() < (timeout_minutes * 60)
    
    def next_question(self):
        """Move to next question"""
        self.current_question_index += 1
        self.last_activity = datetime.now()
    
    def complete(self):
        """Mark interview as completed"""
        self.is_completed = True
        self.last_activity = datetime.now()

class AudioFileHandler:
    """Handle temporary storage and cleanup of audio files"""
    
    @staticmethod
    async def save_temp_audio(file_content: bytes, file_extension: str = "wav") -> str:
        """Save temporary audio file"""
        try:
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f'.{file_extension}'
            )
            temp_file.write(file_content)
            temp_file.flush()
            temp_file.close()
            
            logger.info(f"Temporary audio file saved: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to save temporary audio file: {e}")
            raise
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Temporary file cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup temporary file {file_path}: {e}")

class ResponseFormatter:
    """Format API responses"""
    
    @staticmethod
    def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
        """Success response format"""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def error_response(error: str, code: int = 500, details: Any = None) -> Dict[str, Any]:
        """Error response format"""
        return {
            "status": "error",
            "message": error,
            "error_code": code,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

class AsyncTaskManager:
    """Manage async tasks, focused on concurrency and performance optimization"""
    
    def __init__(self):
        self.running_tasks = {}
        self._semaphore = asyncio.Semaphore(15)  # Increase concurrency limit
    
    async def run_with_timeout(self, coro, timeout: int = 30):
        """Run async task with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Task timed out after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"Task failed: {e}")
            raise
    
    async def run_concurrent(self, tasks: list, timeout: int = 30):
        """Run multiple tasks concurrently"""
        async with self._semaphore:
            try:
                # Use asyncio.gather for true concurrent execution
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
            except Exception as e:
                logger.error(f"Concurrent tasks failed: {e}")
                raise
    
    async def run_parallel_tasks(self, task_dict: dict, timeout: int = 30):
        """Run named task dictionary in parallel"""
        try:
            # Create task list
            tasks = []
            task_names = []
            for name, coro in task_dict.items():
                tasks.append(asyncio.wait_for(coro, timeout=timeout))
                task_names.append(name)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Return named results
            return dict(zip(task_names, results))
            
        except Exception as e:
            logger.error(f"Parallel tasks failed: {e}")
            raise

# Global instances
task_manager = AsyncTaskManager()