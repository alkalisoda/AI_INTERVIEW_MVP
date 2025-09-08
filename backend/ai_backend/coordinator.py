import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import os

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
        
        # Processing status tracking
        self.active_tasks = {}
        
        # Supported audio formats
        self.supported_audio_formats = settings.SUPPORTED_AUDIO_FORMATS
        
        logger.info("AI Coordinator initialized with optimized modules and concurrent processing")
        logger.info(f"Test data path set to: {self.test_data_path}")
        logger.info(f"Supported audio formats: {self.supported_audio_formats}")
        
        # Interview status tracking
        self.interview_states = {}  # session_id -> {current_question_index, followup_count, questions}
    
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
                    message = "Interview completed，感谢您的参与"
            
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
    
    async def generate_interview_report(
        self,
        session_id: str,
        candidate_name: str = "Anonymous"
    ) -> Dict[str, Any]:
        """
        Generate interview report
        
        Args:
            session_id: Session ID
            candidate_name: Candidate name
            
        Returns:
            Dict: Interview report data
        """
        try:
            logger.info(f"[{session_id}] Generating interview report for {candidate_name}")
            
            # 检查面试状态
            if session_id not in self.interview_states:
                raise ValueError("No interview session found")
            
            state = self.interview_states[session_id]
            
            # 计算面试时长（简化版，基于交互次数估算）
            estimated_duration = state.get("total_interactions", 0) * 1.5  # 假设每次交互1.5分钟
            
            # 调用planner生成报告
            report = await task_manager.run_with_timeout(
                self.planner.generate_interview_report(
                    session_id=session_id,
                    interview_duration_minutes=estimated_duration,
                    candidate_name=candidate_name
                ),
                timeout=settings.FOLLOWUP_TIMEOUT * 2  # 报告生成可能需要更长时间
            )
            
            logger.info(f"[{session_id}] Interview report generated successfully")
            
            return {
                "success": True,
                "report": report.model_dump(),
                "generated_at": datetime.now().isoformat(),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to generate interview report: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "generated_at": datetime.now().isoformat()
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
            input_data: 输入数据，可以包含:
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
            
            # 导入预定义Question列表
            from api_gateway.routes import INTERVIEW_QUESTIONS
            
            # Initialize or get interview status
            if session_id not in self.interview_states:
                self.interview_states[session_id] = {
                    "current_question_index": 0,  # 当前Question索引
                    "followup_count": 0,  # 当前Question的追问次数
                    "total_interactions": 0,  # 总交互次数
                    "questions": INTERVIEW_QUESTIONS  # Question列表
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
            
            # 1. 判断输入类型并获取文本
            user_text = ""
            transcription_result = None
            
            if "audio_content" in input_data and "audio_format" in input_data:
                # 音频输入 - 需要先进行语音识别
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
                # 文本输入 - 直接使用
                user_text = input_data["text"]
                logger.info(f"[{session_id}] Processing text input: {user_text[:100]}...")
                
            else:
                raise ValueError("Input must contain either 'text' or both 'audio_content' and 'audio_format'")
            
            # 2. 获取当前Question
            current_question = INTERVIEW_QUESTIONS[state["current_question_index"]]
            current_question_text = current_question["question"]
            
            logger.info(f"[{session_id}] Processing answer for question {state['current_question_index'] + 1}/{len(INTERVIEW_QUESTIONS)}: {current_question_text[:50]}...")
            
            # 3. 使用plannerAnalyze answer quality
            planning_result = await task_manager.run_with_timeout(
                self.planner.analyze_answer(
                    user_answer=user_text,
                    original_question=current_question_text,
                    context=input_data.get("context", ""),
                    session_id=session_id
                ),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            # 4. 决定是否追问（基于追问控制逻辑）
            should_followup = False
            action_type = "next_question"  # 默认行为
            ai_response = ""
            
            # 检查是否应该Continue follow-up（最多1次）
            if (state["followup_count"] < 1 and 
                planning_result.get("needs_followup", False)):
                # Continue follow-up当前Question
                should_followup = True
                action_type = "followup"
                state["followup_count"] += 1
                logger.info(f"[{session_id}] Generating followup for question {state['current_question_index'] + 1}, count: {state['followup_count']}/1")
                
                # 生成追问
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
                # 移动到下一个Question
                state["current_question_index"] += 1
                state["followup_count"] = 0  # 重置追问计数
                
                if state["current_question_index"] < len(INTERVIEW_QUESTIONS):
                    # 还有下一个Question
                    next_question = INTERVIEW_QUESTIONS[state["current_question_index"]]
                    ai_response = next_question["question"]
                    action_type = "next_question"
                    logger.info(f"[{session_id}] Moving to question {state['current_question_index'] + 1}/{len(INTERVIEW_QUESTIONS)}: {next_question['question'][:50]}...")
                else:
                    # 面试完成
                    ai_response = "Thank you for completing the interview! All questions have been covered."
                    action_type = "interview_completed"
                    logger.info(f"[{session_id}] Interview completed - all {len(INTERVIEW_QUESTIONS)} questions covered")
            
            # 增加总交互次数
            state["total_interactions"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[{session_id}] Unified processing completed in {processing_time:.2f}s, action: {action_type}")
            
            # 5. 构建统一的响应
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
                
                # Question进度信息
                "current_question_index": state["current_question_index"],
                "total_questions": len(INTERVIEW_QUESTIONS),
                "interview_completed": state["current_question_index"] >= len(INTERVIEW_QUESTIONS),
                
                # 追问控制信息
                "followup_count": state["followup_count"],
                "total_interactions": state["total_interactions"],
                "should_followup": should_followup,
                
                # 分析摘要
                "analysis_summary": {
                    "completeness_score": planning_result.get("completeness_score", 0),
                    "specificity_score": planning_result.get("specificity_score", 0),
                    "key_themes": planning_result.get("key_themes", []),
                    "suggested_focus": planning_result.get("suggested_focus", "")
                }
            }
            
            # 添加转录相关信息（如果是音频输入）
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

    async def transcribe_audio_direct(
        self,
        audio_content: bytes,
        file_format: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Direct audio transcription (optimized)- process directly without saving to disk
        
        Args:
            audio_content: audio file content
            file_format: 音频格式
            session_id: Session ID
            
        Returns:
            Dict: 转录结果
        """
        start_time = datetime.now()
        temp_file_path = None
        
        try:
            logger.info(f"[{session_id}] Starting direct audio transcription")
            
            # 验证音频格式
            if file_format.lower() not in self.supported_audio_formats:
                raise ValueError(f"Unsupported audio format: {file_format}. Supported: {self.supported_audio_formats}")
            
            # 验证文件大小
            if len(audio_content) > settings.MAX_AUDIO_SIZE:
                raise ValueError(f"Audio file too large: {len(audio_content)} bytes. Max: {settings.MAX_AUDIO_SIZE} bytes")
            
            # 创建临时文件（目前仍需要，因为Whisper API需要文件路径）
            temp_file_path = await AudioFileHandler.save_temp_audio(
                audio_content, file_format
            )
            
            # 调用语音识别
            transcription_result = await task_manager.run_with_timeout(
                self.speech_recognizer.transcribe_file(temp_file_path),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[{session_id}] Direct audio transcription completed in {processing_time:.2f}s")
            
            return {
                "text": transcription_result["text"],
                "confidence": transcription_result.get("confidence", 0.0),
                "duration": transcription_result.get("duration", 0.0),
                "language": transcription_result.get("language", "en"),
                "processing_time": processing_time,
                "success": True
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{session_id}] Direct audio transcription failed: {e}")
            
            return {
                "text": "",
                "confidence": 0.0,
                "duration": 0.0,
                "language": "en",
                "processing_time": processing_time,
                "success": False,
                "error": str(e)
            }
            
        finally:
            # 清理临时文件
            if temp_file_path:
                AudioFileHandler.cleanup_temp_file(temp_file_path)
    
    async def transcribe_audio(self, audio_content: bytes, file_format: str, session_id: str) -> Dict[str, Any]:
        """
        音频转录流程
        1. 保存临时文件
        2. 调用语音识别模块
        3. 清理临时文件
        """
        start_time = datetime.now()
        temp_file_path = None
        
        try:
            logger.info(f"Starting audio transcription for session {session_id}")
            
            # 1. 保存临时音频文件
            temp_file_path = await AudioFileHandler.save_temp_audio(
                audio_content, file_format
            )
            
            # 2. 调用语音识别模块进行转录
            transcription_result = await task_manager.run_with_timeout(
                self.speech_recognizer.transcribe_file(temp_file_path),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Audio transcription completed for session {session_id} in {processing_time:.2f}s")
            
            return {
                "transcription": transcription_result["text"],
                "confidence": transcription_result.get("confidence", 0.0),
                "processing_time": processing_time,
                "success": True
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Audio transcription failed for session {session_id}: {e}")
            
            return {
                "transcription": "",
                "confidence": 0.0,
                "processing_time": processing_time,
                "success": False,
                "error": str(e)
            }
            
        finally:
            # 3. 清理临时文件
            if temp_file_path:
                AudioFileHandler.cleanup_temp_file(temp_file_path)
    
    async def transcribe_test_audio(self, test_file_name: str, session_id: str = "test") -> Dict[str, Any]:
        """
        测试专用：直接从测试数据路径转录音频文件
        
        Args:
            test_file_name: 测试文件名 (例如: "1A.m4a", "2B.m4a")
            session_id: Session ID，默认为"test"
            
        Returns:
            Dict包含转录结果和相关信息
        """
        start_time = datetime.now()
        
        try:
            # 构建测试文件的完整路径
            test_file_path = self.test_data_path / test_file_name
            
            # 检查文件是否存在
            if not test_file_path.exists():
                available_files = list(self.test_data_path.glob("*.m4a"))
                raise FileNotFoundError(
                    f"Test file {test_file_name} not found. Available files: {[f.name for f in available_files]}"
                )
            
            logger.info(f"Starting test audio transcription: {test_file_path}")
            
            # 调用语音识别模块进行转录
            transcription_result = await task_manager.run_with_timeout(
                self.speech_recognizer.transcribe_file(str(test_file_path)),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Test audio transcription completed in {processing_time:.2f}s")
            logger.info(f"Transcribed text: {transcription_result['text'][:100]}...")
            
            return {
                "test_file": test_file_name,
                "file_path": str(test_file_path),
                "transcription": transcription_result["text"],
                "confidence": transcription_result.get("confidence", 0.0),
                "duration": transcription_result.get("duration", 0.0),
                "language": transcription_result.get("language", "en"),
                "processing_time": processing_time,
                "success": True
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Test audio transcription failed for {test_file_name}: {e}")
            
            return {
                "test_file": test_file_name,
                "file_path": str(self.test_data_path / test_file_name) if hasattr(self, 'test_data_path') else "unknown",
                "transcription": "",
                "confidence": 0.0,
                "duration": 0.0,
                "language": "en",
                "processing_time": processing_time,
                "success": False,
                "error": str(e)
            }
    
    async def batch_transcribe_test_files(self, file_names: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        批量转录测试文件
        
        Args:
            file_names: 要转录的文件名列表，如果为None则转录所有测试文件
            
        Returns:
            Dict[文件名, 转录结果]
        """
        try:
            # 如果没有指定文件名，则获取所有测试文件
            if file_names is None:
                test_files = list(self.test_data_path.glob("*.m4a"))
                file_names = [f.name for f in test_files]
                logger.info(f"Found {len(file_names)} test files: {file_names}")
            
            # 并发处理所有文件
            logger.info(f"Starting batch transcription of {len(file_names)} files")
            
            tasks = [
                self.transcribe_test_audio(file_name, f"test_batch_{i}")
                for i, file_name in enumerate(file_names)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 整理结果
            batch_results = {}
            for file_name, result in zip(file_names, results):
                if isinstance(result, Exception):
                    batch_results[file_name] = {
                        "success": False,
                        "error": str(result),
                        "transcription": "",
                        "confidence": 0.0
                    }
                else:
                    batch_results[file_name] = result
            
            # 统计结果
            successful = sum(1 for r in batch_results.values() if r.get("success", False))
            logger.info(f"Batch transcription completed: {successful}/{len(file_names)} successful")
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Batch transcription failed: {e}")
            return {}
    
    async def process_json_workflow(
        self,
        json_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        处理JSON工作流：接收包含用户输入和planner建议的JSON数据
        
        Args:
            json_data: 包含user_input和planner_suggestion的JSON数据
            session_id: Session ID
            
        Returns:
            Dict: 包含chatbot回复的结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"[{session_id}] Starting JSON workflow processing")
            
            # 直接调用chatbot的JSON处理方法
            chatbot_result = await task_manager.run_with_timeout(
                self.chatbot.process_json_input(json_data),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[{session_id}] JSON workflow completed in {processing_time:.2f}s")
            
            return {
                **chatbot_result,
                "processing_time": processing_time,
                "workflow_type": "json_integrated"
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{session_id}] JSON workflow failed: {e}")
            
            return {
                "question": "I'd like to understand more about your experience. Could you share additional details?",
                "response_type": "question",
                "strategy_used": "deep_dive",
                "focus_area": "general",
                "alternatives": [],
                "generation_method": "json_workflow_fallback",
                "confidence": 0.3,
                "processing_time": processing_time,
                "success": False,
                "error": str(e),
                "workflow_type": "json_integrated"
            }

    async def generate_response_from_planner_data(
        self,
        user_input: str,
        planner_suggestion: Dict[str, Any],
        conversation_context: str = "",
        original_question: str = "",
        interview_style: str = "formal",
        session_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        根据planner数据生成回复的便捷方法
        
        Args:
            user_input: 用户输入
            planner_suggestion: planner的建议数据
            conversation_context: conversation context
            original_question: original question
            interview_style: interview style
            session_id: Session ID
            
        Returns:
            Dict: 包含生成回复的结果
        """
        try:
            # 构造JSON数据
            json_data = {
                "user_input": user_input,
                "planner_suggestion": planner_suggestion,
                "conversation_context": conversation_context,
                "original_question": original_question,
                "interview_style": interview_style,
                "session_id": session_id
            }
            
            # 调用JSON工作流
            return await self.process_json_workflow(json_data, session_id)
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to generate response from planner data: {e}")
            return {
                "question": "Can you tell me more about that?",
                "success": False,
                "error": str(e)
            }

    async def generate_followup_question(
        self, 
        user_answer: str, 
        original_question: str,
        conversation_context: str,
        session_id: str,
        interview_style: str = "formal"
    ) -> Dict[str, Any]:
        """
        生成后续Question流程（优化版 - 并发处理）
        1. 使用规划模块分析用户答案和上下文
        2. 使用对话机器人生成合适的后续Question
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting optimized followup generation for session {session_id}")
            
            # 1. 使用规划模块Analyze answer quality
            planning_result = await task_manager.run_with_timeout(
                self.planner.analyze_answer(
                    user_answer=user_answer,
                    original_question=original_question,
                    context=conversation_context,
                    session_id=session_id
                ),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            # 2. 使用对话机器人生成后续Question
            chatbot_result = await task_manager.run_with_timeout(
                self.chatbot.generate_followup(
                    analysis=planning_result,
                    user_answer=user_answer,
                    context=conversation_context,
                    style=interview_style
                ),
                timeout=settings.FOLLOWUP_TIMEOUT
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Optimized followup generation completed for session {session_id} in {processing_time:.2f}s")
            
            return {
                "followup_question": chatbot_result.get("followup_question", chatbot_result.get("question", "")),
                "reasoning": planning_result.get("reasoning", ""),
                "focus_area": planning_result.get("suggested_focus", "general"),
                "processing_time": processing_time,
                "success": True
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Followup generation failed for session {session_id}: {e}")
            
            # 回退到基本后续Question
            fallback_question = await self._generate_fallback_followup(user_answer)
            
            return {
                "followup_question": fallback_question,
                "reasoning": "Fallback due to processing error",
                "focus_area": "general",
                "processing_time": processing_time,
                "success": False,
                "error": str(e)
            }
    
    async def evaluate_interview_progress(
        self, 
        conversation_history: list,
        session_id: str
    ) -> Dict[str, Any]:
        """
        评估面试进度
        使用规划模块分析整体面试表现
        """
        try:
            logger.info(f"Evaluating interview progress for session {session_id}")
            
            # 简化评估逻辑
            total_questions = len(conversation_history)
            if total_questions == 0:
                evaluation = {
                    "overall_score": 0,
                    "feedback": "No conversation history available"
                }
            else:
                # 基于对话数量给出基本评分
                evaluation = {
                    "overall_score": min(total_questions * 2, 8),  # 最高8分
                    "feedback": f"Completed {total_questions} interview interactions",
                    "total_interactions": total_questions
                }
            
            return {
                "evaluation": evaluation,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Interview evaluation failed for session {session_id}: {e}")
            return {
                "evaluation": {"score": 0, "feedback": "Evaluation failed"},
                "success": False,
                "error": str(e)
            }
    
    async def _generate_fallback_followup(self, user_answer: str) -> str:
        """生成回退后续Question"""
        fallback_questions = [
            "Can you tell me more about that experience?",
            "What was the most challenging aspect of that situation?", 
            "How did that experience change your approach to similar situations?",
            "What would you do differently if you faced a similar situation again?",
            "Can you provide more specific details about your role in that situation?"
        ]
        
        # 简单的启发式选择
        if len(user_answer) < 50:
            return "Can you provide more details about that experience?"
        elif "challenge" in user_answer.lower():
            return "What was the most difficult part of overcoming that challenge?"
        elif "team" in user_answer.lower():
            return "How did you work with your team members in that situation?"
        else:
            return fallback_questions[0]
    
    async def health_check(self) -> Dict[str, Any]:
        """检查所有AI模块的健康状态"""
        try:
            speech_health = await self.speech_recognizer.health_check()
            planner_health = await self.planner.health_check()
            chatbot_health = await self.chatbot.health_check()
            
            all_healthy = all([
                speech_health.get("status") == "healthy",
                planner_health.get("status") == "healthy", 
                chatbot_health.get("status") == "healthy"
            ])
            
            return {
                "coordinator_status": "healthy" if all_healthy else "degraded",
                "modules": {
                    "speech_recognition": speech_health,
                    "planner": planner_health,
                    "chatbot": chatbot_health
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "coordinator_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_multiple_sessions_concurrent(
        self, 
        session_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        并发处理多个会话请求（性能优化版）
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing {len(session_requests)} sessions concurrently")
            
            # 创建并发任务
            tasks = {}
            for i, request in enumerate(session_requests):
                session_id = request.get("session_id", f"concurrent_{i}")
                request_type = request.get("type", "followup")
                
                if request_type == "followup":
                    tasks[session_id] = self.generate_followup_question(
                        user_answer=request["user_answer"],
                        original_question=request["original_question"],
                        conversation_context=request.get("conversation_context", ""),
                        session_id=session_id,
                        interview_style=request.get("interview_style", "formal")
                    )
                elif request_type == "json_workflow":
                    tasks[session_id] = self.process_json_workflow(
                        json_data=request["json_data"],
                        session_id=session_id
                    )
            
            # 并发执行所有任务
            results = await task_manager.run_parallel_tasks(
                tasks, 
                timeout=settings.FOLLOWUP_TIMEOUT * 2
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 统计成功和失败的数量
            successful = sum(1 for result in results.values() 
                           if not isinstance(result, Exception) and result.get("success", True))
            failed = len(results) - successful
            
            logger.info(f"Concurrent processing completed: {successful} successful, {failed} failed in {processing_time:.2f}s")
            
            return {
                "results": results,
                "summary": {
                    "total_sessions": len(session_requests),
                    "successful": successful,
                    "failed": failed,
                    "processing_time": processing_time
                },
                "success": True
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Concurrent session processing failed: {e}")
            
            return {
                "results": {},
                "summary": {
                    "total_sessions": len(session_requests),
                    "successful": 0,
                    "failed": len(session_requests),
                    "processing_time": processing_time
                },
                "success": False,
                "error": str(e)
            }