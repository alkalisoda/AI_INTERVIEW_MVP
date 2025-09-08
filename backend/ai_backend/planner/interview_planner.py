"""
Simplified interview planner module
Responsible for deciding whether to continue follow-up (maximum 1) or move to next question
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.schema.runnable import RunnablePassthrough

from ..config import (
    langchain_manager, 
    get_system_message, 
    create_runnable_config
)
from core.config import settings

logger = logging.getLogger(__name__)

class SkillAssessment(BaseModel):
    """技能评估模型"""
    skill_name: str = Field(description="技能名称")
    score: int = Field(ge=1, le=10, description="评分 1-10")
    evidence: List[str] = Field(description="支持证据")
    improvement_suggestions: List[str] = Field(description="改进建议")

class InterviewReport(BaseModel):
    """面试报告模型"""
    session_id: str = Field(description="Session ID")
    candidate_name: str = Field(default="Anonymous", description="Candidate name")
    interview_date: str = Field(description="面试日期")
    duration_minutes: float = Field(description="面试时长（分钟）")
    
    # 整体评估
    overall_score: int = Field(ge=1, le=10, description="总体评分")
    overall_summary: str = Field(description="总体评价")
    
    # 技能评估
    skill_assessments: List[SkillAssessment] = Field(description="技能评估列表")
    
    # 详细分析
    strengths: List[str] = Field(description="优势列表")
    areas_for_improvement: List[str] = Field(description="需要改进的领域")
    behavioral_insights: List[str] = Field(description="行为洞察")
    
    # Question分析
    question_performance: List[Dict[str, Any]] = Field(description="每个Question的表现分析")
    
    # 推荐
    hiring_recommendation: str = Field(description="招聘建议: strongly_recommend, recommend, neutral, not_recommend")
    next_steps: List[str] = Field(description="后续步骤建议")
    
    # 元数据
    total_questions: int = Field(description="总Question数")
    followup_questions: int = Field(description="追问数量")
    response_quality_avg: float = Field(description="Answer质量平均分")

class AnalysisResult(BaseModel):
    """Answer质量分析结果模型"""
    # 分析部分
    completeness_score: int = Field(ge=1, le=10, description="Answer完整性评分 1-10")
    specificity_score: int = Field(ge=1, le=10, description="具体性评分 1-10") 
    key_themes: List[str] = Field(description="识别到的关键主题", max_items=3)
    missing_elements: List[str] = Field(description="缺少的要素", max_items=3)
    
    # 质量判断
    needs_followup: bool = Field(description="基于质量判断是否需要追问")
    reasoning: str = Field(description="分析理由")
    
    # 给chatbot的建议
    suggested_focus: str = Field(description="建议关注的方向")
    conversation_context: str = Field(description="conversation context总结")

class SimplifiedInterviewPlanner:
    """
    Simplified interview planner module
    只负责决定是否Continue follow-up(maximum 1)或Move to next question
    """
    
    def __init__(self):
        self.llm = langchain_manager.get_analysis_llm()
        
        # 创建输出解析器
        self.parser = PydanticOutputParser(pydantic_object=AnalysisResult)
        self.fixing_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.llm)
        
        # 创建分析链
        self.analysis_chain = self._create_analysis_chain()
        
        # conversation memory storage - uncompressed, save complete conversation
        self.conversation_memories: Dict[str, List[Dict]] = {}  # session_id -> conversation history
        
        logger.info("Simplified Interview Planner initialized with conversation memory")
    
    def _create_analysis_chain(self):
        """Create answer quality analysis chain"""
        
        analysis_template = """你是专业的面试分析师。请基于完整对话历史分析候选人Answer的质量。

**当前Question**: {original_question}
**候选人Answer**: {user_answer}

**完整对话历史**:
{conversation_history}

**额外上下文**: {context}

请结合对话历史进行深度质量分析：

1. **Answer质量评估**:
   - 完整性评分 (1-10): Answer是否完整回应了Question
   - 具体性评分 (1-10): 是否包含具体例子和细节
   - 关键主题: 识别Answer中的主要主题 (最多3个)
   - 缺失要素: Answer中缺少的重要信息 (最多3个)

2. **基于历史的追问建议**:
   - 结合之前的对话，判断是否需要追问
   - 考虑是否已经在之前Answer中涵盖了相关内容
   - 如果Answer完整具体(完整性≥7，具体性≥6)，通常不需要追问
   - 如果Answer模糊或缺少关键细节，且之前未涉及，建议追问
   - 避免重复已经问过的内容

3. **给chatbot的指导**:
   - 建议关注方向: 应该关注什么方面（考虑历史对话）
   - conversation context: 总结整体对话进展和候选人表现趋势

{format_instructions}

请返回JSON格式的分析结果。"""

        prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_planner"),
            ("human", analysis_template)
        ])
        
        chain = (
            RunnablePassthrough.assign(
                format_instructions=lambda _: self.parser.get_format_instructions()
            )
            | prompt
            | self.llm
            | self.fixing_parser
        )
        
        return chain
    
    async def analyze_answer(
        self,
        user_answer: str,
        original_question: str,
        context: str = "",
        session_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Analyze user answer quality using complete conversation history
        """
        try:
            logger.info(f"[{session_id}] Analyzing answer quality with conversation history")
            
            # Record current conversation to memory
            self._add_to_memory(session_id, {
                "question": original_question,
                "answer": user_answer,
                "timestamp": logger.name  # 简单标记，可以用datetime
            })
            
            # Get complete conversation history
            conversation_history = self._get_conversation_context(session_id)
            
            # Use AI for quality analysis including conversation history
            input_data = {
                "user_answer": user_answer,
                "original_question": original_question,
                "conversation_history": conversation_history,
                "context": context or "无先前对话"
            }
            
            config = create_runnable_config(session_id, task="answer_analysis")
            analysis_result = await self.analysis_chain.ainvoke(input_data, config=config)
            
            # Return analysis results
            return {
                # 分析结果 - 给chatbot使用
                "completeness_score": analysis_result.completeness_score,
                "specificity_score": analysis_result.specificity_score,
                "key_themes": analysis_result.key_themes,
                "missing_elements": analysis_result.missing_elements,
                "suggested_focus": analysis_result.suggested_focus,
                "conversation_context": analysis_result.conversation_context,
                
                # 质量建议
                "needs_followup": analysis_result.needs_followup,
                "reasoning": analysis_result.reasoning,
                
                # 原始数据
                "user_answer": user_answer,
                "original_question": original_question,
                "full_conversation": conversation_history
            }
                
        except Exception as e:
            logger.error(f"[{session_id}] Answer analysis failed: {e}")
            return {
                "completeness_score": 5,
                "specificity_score": 5,
                "key_themes": ["general"],
                "missing_elements": [],
                "suggested_focus": "general",
                "conversation_context": "分析失败",
                "needs_followup": False,
                "reasoning": "System error, unable to analyze"
            }
    
    def _add_to_memory(self, session_id: str, conversation_entry: Dict[str, str]):
        """Add conversation record to memory"""
        if session_id not in self.conversation_memories:
            self.conversation_memories[session_id] = []
        
        self.conversation_memories[session_id].append(conversation_entry)
        logger.debug(f"[{session_id}] Added conversation to memory, total: {len(self.conversation_memories[session_id])}")
    
    def _get_conversation_context(self, session_id: str) -> str:
        """Get complete conversation history的文本格式"""
        if session_id not in self.conversation_memories or not self.conversation_memories[session_id]:
            return "No conversation history"
        
        history_parts = []
        for i, entry in enumerate(self.conversation_memories[session_id], 1):
            history_parts.append(f"Conversation round {i}:")
            history_parts.append(f"Question: {entry['question']}")
            history_parts.append(f"Answer: {entry['answer']}")
            history_parts.append("---")
        
        return "\n".join(history_parts)
    
    def get_conversation_memory(self, session_id: str) -> List[Dict]:
        """Get original conversation records"""
        return self.conversation_memories.get(session_id, [])
    
    def reset_session(self, session_id: str):
        """Reset session state, clear conversation memory"""
        if session_id in self.conversation_memories:
            del self.conversation_memories[session_id]
        logger.info(f"[{session_id}] Session state and conversation memory reset")
    
    async def generate_interview_report(
        self,
        session_id: str,
        interview_duration_minutes: float = 0.0,
        candidate_name: str = "Anonymous"
    ) -> InterviewReport:
        """
        生成完整的面试报告
        
        Args:
            session_id: Session ID
            interview_duration_minutes: 面试时长（分钟）
            candidate_name: Candidate name
            
        Returns:
            InterviewReport: 结构化的面试报告
        """
        try:
            logger.info(f"[{session_id}] Generating comprehensive interview report")
            
            # Get complete conversation history
            conversation_history = self.get_conversation_memory(session_id)
            if not conversation_history:
                raise ValueError("No conversation history found for this session")
            
            # 准备分析数据
            full_conversation = self._get_conversation_context(session_id)
            
            # 创建报告生成链
            report_chain = self._create_report_generation_chain()
            
            # 准备输入数据
            input_data = {
                "conversation_history": full_conversation,
                "total_interactions": len(conversation_history),
                "session_duration": interview_duration_minutes,
                "candidate_name": candidate_name
            }
            
            # 生成报告
            config = create_runnable_config(session_id, task="report_generation")
            report_result = await report_chain.ainvoke(input_data, config=config)
            
            # 计算统计数据
            total_questions = len(conversation_history)
            followup_count = sum(1 for entry in conversation_history if "followup" in str(entry).lower())
            
            # 构建最终报告
            report = InterviewReport(
                session_id=session_id,
                candidate_name=candidate_name,
                interview_date=datetime.now().strftime("%Y-%m-%d"),
                duration_minutes=interview_duration_minutes,
                overall_score=report_result.overall_score,
                overall_summary=report_result.overall_summary,
                skill_assessments=report_result.skill_assessments,
                strengths=report_result.strengths,
                areas_for_improvement=report_result.areas_for_improvement,
                behavioral_insights=report_result.behavioral_insights,
                question_performance=report_result.question_performance,
                hiring_recommendation=report_result.hiring_recommendation,
                next_steps=report_result.next_steps,
                total_questions=total_questions,
                followup_questions=followup_count,
                response_quality_avg=report_result.response_quality_avg
            )
            
            logger.info(f"[{session_id}] Interview report generated successfully, overall score: {report.overall_score}/10")
            
            return report
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to generate interview report: {e}")
            
            # 返回基础回退报告
            return InterviewReport(
                session_id=session_id,
                candidate_name=candidate_name,
                interview_date=datetime.now().strftime("%Y-%m-%d"),
                duration_minutes=interview_duration_minutes,
                overall_score=5,
                overall_summary="Report generation failed. Manual review recommended.",
                skill_assessments=[],
                strengths=["Unable to assess due to technical issues"],
                areas_for_improvement=["Manual review required"],
                behavioral_insights=["Technical issues prevented detailed analysis"],
                question_performance=[],
                hiring_recommendation="neutral",
                next_steps=["Conduct manual review", "Consider re-interview if needed"],
                total_questions=len(self.get_conversation_memory(session_id)),
                followup_questions=0,
                response_quality_avg=5.0
            )
    
    def _create_report_generation_chain(self):
        """创建面试报告生成链"""
        
        report_template = """你是专业的HR面试分析师。请基于完整的面试对话历史，生成一份详细的面试报告。

**候选人**: {candidate_name}
**面试时长**: {session_duration} 分钟
**Conversation round**: {total_interactions}

**完整对话历史**:
{conversation_history}

请进行全面分析并生成结构化报告：

1. **整体评估** (1-10分):
   - 综合评分及理由
   - 总体印象和表现摘要

2. **技能评估** (每项1-10分):
   - 沟通能力: 表达清晰度、逻辑性
   - Question解决能力: 分析思维、解决方案
   - 团队合作: 协作精神、适应性
   - 领导力: 影响力、决策能力
   - 学习能力: 成长意愿、反思能力

3. **详细分析**:
   - 主要优势 (3-5点)
   - 需要改进的领域 (2-4点)
   - 行为特征洞察 (2-3点)

4. **Question表现分析**:
   - 每个主要Question的Answer质量
   - 具体表现和改进建议

5. **招聘建议**:
   - 推荐等级: strongly_recommend/recommend/neutral/not_recommend
   - 具体理由和后续步骤

6. **量化指标**:
   - 平均Answer质量评分

请确保分析客观、具体，基于实际对话内容，避免主观臆断。

{format_instructions}

请返回JSON格式的完整报告。"""

        # 创建报告结果的解析器
        from pydantic import BaseModel, Field
        
        class ReportGenerationResult(BaseModel):
            overall_score: int = Field(ge=1, le=10, description="总体评分")
            overall_summary: str = Field(description="总体评价")
            skill_assessments: List[SkillAssessment] = Field(description="技能评估")
            strengths: List[str] = Field(description="优势")
            areas_for_improvement: List[str] = Field(description="改进领域")
            behavioral_insights: List[str] = Field(description="行为洞察")
            question_performance: List[Dict[str, Any]] = Field(description="Question表现")
            hiring_recommendation: str = Field(description="招聘建议")
            next_steps: List[str] = Field(description="后续步骤")
            response_quality_avg: float = Field(description="平均Answer质量")
        
        parser = PydanticOutputParser(pydantic_object=ReportGenerationResult)
        fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm)
        
        prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_planner"),
            ("human", report_template)
        ])
        
        chain = (
            RunnablePassthrough.assign(
                format_instructions=lambda _: parser.get_format_instructions()
            )
            | prompt
            | self.llm
            | fixing_parser
        )
        
        return chain
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        try:
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "unhealthy",
                    "reason": "Missing OpenAI API key",
                    "langchain_integration": False
                }
            
            # 简单测试分析链
            config = create_runnable_config("health_check", task="health_check")
            test_result = await self.analysis_chain.ainvoke({
                "user_answer": "I completed a project successfully.",
                "original_question": "Test question",
                "context": "Test context",
                "current_followup_count": 0
            }, config=config)
            
            return {
                "status": "healthy",
                "langchain_integration": True,
                "model": settings.OPENAI_MODEL_GPT,
                "features": [
                    "answer_quality_analysis",
                    "context_report_generation", 
                    "followup_decision_making",
                    "max_followup_limit_1",
                    "chatbot_guidance"
                ]
            }
            
        except Exception as e:
            logger.error(f"Simplified planner health check failed: {e}")
            return {
                "status": "unhealthy",
                "reason": str(e),
                "langchain_integration": False
            }

# 导出简化的规划器
InterviewPlanner = SimplifiedInterviewPlanner