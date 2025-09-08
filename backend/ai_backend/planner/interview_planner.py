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
    """Skill assessment model"""
    skill_name: str = Field(description="Skill name")
    score: int = Field(ge=1, le=10, description="Score 1-10")
    evidence: List[str] = Field(description="Supporting evidence")
    improvement_suggestions: List[str] = Field(description="Improvement suggestions")

class InterviewReport(BaseModel):
    """Interview report model"""
    session_id: str = Field(description="Session ID")
    candidate_name: str = Field(default="Anonymous", description="Candidate name")
    interview_date: str = Field(description="Interview date")
    duration_minutes: float = Field(description="Interview duration (minutes)")
    
    # Overall assessment
    overall_score: int = Field(ge=1, le=10, description="Overall score")
    overall_summary: str = Field(description="Overall evaluation")
    
    # Skill assessment
    skill_assessments: List[SkillAssessment] = Field(description="Skill assessment list")
    
    # Detailed analysis
    strengths: List[str] = Field(description="Strengths list")
    areas_for_improvement: List[str] = Field(description="Areas needing improvement")
    behavioral_insights: List[str] = Field(description="Behavioral insights")
    
    # Question analysis
    question_performance: List[Dict[str, Any]] = Field(description="Performance analysis for each question")
    
    # Recommendations
    hiring_recommendation: str = Field(description="Hiring recommendation: strongly_recommend, recommend, neutral, not_recommend")
    next_steps: List[str] = Field(description="Next step recommendations")
    
    # Metadata
    total_questions: int = Field(description="Total number of questions")
    followup_questions: int = Field(description="Number of follow-up questions")
    response_quality_avg: float = Field(description="Average answer quality score")

class AnalysisResult(BaseModel):
    """Answer quality analysis result model"""
    # Analysis section
    completeness_score: int = Field(ge=1, le=10, description="Answer completeness score 1-10")
    specificity_score: int = Field(ge=1, le=10, description="Specificity score 1-10") 
    key_themes: List[str] = Field(description="Identified key themes", max_items=3)
    missing_elements: List[str] = Field(description="Missing elements", max_items=3)
    
    # Quality judgment
    needs_followup: bool = Field(description="Whether follow-up is needed based on quality assessment")
    reasoning: str = Field(description="Analysis reasoning")
    
    # Suggestions for chatbot
    suggested_focus: str = Field(description="Recommended focus direction")
    conversation_context: str = Field(description="Conversation context summary")

class SimplifiedInterviewPlanner:
    """
    Simplified interview planner module
    Only responsible for deciding whether to continue follow-up (maximum 1) or move to next question
    """
    
    def __init__(self):
        self.llm = langchain_manager.get_analysis_llm()
        
        # Create output parser
        self.parser = PydanticOutputParser(pydantic_object=AnalysisResult)
        self.fixing_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.llm)
        
        # Create analysis chain
        self.analysis_chain = self._create_analysis_chain()
        
        # conversation memory storage - uncompressed, save complete conversation
        self.conversation_memories: Dict[str, List[Dict]] = {}  # session_id -> conversation history
        
        logger.info("Simplified Interview Planner initialized with conversation memory")
    
    def _create_analysis_chain(self):
        """Create answer quality analysis chain"""
        
        analysis_template = """You are a professional interview analyst. Please analyze the quality of the candidate's Answer based on the complete conversation history.

**Current Question**: {original_question}
**Candidate Answer**: {user_answer}

**Complete Conversation History**:
{conversation_history}

**Additional Context**: {context}

Please conduct a deep quality analysis considering the conversation history:

1. **Answer Quality Assessment**:
   - Completeness Score (1-10): Whether the Answer fully addresses the Question
   - Specificity Score (1-10): Whether it includes specific examples and details
   - Key Themes: Identify main themes in the Answer (max 3)
   - Missing Elements: Important information missing from the Answer (max 3)

2. **Follow-up Recommendations Based on History**:
   - Consider previous dialogue to determine if follow-up is needed
   - Check if content has been covered in previous Answers
   - If Answer is complete and specific (completeness ≥7, specificity ≥6), follow-up usually not needed
   - If Answer is vague or lacks key details, and not previously covered, recommend follow-up
   - Avoid repeating previously asked content

3. **Guidance for Chatbot**:
   - Suggested Focus: What aspects to focus on (considering conversation history)
   - Conversation Context: Summarize overall dialogue progress and candidate performance trends

{format_instructions}

Please return the analysis results in JSON format."""

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
                "timestamp": logger.name  # Simple marker, can use datetime
            })
            
            # Get complete conversation history
            conversation_history = self._get_conversation_context(session_id)
            
            # Use AI for quality analysis including conversation history
            input_data = {
                "user_answer": user_answer,
                "original_question": original_question,
                "conversation_history": conversation_history,
                "context": context or "No previous conversation"
            }
            
            config = create_runnable_config(session_id, task="answer_analysis")
            analysis_result = await self.analysis_chain.ainvoke(input_data, config=config)
            
            # Return analysis results
            return {
                # analysis result - for chatbot use
                "completeness_score": analysis_result.completeness_score,
                "specificity_score": analysis_result.specificity_score,
                "key_themes": analysis_result.key_themes,
                "missing_elements": analysis_result.missing_elements,
                "suggested_focus": analysis_result.suggested_focus,
                "conversation_context": analysis_result.conversation_context,
                
                # quality suggestions
                "needs_followup": analysis_result.needs_followup,
                "reasoning": analysis_result.reasoning,
                
                # original data
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
                "conversation_context": "Analysis failed",
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
        """Get complete conversation history in text format"""
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
        Generate comprehensive interview report
        
        Args:
            session_id: Session ID
            interview_duration_minutes: Interview duration (minutes)
            candidate_name: Candidate name
            
        Returns:
            InterviewReport: Structured interview report
        """
        try:
            logger.info(f"[{session_id}] Generating comprehensive interview report")
            
            # Get complete conversation history
            conversation_history = self.get_conversation_memory(session_id)
            if not conversation_history:
                raise ValueError("No conversation history found for this session")
            # Prepare analysis data
            full_conversation = self._get_conversation_context(session_id)
            
            # Create report generation chain
            report_chain = self._create_report_generation_chain()
            
            # Prepare input data
            input_data = {
                "conversation_history": full_conversation,
                "total_interactions": len(conversation_history),
                "session_duration": interview_duration_minutes,
                "candidate_name": candidate_name
            }
            
            # Generate report
            config = create_runnable_config(session_id, task="report_generation")
            report_result = await report_chain.ainvoke(input_data, config=config)
            
            # Calculate statistics
            total_questions = len(conversation_history)
            followup_count = sum(1 for entry in conversation_history if "followup" in str(entry).lower())
            
            # Build final report
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
            
            # Return basic fallback report
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
        """Create interview report generation chain"""
        
        report_template = """You are a professional HR interview analyst. Please generate a detailed interview report based on the complete interview conversation history.

**Candidate**: {candidate_name}
**Interview Duration**: {session_duration} minutes
**Conversation round**: {total_interactions}

**Complete Conversation History**:
{conversation_history}

Please conduct a comprehensive analysis and generate a structured report:

1. **Overall Assessment** (1-10 points):
   - Comprehensive score and rationale
   - Overall impression and performance summary

2. **Skills Assessment** (1-10 points each):
   - Communication: Clarity of expression, logic
   - Problem-solving: Analytical thinking, solutions
   - Teamwork: Collaborative spirit, adaptability
   - Leadership: Influence, decision-making
   - Learning ability: Growth mindset, reflection

3. **Detailed Analysis**:
   - Key strengths (3-5 points)
   - Areas for improvement (2-4 points)
   - Behavioral insights (2-3 points)

4. **Question Performance Analysis**:
   - Answer quality for each main question
   - Specific performance and improvement suggestions

5. **Hiring Recommendation**:
   - Recommendation level: strongly_recommend/recommend/neutral/not_recommend
   - Specific reasons and next steps

6. **Quantitative Metrics**:
   - Average answer quality score

Please ensure analysis is objective and specific, based on actual conversation content, avoiding subjective assumptions.

{format_instructions}

Please return the complete report in JSON format."""

        # Create report result parser
        from pydantic import BaseModel, Field
        
        class ReportGenerationResult(BaseModel):
            overall_score: int = Field(ge=1, le=10, description="Overall score")
            overall_summary: str = Field(description="Overall evaluation")
            skill_assessments: List[SkillAssessment] = Field(description="Skills assessment")
            strengths: List[str] = Field(description="Strengths")
            areas_for_improvement: List[str] = Field(description="Areas for improvement")
            behavioral_insights: List[str] = Field(description="Behavioral insights")
            question_performance: List[Dict[str, Any]] = Field(description="Question performance")
            hiring_recommendation: str = Field(description="Hiring recommendation")
            next_steps: List[str] = Field(description="Next steps")
            response_quality_avg: float = Field(description="Average answer quality")
        
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
            
            # Simple test of analysis chain
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

# Export simplified planner
InterviewPlanner = SimplifiedInterviewPlanner