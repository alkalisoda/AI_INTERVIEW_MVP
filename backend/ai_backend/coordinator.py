import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import os
import json

from core.config import settings
from core.utils import AudioFileHandler, ResponseFormatter, task_manager

# Import AI modules
from .speech_recognition.recognizer import SpeechRecognizer
from .planner.interview_planner import SimplifiedInterviewPlanner
from .chatbot.interviewer_bot import LangChainInterviewerBot
from .models import PlannerToChbotData, PlannerStrategy, ResponseQuality, InterviewStrategy

logger = logging.getLogger(__name__)

class AICoordinator:
    """
    AI Backend Coordinator - manages collaboration of three AI modules
    responsible for coordinating speech recognition, planning, and chatbot modules
    unified routing for text and audio input processing
    """
    
    def __init__(self):
        # Initialize three AI modules
        self.speech_recognizer = SpeechRecognizer()
        self.planner = SimplifiedInterviewPlanner()
        self.chatbot = LangChainInterviewerBot()
        
        # Set test data path
        self.test_data_path = Path(__file__).parent.parent / "tests" / "test_data"
        
        # Set reports data path
        self.reports_path = Path(__file__).parent.parent / "reports"
        
        # Processing status tracking
        self.active_tasks = {}
        
        # Supported audio formats
        self.supported_audio_formats = settings.SUPPORTED_AUDIO_FORMATS
        
        logger.info("AI Coordinator initialized with optimized modules and concurrent processing")
        logger.info(f"Test data path set to: {self.test_data_path}")
        logger.info(f"Supported audio formats: {self.supported_audio_formats}")
        
        # Interview status tracking
        self.interview_states = {}  # session_id -> {current_question_index, followup_count, questions}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all AI modules
        
        Returns:
            Dict: Health status of coordinator and all modules
        """
        try:
            logger.info("Performing AI Coordinator health check")
            
            health_status = {
                "coordinator_status": "healthy",
                "modules": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Check speech recognizer
            try:
                recognizer_health = await self.speech_recognizer.health_check()
                health_status["modules"]["speech_recognition"] = recognizer_health.get("status", "unknown")
            except Exception as e:
                logger.warning(f"Speech recognizer health check failed: {e}")
                health_status["modules"]["speech_recognition"] = "unhealthy"
            
            # Check planner
            try:
                # Basic initialization check
                if hasattr(self.planner, 'llm') and self.planner.llm:
                    health_status["modules"]["planner"] = "healthy"
                else:
                    health_status["modules"]["planner"] = "degraded"
            except Exception as e:
                logger.warning(f"Planner health check failed: {e}")
                health_status["modules"]["planner"] = "unhealthy"
            
            # Check chatbot
            try:
                # Basic initialization check
                if hasattr(self.chatbot, 'llm') and self.chatbot.llm:
                    health_status["modules"]["chatbot"] = "healthy"
                else:
                    health_status["modules"]["chatbot"] = "degraded"
            except Exception as e:
                logger.warning(f"Chatbot health check failed: {e}")
                health_status["modules"]["chatbot"] = "unhealthy"
            
            # Determine overall coordinator status
            unhealthy_modules = [k for k, v in health_status["modules"].items() if v == "unhealthy"]
            if unhealthy_modules:
                health_status["coordinator_status"] = "degraded"
                logger.warning(f"AI Coordinator degraded - unhealthy modules: {unhealthy_modules}")
            
            # Add system information
            health_status["system_info"] = {
                "active_sessions": len(self.interview_states),
                "supported_audio_formats": self.supported_audio_formats,
                "test_data_available": self.test_data_path.exists()
            }
            
            logger.info(f"AI Coordinator health check completed: {health_status['coordinator_status']}")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "coordinator_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def transcribe_audio(
        self,
        audio_content: bytes,
        audio_format: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Transcribe audio content (for API Gateway compatibility)
        
        Args:
            audio_content: Audio file content as bytes
            audio_format: Audio file format
            session_id: Session ID for logging
            
        Returns:
            Dict: Transcription result with success status and transcription text
        """
        try:
            start_time = datetime.now()
            
            # Call recognizer directly
            result = await self.speech_recognizer.transcribe_audio(
                audio_content=audio_content,
                audio_format=audio_format,
                session_id=session_id
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Return in expected format for API Gateway
            return {
                "success": True,
                "transcription": result.get("transcription", ""),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "language": result.get("language", "en"),
                "processing_time": processing_time
            }
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{session_id}] Audio transcription failed: {e}")
            return {
                "success": False,
                "transcription": "",
                "error": str(e),
                "processing_time": processing_time
            }
    
    async def transcribe_audio_direct(
        self,
        audio_content: bytes,
        file_format: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Direct audio transcription method (for process_unified_input compatibility)
        
        Args:
            audio_content: Audio file content as bytes
            file_format: Audio file format (e.g., 'webm', 'mp3', 'wav')
            session_id: Session ID for logging
            
        Returns:
            Dict: Transcription result with success status and text
        """
        try:
            # Call recognizer directly
            result = await self.speech_recognizer.transcribe_audio(
                audio_content=audio_content,
                audio_format=file_format,
                session_id=session_id
            )
            
            # Return unified format
            return {
                "success": True,
                "text": result.get("transcription", ""),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "language": result.get("language", "en"),
                "processing_time": result.get("processing_time", 0.0)
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] Direct audio transcription failed: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "processing_time": 0.0
            }
    
    async def process_interview_cycle(
        self,
        input_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Handle interview cycle: use nested loops to control follow-up count and question progress
        Outer loop: question list
        Inner loop: maximum 1 follow-up per question
        """
        try:
            start_time = datetime.now()
            
            # Initialize or get interview status
            if session_id not in self.interview_states:
                self.interview_states[session_id] = {
                    "current_question_index": 0,
                    "followup_count": 0,
                    "questions": input_data.get("questions", [])
                }
            
            state = self.interview_states[session_id]
            
            # Check if there are more questions
            if state["current_question_index"] >= len(state["questions"]):
                return {
                    "session_id": session_id,
                    "status": "interview_completed",
                    "message": "Interview completed",
                    "total_questions": len(state["questions"])
                }
            
            # 1. Speech to text (if needed)
            if input_data.get("audio_content"):
                transcription_result = await self.speech_recognizer.transcribe_audio(
                    audio_content=input_data["audio_content"],
                    audio_format=input_data.get("audio_format", "webm"),
                    session_id=session_id
                )
                user_text = transcription_result["transcription"]
                logger.info(f"[{session_id}] Transcribed audio: {user_text[:100]}...")
            elif input_data.get("text"):
                user_text = input_data["text"]
                transcription_result = None
                logger.info(f"[{session_id}] Processing text input: {user_text[:100]}...")
            else:
                raise ValueError("Input must contain either 'text' or audio data")
            
            # 2. Analyze answer quality
            current_question = state["questions"][state["current_question_index"]]
            analysis_result = await self.planner.analyze_answer(
                user_answer=user_text,
                original_question=current_question.get("question", ""),
                context=input_data.get("context", ""),
                session_id=session_id
            )
            
            # 3. Decide whether to follow up (based on loop control, max 1 time)
            if state["followup_count"] < 1 and analysis_result.get("needs_followup", False):
                # Continue follow-up
                state["followup_count"] += 1
                
                chatbot_result = await self.chatbot.generate_followup(
                    analysis=analysis_result,
                    user_answer=user_text,
                    context=input_data.get("context", ""),
                    style=input_data.get("interview_style", "formal"),
                    session_id=session_id
                )
                
                action = "followup"
                message = chatbot_result.get("followup_question", "")
                
            else:
                # Move to next question
                state["current_question_index"] += 1
                state["followup_count"] = 0
                
                if state["current_question_index"] < len(state["questions"]):
                    next_question = state["questions"][state["current_question_index"]]
                    action = "next_question"
                    message = next_question.get("question", "")
                else:
                    action = "interview_completed"
                    message = "Interview completed, thank you for your participation"
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "session_id": session_id,
                "action": action,
                "message": message,
                "current_question_index": state["current_question_index"],
                "followup_count": state["followup_count"],
                "total_questions": len(state["questions"]),
                "analysis_summary": {
                    "completeness_score": analysis_result.get("completeness_score", 0),
                    "specificity_score": analysis_result.get("specificity_score", 0),
                    "key_themes": analysis_result.get("key_themes", [])
                },
                "processing_time": processing_time,
                "transcription": transcription_result
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] Interview cycle processing failed: {e}")
            return {
                "session_id": session_id,
                "action": "error",
                "message": "Processing error, please retry",
                "error": str(e)
            }
    
    def reset_interview_session(self, session_id: str):
        """Reset interview session state including planner conversation memory"""
        if session_id in self.interview_states:
            del self.interview_states[session_id]
        
        # Also reset planner conversation memory
        self.planner.reset_session(session_id)
        
        logger.info(f"[{session_id}] Interview session state and conversation memory reset")
    
    def reset_followup_count(self, session_id: str):
        """Reset current question follow-up count for manual progression to next question"""
        if session_id in self.interview_states:
            self.interview_states[session_id]["followup_count"] = 0
            logger.info(f"[{session_id}] Followup count reset to 0")
        else:
            logger.warning(f"[{session_id}] No interview state found for followup reset")
    
    def get_interview_status(self, session_id: str) -> Dict[str, Any]:
        """Get interview status"""
        if session_id not in self.interview_states:
            return {"exists": False, "message": "No interview session found"}
        
        state = self.interview_states[session_id]
        return {
            "exists": True,
            "current_question_index": state["current_question_index"],
            "followup_count": state["followup_count"],
            "total_questions": len(state["questions"]),
            "progress": f"{state['current_question_index']}/{len(state['questions'])}",
            "conversation_count": len(self.planner.get_conversation_memory(session_id))
        }
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get complete conversation history"""
        return self.planner.get_conversation_memory(session_id)
    
    def _save_report_to_file(self, report_data: Dict[str, Any], candidate_name: str, session_id: str) -> Dict[str, str]:
        """
        Save interview report to files (JSON and Markdown)
        
        Args:
            report_data: Report data dictionary
            candidate_name: Candidate name for file naming
            session_id: Session ID
            
        Returns:
            Dict: File paths of saved reports
        """
        try:
            # Create date-based directory
            now = datetime.now()
            date_folder = now.strftime("%Y-%m-%d")
            time_stamp = now.strftime("%H-%M-%S")
            
            # Create directory structure
            date_dir = self.reports_path / date_folder
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean candidate name for filename
            safe_candidate_name = "".join(c for c in candidate_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_candidate_name = safe_candidate_name.replace(' ', '_')
            
            # Generate file names
            base_filename = f"{time_stamp}_{safe_candidate_name}_{session_id[:8]}"
            json_filename = f"{base_filename}_report.json"
            md_filename = f"{base_filename}_report.md"
            
            json_path = date_dir / json_filename
            md_path = date_dir / md_filename
            
            # Save JSON report
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Generate and save Markdown report
            md_content = self._generate_markdown_report(report_data)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"[{session_id}] Reports saved - JSON: {json_path}, Markdown: {md_path}")
            
            return {
                "json_path": str(json_path),
                "markdown_path": str(md_path),
                "date_folder": date_folder,
                "timestamp": time_stamp
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to save report files: {e}")
            return {
                "error": str(e),
                "json_path": "",
                "markdown_path": ""
            }

    def _generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """
        Generate human-readable Markdown report
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            str: Markdown formatted report
        """
        report = report_data.get("report", {})
        
        md_lines = [
            f"# Interview Report",
            f"",
            f"## Interview Information",
            f"- **Candidate**: {report.get('candidate_name', 'Anonymous')}",
            f"- **Session ID**: {report.get('session_id', 'Unknown')}",
            f"- **Date**: {report.get('interview_date', 'Unknown')}",
            f"- **Duration**: {report.get('duration_minutes', 0):.1f} minutes",
            f"- **Generated**: {report_data.get('generated_at', 'Unknown')}",
            f"",
            f"## Overall Assessment",
            f"- **Overall Score**: {report.get('overall_score', 0)}/10",
            f"- **Questions Answered**: {report.get('total_questions', 0)}",
            f"- **Follow-up Questions**: {report.get('followup_questions', 0)}",
            f"- **Average Response Quality**: {report.get('response_quality_avg', 0):.1f}/10",
            f"",
            f"### Overall Summary",
            f"{report.get('overall_summary', 'No summary available')}",
            f"",
            f"## Skills Assessment",
            f""
        ]
        
        # Add skill assessments
        for skill in report.get('skill_assessments', []):
            md_lines.extend([
                f"### {skill.get('skill_name', 'Unknown Skill')} ({skill.get('score', 0)}/10)",
                f"",
                f"**Evidence:**"
            ])
            for evidence in skill.get('evidence', []):
                md_lines.append(f"- {evidence}")
            
            md_lines.append(f"")
            md_lines.append(f"**Improvement Suggestions:**")
            for suggestion in skill.get('improvement_suggestions', []):
                md_lines.append(f"- {suggestion}")
            
            md_lines.append(f"")
        
        # Add strengths and areas for improvement
        md_lines.extend([
            f"## Strengths",
            f""
        ])
        for strength in report.get('strengths', []):
            md_lines.append(f"- {strength}")
        
        md_lines.extend([
            f"",
            f"## Areas for Improvement",
            f""
        ])
        for area in report.get('areas_for_improvement', []):
            md_lines.append(f"- {area}")
        
        # Add behavioral insights
        md_lines.extend([
            f"",
            f"## Behavioral Insights",
            f""
        ])
        for insight in report.get('behavioral_insights', []):
            md_lines.append(f"- {insight}")
        
        # Add hiring recommendation
        md_lines.extend([
            f"",
            f"## Hiring Recommendation",
            f"**Decision**: {report.get('hiring_recommendation', 'neutral').replace('_', ' ').title()}",
            f"",
            f"**Next Steps:**"
        ])
        for step in report.get('next_steps', []):
            md_lines.append(f"- {step}")
        
        # Add question performance
        md_lines.extend([
            f"",
            f"## Question Performance Analysis",
            f""
        ])
        
        for i, performance in enumerate(report.get('question_performance', []), 1):
            md_lines.extend([
                f"### Question {i}",
                f"**Question**: {performance.get('question', 'Unknown')}",
                f"**Performance Score**: {performance.get('score', 0)}/10",
                f"**Analysis**: {performance.get('analysis', 'No analysis available')}",
                f""
            ])
        
        md_lines.extend([
            f"",
            f"---",
            f"*This report was automatically generated by the AI Interview System*"
        ])
        
        return "\n".join(md_lines)

    async def generate_interview_report(
        self,
        session_id: str,
        candidate_name: str = "Anonymous"
    ) -> Dict[str, Any]:
        """
        Generate and save interview report to files
        
        Args:
            session_id: Session ID
            candidate_name: Candidate name
            
        Returns:
            Dict: Interview report data with file paths
        """
        try:
            logger.info(f"[{session_id}] Generating interview report for {candidate_name}")
            
            # Check interview status
            if session_id not in self.interview_states:
                raise ValueError("No interview session found")
            
            state = self.interview_states[session_id]
            
            # Calculate interview duration (simplified version, estimated based on interaction count)
            estimated_duration = state.get("total_interactions", 0) * 1.5  # Assume 1.5 minutes per interaction
            
            # Call planner to generate report
            report = await task_manager.run_with_timeout(
                self.planner.generate_interview_report(
                    session_id=session_id,
                    interview_duration_minutes=estimated_duration,
                    candidate_name=candidate_name
                ),
                timeout=settings.FOLLOWUP_TIMEOUT * 2  # Report generation may take longer
            )
            
            # Prepare report data for saving
            report_data = {
                "success": True,
                "report": report.model_dump(),
                "generated_at": datetime.now().isoformat(),
                "session_id": session_id
            }
            
            # Save report to files
            file_paths = self._save_report_to_file(report_data, candidate_name, session_id)
            
            # Add file paths to response
            report_data.update({
                "files": file_paths
            })
            
            logger.info(f"[{session_id}] Interview report generated and saved successfully")
            
            return report_data
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to generate interview report: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "generated_at": datetime.now().isoformat(),
                "files": {
                    "error": str(e),
                    "json_path": "",
                    "markdown_path": ""
                }
            }

    async def process_unified_input(
        self,
        input_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Unified input processing method - includes follow-up control logic and question list traversal
        combines the original process_interview_cycle 's follow-up control and predefined question list
        
        Args:
            input_data: Input data, can contain:
                - text: direct text input
                - audio_content: audio file content (bytes)
                - audio_format: audio file format
                - context: conversation context
                - original_question: original question
                - interview_style: interview style
            session_id: Session ID
            
        Returns:
            Dict: unified processing result including follow-up control and question traversal
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"[{session_id}] Starting unified input processing with question progression")
            
            # Import predefined question list
            from api_gateway.routes import INTERVIEW_QUESTIONS
            
            # Initialize or get interview status
            if session_id not in self.interview_states:
                self.interview_states[session_id] = {
                    "current_question_index": 0,  # Current question index
                    "followup_count": 0,  # Current question follow-up count
                    "total_interactions": 0,  # Total interaction count
                    "questions": INTERVIEW_QUESTIONS  # Question list
                }
            
            state = self.interview_states[session_id]
            
            # Check if there are more questions
            if state["current_question_index"] >= len(INTERVIEW_QUESTIONS):
                return {
                    "session_id": session_id,
                    "input_type": "text",
                    "user_input": input_data.get("text", ""),
                    "ai_response": "Thank you for completing the interview! All questions have been covered.",
                    "response_type": "interview_completed",
                    "strategy_used": "completion",
                    "focus_area": "completion",
                    "confidence": 1.0,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "success": True,
                    "followup_count": 0,
                    "total_interactions": state["total_interactions"],
                    "should_followup": False,
                    "current_question_index": state["current_question_index"],
                    "total_questions": len(INTERVIEW_QUESTIONS),
                    "interview_completed": True
                }
            
            # 1. Determine input type and get text
            user_text = ""
            transcription_result = None
            
            if "audio_content" in input_data and "audio_format" in input_data:
                # Audio input - requires speech recognition first
                logger.info(f"[{session_id}] Processing audio input")
                
                transcription_result = await self.transcribe_audio_direct(
                    audio_content=input_data["audio_content"],
                    file_format=input_data["audio_format"],
                    session_id=session_id
                )
                
                if not transcription_result["success"]:
                    raise Exception(f"Audio transcription failed: {transcription_result.get('error', 'Unknown error')}")
                
                user_text = transcription_result["text"]
                logger.info(f"[{session_id}] Audio transcribed: {user_text[:100]}...")
                
            elif "text" in input_data:
                # Text input - use directly
                user_text = input_data["text"]
                logger.info(f"[{session_id}] Processing text input: {user_text[:100]}...")
                
            else:
                raise ValueError("Input must contain either 'text' or both 'audio_content' and 'audio_format'")
            
            # 2. Get current question
            current_question = INTERVIEW_QUESTIONS[state["current_question_index"]]
            current_question_text = current_question["question"]
            
            logger.info(f"[{session_id}] Processing answer for question {state['current_question_index'] + 1}/{len(INTERVIEW_QUESTIONS)}: {current_question_text[:50]}...")
            
            # 3. Use planner to analyze answer quality
            planning_result = await task_manager.run_with_timeout(
                self.planner.analyze_answer(
                    user_answer=user_text,
                    original_question=current_question_text,
                    context=input_data.get("context", ""),
                    session_id=session_id
                ),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            # 4. Decide whether to follow up (based on follow-up control logic)
            should_followup = False
            action_type = "next_question"  # Default behavior
            ai_response = ""
            
            # Check if should continue follow-up (maximum 1 time)
            if (state["followup_count"] < 1 and 
                planning_result.get("needs_followup", False)):
                # Continue follow-up for current question
                should_followup = True
                action_type = "followup"
                state["followup_count"] += 1
                logger.info(f"[{session_id}] Generating followup for question {state['current_question_index'] + 1}, count: {state['followup_count']}/1")
                
                # Generate follow-up
                chatbot_result = await task_manager.run_with_timeout(
                    self.chatbot.generate_followup(
                        analysis=planning_result,
                        user_answer=user_text,
                        context=input_data.get("context", ""),
                        style=input_data.get("interview_style", "formal"),
                        session_id=session_id
                    ),
                    timeout=settings.FOLLOWUP_TIMEOUT
                )
                ai_response = chatbot_result.get("followup_question", chatbot_result.get("question", ""))
                
            else:
                # Move to next question
                state["current_question_index"] += 1
                state["followup_count"] = 0  # Reset followup count
                
                if state["current_question_index"] < len(INTERVIEW_QUESTIONS):
                    # There is a next question
                    next_question = INTERVIEW_QUESTIONS[state["current_question_index"]]
                    ai_response = next_question["question"]
                    action_type = "next_question"
                    logger.info(f"[{session_id}] Moving to question {state['current_question_index'] + 1}/{len(INTERVIEW_QUESTIONS)}: {next_question['question'][:50]}...")
                else:
                    # Interview completed
                    ai_response = "Thank you for completing the interview! All questions have been covered."
                    action_type = "interview_completed"
                    logger.info(f"[{session_id}] Interview completed - all {len(INTERVIEW_QUESTIONS)} questions covered")
            
            # Increment total interactions
            state["total_interactions"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[{session_id}] Unified processing completed in {processing_time:.2f}s, action: {action_type}")
            
            # 5. Build unified response
            result = {
                "session_id": session_id,
                "input_type": "audio" if transcription_result else "text",
                "user_input": user_text,
                "ai_response": ai_response,
                "response_type": action_type,
                "strategy_used": planning_result.get("reasoning", "quality_analysis"),
                "focus_area": planning_result.get("suggested_focus", "general"),
                "confidence": chatbot_result.get("confidence", 0.7) if should_followup else 0.9,
                "processing_time": processing_time,
                "success": True,
                
                # Question progress info
                "current_question_index": state["current_question_index"],
                "total_questions": len(INTERVIEW_QUESTIONS),
                "interview_completed": state["current_question_index"] >= len(INTERVIEW_QUESTIONS),
                
                # Followup control info
                "followup_count": state["followup_count"],
                "total_interactions": state["total_interactions"],
                "should_followup": should_followup,
                
                # Analysis summary
                "analysis_summary": {
                    "completeness_score": planning_result.get("completeness_score", 0),
                    "specificity_score": planning_result.get("specificity_score", 0),
                    "key_themes": planning_result.get("key_themes", []),
                    "suggested_focus": planning_result.get("suggested_focus", "")
                }
            }
            
            # Add transcription info (if audio input)
            if transcription_result:
                result["transcription_info"] = {
                    "confidence": transcription_result.get("confidence", 0.0),
                    "duration": transcription_result.get("duration", 0.0),
                    "language": transcription_result.get("language", "en"),
                    "transcription_time": transcription_result.get("processing_time", 0.0)
                }
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{session_id}] Unified processing failed: {e}")
            
            return {
                "session_id": session_id,
                "input_type": "unknown",
                "user_input": "",
                "ai_response": "I apologize, but I encountered an issue processing your input. Could you please try again?",
                "response_type": "error_fallback",
                "strategy_used": "error_recovery",
                "focus_area": "general",
                "confidence": 0.1,
                "processing_time": processing_time,
                "success": False,
                "error": str(e),
                "followup_count": 0,
                "total_interactions": 0,
                "should_followup": False,
                "current_question_index": 0,
                "total_questions": 3,
                "interview_completed": False
            }