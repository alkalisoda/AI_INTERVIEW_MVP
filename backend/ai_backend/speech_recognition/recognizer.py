import openai
import logging
from typing import Dict, Any
import asyncio
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """
    Speech recognition module
    Responsible for converting audio files to text
    Uses OpenAI Whisper API as the main recognition engine
    """
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL_WHISPER
        logger.info(f"Speech Recognizer initialized with model: {self.model}")
    
    async def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file
        
        Args:
            file_path: Audio file path
            
        Returns:
            Dict containing transcription text and confidence information
        """
        try:
            logger.info(f"Starting transcription of file: {file_path}")
            
            # Verify file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Get file size
            file_size = Path(file_path).stat().st_size
            if file_size > settings.MAX_AUDIO_SIZE:
                raise ValueError(f"File too large: {file_size} bytes (max: {settings.MAX_AUDIO_SIZE})")
            
            # Call Whisper API
            with open(file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="en",  # English interview
                    response_format="verbose_json",  # Get detailed information
                    temperature=0.0  # More accurate transcription
                )
            
            # Process transcription results
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
        Transcribe with preprocessing
        Preprocess audio to improve recognition accuracy
        """
        try:
            # TODO: Add audio preprocessing steps
            # - Noise reduction
            # - Volume normalization
            # - Format conversion
            
            return await self.transcribe_file(file_path)
            
        except Exception as e:
            logger.error(f"Preprocessing transcription failed: {e}")
            raise
    
    async def batch_transcribe(self, file_paths: list) -> Dict[str, Dict[str, Any]]:
        """
        Batch transcribe multiple audio files
        """
        results = {}
        
        try:
            # Process multiple files concurrently
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
        Estimate transcription confidence
        Calculate confidence score based on Whisper API response
        """
        try:
            # Whisper API verbose_json format may include segment-level confidence
            if hasattr(transcript, 'segments') and transcript.segments:
                # Calculate average confidence across all segments
                confidences = []
                for segment in transcript.segments:
                    if hasattr(segment, 'avg_logprob'):
                        # Convert log probability to 0-1 confidence range
                        confidence = min(1.0, max(0.0, (segment.avg_logprob + 1.0)))
                        confidences.append(confidence)
                
                if confidences:
                    return sum(confidences) / len(confidences)
            
            # If no detailed info, estimate based on text quality
            text = transcript.text.strip()
            if not text:
                return 0.0
            
            # Simple heuristic evaluation
            confidence = 0.7  # Base confidence
            
            # Adjust based on text features
            if len(text) > 10:
                confidence += 0.1
            if any(char.isdigit() for char in text):
                confidence += 0.05
            if text.count('.') > 0:  # Complete sentences
                confidence += 0.1
            if text.isupper() or text.islower():  # All caps or lowercase may indicate errors
                confidence -= 0.2
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.warning(f"Confidence estimation failed: {e}")
            return 0.5  # Default medium confidence
    
    async def validate_audio_quality(self, file_path: str) -> Dict[str, Any]:
        """
        Validate audio quality
        Check if audio is suitable for transcription
        """
        try:
            file_path_obj = Path(file_path)
            
            # Basic file checks
            if not file_path_obj.exists():
                return {"valid": False, "reason": "File not found"}
            
            file_size = file_path_obj.stat().st_size
            if file_size < 1024:  # Less than 1KB
                return {"valid": False, "reason": "File too small"}
            
            if file_size > settings.MAX_AUDIO_SIZE:
                return {"valid": False, "reason": "File too large"}
            
            # Check file format
            file_extension = file_path_obj.suffix.lower().lstrip('.')
            if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
                return {
                    "valid": False, 
                    "reason": f"Unsupported format: {file_extension}"
                }
            
            # TODO: Add more detailed audio quality checks
            # - Audio duration
            # - Sample rate
            # - Bit rate
            # - Noise level
            
            return {
                "valid": True,
                "file_size": file_size,
                "format": file_extension
            }
            
        except Exception as e:
            logger.error(f"Audio quality validation failed: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    async def transcribe_audio(
        self,
        audio_content: bytes,
        audio_format: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes content
        
        Args:
            audio_content: Audio file content as bytes
            audio_format: Audio file format (e.g., 'webm', 'mp3', 'wav')
            session_id: Session ID for logging
            
        Returns:
            Dict containing transcription text and metadata
        """
        try:
            logger.info(f"[{session_id}] Starting audio transcription from bytes, format: {audio_format}")
            
            # Validate file size
            if len(audio_content) > settings.MAX_AUDIO_SIZE:
                raise ValueError(f"Audio content too large: {len(audio_content)} bytes (max: {settings.MAX_AUDIO_SIZE})")
            
            # Validate format
            if audio_format not in settings.SUPPORTED_AUDIO_FORMATS:
                raise ValueError(f"Unsupported audio format: {audio_format}")
            
            # Create a file-like object from bytes
            import io
            audio_file = io.BytesIO(audio_content)
            audio_file.name = f"audio.{audio_format}"  # Set filename for API
            
            # Call Whisper API
            transcript = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language="en",  # English interview
                response_format="verbose_json",  # Get detailed information
                temperature=0.0  # More accurate transcription
            )
            
            # Process transcription results
            result = {
                "transcription": transcript.text.strip(),
                "confidence": self._estimate_confidence(transcript),
                "duration": getattr(transcript, 'duration', 0.0),
                "language": getattr(transcript, 'language', 'en')
            }
            
            logger.info(f"[{session_id}] Transcription completed. Text length: {len(result['transcription'])} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"[{session_id}] Audio transcription failed: {e}")
            raise Exception(f"Speech recognition failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check
        Verify if speech recognition service is working properly
        """
        try:
            # Check OpenAI API connection
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "unhealthy",
                    "reason": "Missing OpenAI API key"
                }
            
            # TODO: Add actual API connection test
            # Use small test audio file to verify service availability
            
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