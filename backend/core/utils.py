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
    """管理面试会话状态（增强版）"""
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.current_question_index = 0
        self.conversation_history = []
        self.user_responses = []
        self.followup_questions = []
        self.ai_interactions = []  # 记录所有AI交互
        self.is_completed = False
        self.interview_style = "formal"
        self.session_metadata = {}  # 存储额外的会话信息
        
    def add_response(self, question_id: int, question: str, answer: str, followup: str = None):
        """添加用户Answer和后续Question"""
        self.last_activity = datetime.now()
        
        response_data = {
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "followup": followup,
            "timestamp": datetime.now().isoformat(),
            "input_type": "text"  # 默认为文本，可以在调用时指定
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
        """记录AI交互"""
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
        """获取conversation context用于AI处理（增强版）"""
        context = ""
        
        # 使用最近的AI交互记录
        recent_interactions = self.ai_interactions[-max_interactions:]
        
        for interaction in recent_interactions:
            context += f"User: {interaction['user_input']}\n"
            context += f"AI: {interaction['ai_response']}\n\n"
        
        return context.strip()
    
    def get_full_context(self) -> Dict[str, Any]:
        """获取完整的会话上下文信息"""
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
        """更新会话元数据"""
        self.session_metadata[key] = value
        self.last_activity = datetime.now()
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否仍然活跃"""
        time_since_activity = datetime.now() - self.last_activity
        return time_since_activity.total_seconds() < (timeout_minutes * 60)
    
    def next_question(self):
        """移动到下一个Question"""
        self.current_question_index += 1
        self.last_activity = datetime.now()
    
    def complete(self):
        """标记面试完成"""
        self.is_completed = True
        self.last_activity = datetime.now()

class AudioFileHandler:
    """处理音频文件的临时存储和清理"""
    
    @staticmethod
    async def save_temp_audio(file_content: bytes, file_extension: str = "wav") -> str:
        """保存临时音频文件"""
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
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Temporary file cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup temporary file {file_path}: {e}")

class ResponseFormatter:
    """格式化API响应"""
    
    @staticmethod
    def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
        """成功响应格式"""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def error_response(error: str, code: int = 500, details: Any = None) -> Dict[str, Any]:
        """错误响应格式"""
        return {
            "status": "error",
            "message": error,
            "error_code": code,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

class AsyncTaskManager:
    """管理异步任务，专注于并发和性能优化"""
    
    def __init__(self):
        self.running_tasks = {}
        self._semaphore = asyncio.Semaphore(15)  # 增加并发数量限制
    
    async def run_with_timeout(self, coro, timeout: int = 30):
        """运行带超时的异步任务"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Task timed out after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"Task failed: {e}")
            raise
    
    async def run_concurrent(self, tasks: list, timeout: int = 30):
        """并发运行多个任务"""
        async with self._semaphore:
            try:
                # 使用asyncio.gather进行真正的并发执行
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
            except Exception as e:
                logger.error(f"Concurrent tasks failed: {e}")
                raise
    
    async def run_parallel_tasks(self, task_dict: dict, timeout: int = 30):
        """并行运行命名任务字典"""
        try:
            # 创建任务列表
            tasks = []
            task_names = []
            for name, coro in task_dict.items():
                tasks.append(asyncio.wait_for(coro, timeout=timeout))
                task_names.append(name)
            
            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 返回命名结果
            return dict(zip(task_names, results))
            
        except Exception as e:
            logger.error(f"Parallel tasks failed: {e}")
            raise

# Global instances
task_manager = AsyncTaskManager()