"""
LangChain configuration and shared tools
Provides unified LangChain settings for planner and chatbot modules
"""

import os
import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema.runnable import RunnableConfig
from core.config import settings

logger = logging.getLogger(__name__)

class InterviewCallbackHandler(BaseCallbackHandler):
    """Interview-specific callback handler for recording and monitoring LangChain calls"""
    
    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.start_time = None
        self.token_usage = {}
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts, **kwargs):
        """Callback when LLM starts calling"""
        import time
        self.start_time = time.time()
        logger.info(f"[{self.session_id}] LLM call started")
    
    def on_llm_end(self, response, **kwargs):
        """Callback when LLM call ends"""
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(f"[{self.session_id}] LLM call completed in {duration:.2f}s")
            
        # Record token usage
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            if token_usage:
                self.token_usage = token_usage
                logger.info(f"[{self.session_id}] Token usage: {token_usage}")
    
    def on_llm_error(self, error: Exception, **kwargs):
        """Callback when LLM call errors"""
        logger.error(f"[{self.session_id}] LLM error: {error}")

class LangChainManager:
    """LangChain manager providing unified LLM configuration and tools"""
    
    def __init__(self):
        # Pre-create commonly used LLM instances for better performance
        self._llm_instances = {}
        self._default_llm = self._create_llm()
        self._analysis_llm = self._create_llm(temperature=0.3, max_tokens=1500)  # For analysis
        self._generation_llm = self._create_llm(temperature=0.7, max_tokens=800)  # For generation
        logger.info("LangChain Manager initialized with optimized instances")
    
    def _create_llm(self, temperature: float = 0.7, max_tokens: int = 1000) -> ChatOpenAI:
        """Create OpenAI LLM instance"""
        return ChatOpenAI(
            model=settings.OPENAI_MODEL_GPT,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=False,
            # Optimize connection and retry settings
            max_retries=2,
            request_timeout=25,
            # Enable connection pool optimization
            http_client=None  # Use default httpx client connection pool
        )
    
    def get_llm(self, temperature: float = 0.7, max_tokens: int = 1000) -> ChatOpenAI:
        """Get configured LLM instance"""
        # Return pre-created instances for common configurations
        if temperature == 0.3 and max_tokens == 1500:
            return self._analysis_llm
        elif temperature == 0.7 and max_tokens == 800:
            return self._generation_llm
        elif temperature == 0.7 and max_tokens == 1000:
            return self._default_llm
        
        # Create dynamically for other configurations
        return self._create_llm(temperature, max_tokens)
    
    def get_analysis_llm(self) -> ChatOpenAI:
        """Get analysis-specific LLM instance (low temperature, high tokens)"""
        return self._analysis_llm
    
    def get_generation_llm(self) -> ChatOpenAI:
        """Get generation-specific LLM instance (medium temperature, medium tokens)"""
        return self._generation_llm
    
    def create_callback_handler(self, session_id: str) -> InterviewCallbackHandler:
        """Create callback handler"""
        return InterviewCallbackHandler(session_id)
    
    def format_conversation_history(self, history: list) -> list[BaseMessage]:
        """Format conversation history to LangChain message format"""
        messages = []
        for item in history:
            if isinstance(item, dict):
                question = item.get("question", "")
                answer = item.get("answer", "")
                
                if question:
                    messages.append(HumanMessage(content=f"Question: {question}"))
                if answer:
                    messages.append(AIMessage(content=f"Answer: {answer}"))
        
        return messages
    
    def extract_text_content(self, message: BaseMessage) -> str:
        """Extract text content from LangChain message"""
        if hasattr(message, 'content'):
            return str(message.content)
        return str(message)

# Global LangChain manager instance
langchain_manager = LangChainManager()

# Predefined system message templates
SYSTEM_MESSAGES = {
    "interview_planner": SystemMessage(content="""You are an expert interview analyst and planner. Your role is to:

1. Analyze candidate responses for completeness, specificity, and structure
2. Identify key themes and missing information  
3. Recommend focus areas for follow-up questions
4. Provide strategic guidance for the interview flow

CRITICAL REQUIREMENTS:
- ALWAYS respond in English, regardless of the candidate's input language
- Be thorough, objective, and focused on getting the most valuable insights from candidates
- Maintain professional English throughout all analysis and recommendations

Always respond in JSON format with the following structure:
{
    "completeness_score": 1-10,
    "specificity_score": 1-10, 
    "structure_score": 1-10,
    "key_themes": ["theme1", "theme2"],
    "missing_elements": ["element1", "element2"],
    "strengths": ["strength1", "strength2"],
    "areas_to_explore": ["area1", "area2"],
    "recommended_focus": "specific_details|leadership|problem_solving|teamwork|results_impact|challenges|learning|motivation|general",
    "reasoning": "Brief explanation of the analysis and recommendations"
}"""),
    
    "interview_chatbot": SystemMessage(content="""You are a professional interview chatbot. Your role is to generate thoughtful, relevant follow-up questions based on candidate responses.

CRITICAL REQUIREMENTS:
- ALWAYS generate questions in English, regardless of candidate's input language
- NEVER repeat similar question types that have been asked before in this session
- Ensure each question explores a different aspect or angle of the topic

Guidelines:
- Generate exactly ONE follow-up question
- Make questions conversational and natural
- Focus on behavioral examples and specific details
- Avoid yes/no questions
- Build on what the candidate has already shared
- Keep questions open-ended to encourage detailed responses
- Maintain appropriate tone based on interview style (formal/casual/campus)
- Vary question types: behavioral, situational, technical, reflective, etc.
- Consider the conversation history to avoid repetitive questioning patterns

You will receive analysis results and should use them to craft the most appropriate follow-up question."""),
    
    "interview_evaluator": SystemMessage(content="""You are an interview evaluation expert. Analyze the overall interview performance and provide constructive feedback.

Focus on:
- Communication clarity and structure
- Depth of examples and specificity
- Leadership and problem-solving demonstration
- Areas for improvement
- Overall impression

Provide balanced, constructive feedback that helps candidates understand their performance.""")
}

def get_system_message(message_type: str) -> SystemMessage:
    """Get predefined system message"""
    return SYSTEM_MESSAGES.get(message_type, SystemMessage(content="You are a helpful AI assistant."))

def create_runnable_config(session_id: str, **kwargs) -> RunnableConfig:
    """Create LangChain runnable configuration"""
    callback_handler = langchain_manager.create_callback_handler(session_id)
    
    config = RunnableConfig(
        callbacks=[callback_handler],
        tags=[f"session:{session_id}", "interview"],
        metadata={"session_id": session_id, **kwargs}
    )
    
    return config