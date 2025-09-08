"""
LangChain配置和共享工具
为planner和chatbot模块提供统一的LangChain设置
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
    """面试专用的回调处理器，用于记录和监控LangChain调用"""
    
    def __init__(self, session_id: str = "unknown"):
        self.session_id = session_id
        self.start_time = None
        self.token_usage = {}
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts, **kwargs):
        """LLM开始调用时的回调"""
        import time
        self.start_time = time.time()
        logger.info(f"[{self.session_id}] LLM call started")
    
    def on_llm_end(self, response, **kwargs):
        """LLM调用结束时的回调"""
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(f"[{self.session_id}] LLM call completed in {duration:.2f}s")
            
        # 记录token使用情况
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            if token_usage:
                self.token_usage = token_usage
                logger.info(f"[{self.session_id}] Token usage: {token_usage}")
    
    def on_llm_error(self, error: Exception, **kwargs):
        """LLM调用出错时的回调"""
        logger.error(f"[{self.session_id}] LLM error: {error}")

class LangChainManager:
    """LangChain管理器，提供统一的LLM配置和工具"""
    
    def __init__(self):
        # 预创建常用的LLM实例以提高性能
        self._llm_instances = {}
        self._default_llm = self._create_llm()
        self._analysis_llm = self._create_llm(temperature=0.3, max_tokens=1500)  # 用于分析
        self._generation_llm = self._create_llm(temperature=0.7, max_tokens=800)  # 用于生成
        logger.info("LangChain Manager initialized with optimized instances")
    
    def _create_llm(self, temperature: float = 0.7, max_tokens: int = 1000) -> ChatOpenAI:
        """创建OpenAI LLM实例"""
        return ChatOpenAI(
            model=settings.OPENAI_MODEL_GPT,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=False,
            # 优化连接和重试设置
            max_retries=2,
            request_timeout=25,
            # 启用连接池优化
            http_client=None  # 使用默认的httpx客户端连接池
        )
    
    def get_llm(self, temperature: float = 0.7, max_tokens: int = 1000) -> ChatOpenAI:
        """获取配置好的LLM实例"""
        # 对于常用配置，直接返回预创建的实例
        if temperature == 0.3 and max_tokens == 1500:
            return self._analysis_llm
        elif temperature == 0.7 and max_tokens == 800:
            return self._generation_llm
        elif temperature == 0.7 and max_tokens == 1000:
            return self._default_llm
        
        # 对于其他配置，动态创建
        return self._create_llm(temperature, max_tokens)
    
    def get_analysis_llm(self) -> ChatOpenAI:
        """获取分析专用LLM实例（低温度，高token）"""
        return self._analysis_llm
    
    def get_generation_llm(self) -> ChatOpenAI:
        """获取生成专用LLM实例（中等温度，中等token）"""
        return self._generation_llm
    
    def create_callback_handler(self, session_id: str) -> InterviewCallbackHandler:
        """创建回调处理器"""
        return InterviewCallbackHandler(session_id)
    
    def format_conversation_history(self, history: list) -> list[BaseMessage]:
        """将对话历史格式化为LangChain消息格式"""
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
        """从LangChain消息中提取文本内容"""
        if hasattr(message, 'content'):
            return str(message.content)
        return str(message)

# 全局LangChain管理器实例
langchain_manager = LangChainManager()

# 预定义的系统消息模板
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
    """获取预定义的系统消息"""
    return SYSTEM_MESSAGES.get(message_type, SystemMessage(content="You are a helpful AI assistant."))

def create_runnable_config(session_id: str, **kwargs) -> RunnableConfig:
    """创建LangChain运行配置"""
    callback_handler = langchain_manager.create_callback_handler(session_id)
    
    config = RunnableConfig(
        callbacks=[callback_handler],
        tags=[f"session:{session_id}", "interview"],
        metadata={"session_id": session_id, **kwargs}
    )
    
    return config