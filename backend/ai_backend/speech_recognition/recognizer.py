import openai
import logging
from typing import Dict, Any
import asyncio
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """
    语音识别模块
    负责将音频文件转换为文本
    使用OpenAI Whisper API作为主要识别引擎
    """
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL_WHISPER
        logger.info(f"Speech Recognizer initialized with model: {self.model}")
    
    async def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            Dict包含转录文本和置信度信息
        """
        try:
            logger.info(f"Starting transcription of file: {file_path}")
            
            # 验证文件存在
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # 获取文件大小
            file_size = Path(file_path).stat().st_size
            if file_size > settings.MAX_AUDIO_SIZE:
                raise ValueError(f"File too large: {file_size} bytes (max: {settings.MAX_AUDIO_SIZE})")
            
            # 调用Whisper API
            with open(file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="en",  # 英语面试
                    response_format="verbose_json",  # 获取详细信息
                    temperature=0.0  # 更准确的转录
                )
            
            # 处理转录结果
            result = {
                "text": transcript.text.strip(),
                "confidence": self._estimate_confidence(transcript),
                "duration": getattr(transcript, 'duration', 0.0),
                "language": getattr(transcript, 'language', 'en')
            }
            
            logger.info(f"Transcription completed. Text length: {len(result['text'])} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            raise Exception(f"Speech recognition failed: {str(e)}")
    
    async def transcribe_with_preprocessing(self, file_path: str) -> Dict[str, Any]:
        """
        带预处理的转录
        对音频进行预处理以提高识别准确性
        """
        try:
            # TODO: 可以添加音频预处理步骤
            # - 降噪
            # - 音量标准化
            # - 格式转换
            
            return await self.transcribe_file(file_path)
            
        except Exception as e:
            logger.error(f"Preprocessing transcription failed: {e}")
            raise
    
    async def batch_transcribe(self, file_paths: list) -> Dict[str, Dict[str, Any]]:
        """
        批量转录多个音频文件
        """
        results = {}
        
        try:
            # 并发处理多个文件
            tasks = [
                self.transcribe_file(file_path) 
                for file_path in file_paths
            ]
            
            transcription_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for file_path, result in zip(file_paths, transcription_results):
                if isinstance(result, Exception):
                    results[file_path] = {
                        "success": False,
                        "error": str(result)
                    }
                else:
                    results[file_path] = {
                        "success": True,
                        **result
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Batch transcription failed: {e}")
            raise
    
    def _estimate_confidence(self, transcript) -> float:
        """
        估算转录置信度
        基于Whisper API返回的信息估算置信度分数
        """
        try:
            # Whisper API的verbose_json格式可能包含段落级别的置信度
            if hasattr(transcript, 'segments') and transcript.segments:
                # 计算所有段落的平均置信度
                confidences = []
                for segment in transcript.segments:
                    if hasattr(segment, 'avg_logprob'):
                        # 将对数概率转换为0-1范围的置信度
                        confidence = min(1.0, max(0.0, (segment.avg_logprob + 1.0)))
                        confidences.append(confidence)
                
                if confidences:
                    return sum(confidences) / len(confidences)
            
            # 如果没有详细信息，根据文本质量估算
            text = transcript.text.strip()
            if not text:
                return 0.0
            
            # 简单的启发式评估
            confidence = 0.7  # 基础置信度
            
            # 根据文本特征调整
            if len(text) > 10:
                confidence += 0.1
            if any(char.isdigit() for char in text):
                confidence += 0.05
            if text.count('.') > 0:  # 完整句子
                confidence += 0.1
            if text.isupper() or text.islower():  # 全大写或全小写可能是错误
                confidence -= 0.2
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.warning(f"Confidence estimation failed: {e}")
            return 0.5  # 默认中等置信度
    
    async def validate_audio_quality(self, file_path: str) -> Dict[str, Any]:
        """
        验证音频质量
        检查音频是否适合转录
        """
        try:
            file_path_obj = Path(file_path)
            
            # 基本文件检查
            if not file_path_obj.exists():
                return {"valid": False, "reason": "File not found"}
            
            file_size = file_path_obj.stat().st_size
            if file_size < 1024:  # 小于1KB
                return {"valid": False, "reason": "File too small"}
            
            if file_size > settings.MAX_AUDIO_SIZE:
                return {"valid": False, "reason": "File too large"}
            
            # 检查文件格式
            file_extension = file_path_obj.suffix.lower().lstrip('.')
            if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
                return {
                    "valid": False, 
                    "reason": f"Unsupported format: {file_extension}"
                }
            
            # TODO: 可以添加更详细的音频质量检查
            # - 音频长度
            # - 采样率
            # - 比特率
            # - 噪声水平
            
            return {
                "valid": True,
                "file_size": file_size,
                "format": file_extension
            }
            
        except Exception as e:
            logger.error(f"Audio quality validation failed: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check
        验证语音识别服务是否正常工作
        """
        try:
            # 检查OpenAI API连接
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "unhealthy",
                    "reason": "Missing OpenAI API key"
                }
            
            # TODO: 可以添加实际的API连接测试
            # 使用小的测试音频文件验证服务可用性
            
            return {
                "status": "healthy",
                "model": self.model,
                "supported_formats": settings.SUPPORTED_AUDIO_FORMATS,
                "max_file_size": settings.MAX_AUDIO_SIZE
            }
            
        except Exception as e:
            logger.error(f"Speech recognizer health check failed: {e}")
            return {
                "status": "unhealthy",
                "reason": str(e)
            }