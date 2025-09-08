"""
AI Backend data models
Define data interaction format between planner and chatbot
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class InterviewStrategy(str, Enum):
    """Interview strategy types"""
    DEEP_DIVE = "deep_dive"  # Deep dive into details
    BEHAVIORAL_EXPLORE = "behavioral_explore"  # Explore behavioral performance
    SITUATIONAL_TEST = "situational_test"  # Situational testing
    COMPETENCY_ASSESS = "competency_assess"  # Competency assessment
    REFLECTION_GUIDE = "reflection_guide"  # Reflection guidance
    CHALLENGE_PROBE = "challenge_probe"  # Challenge probing
    FOLLOW_THREAD = "follow_thread"  # Follow main thread

class ResponseQuality(BaseModel):
    """Answer quality assessment"""
    completeness_score: int = Field(ge=1, le=10, description="Completeness score")
    specificity_score: int = Field(ge=1, le=10, description="Specificity score")
    structure_score: int = Field(ge=1, le=10, description="Structure score")
    depth_score: int = Field(ge=1, le=10, description="Depth score")
    overall_score: float = Field(ge=1, le=10, description="Overall score")

class InterviewContext(BaseModel):
    """Interview context information"""
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_question_index: int = 0
    interview_style: str = "formal"
    total_questions: int = 3
    time_elapsed: Optional[float] = None

class PlannerStrategy(BaseModel):
    """Planner output strategy information"""
    # Basic analysis
    quality_assessment: ResponseQuality
    key_themes: List[str] = Field(description="Identified key themes")
    missing_elements: List[str] = Field(description="Missing important information")
    strengths: List[str] = Field(description="Answer strengths")
    
    # Strategy decisions
    recommended_strategy: InterviewStrategy = Field(description="Recommended interview strategy")
    priority_areas: List[str] = Field(description="Priority exploration areas")
    follow_up_directions: List[str] = Field(description="Follow-up question directions")
    
    # Meta information
    reasoning: str = Field(description="Reasoning for strategy selection")
    confidence: float = Field(ge=0, le=1, description="Strategy confidence")
    urgency: int = Field(ge=1, le=5, description="Strategy urgency")

class PlannerToChbotData(BaseModel):
    """JSON data format passed from Planner to Chatbot"""
    user_input: str = Field(description="User input (text or speech recognition result)")
    planner_suggestion: PlannerStrategy = Field(description="Planner's strategy recommendation")
    
    # Context information
    conversation_context: str = Field(default="", description="conversation context")
    original_question: str = Field(default="", description="original question")
    interview_style: str = Field(default="formal", description="interview style")
    
    # Session information
    session_id: str = Field(description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")

class ChatbotInstruction(BaseModel):
    """Chatbot instruction information"""
    strategy: PlannerStrategy
    user_input: str
    context: InterviewContext
    session_id: str
    
    # Generation constraints
    max_length: int = 200
    tone: str = "professional"
    language: str = "en"

class ChatbotResponse(BaseModel):
    """Chatbot response information"""
    # Main output
    response_text: str = Field(description="Generated response text")
    response_type: str = Field(description="Response type: question/statement/guidance")
    
    # Strategy execution
    strategy_used: InterviewStrategy = Field(description="Actually used strategy")
    focus_area: str = Field(description="Response focus area")
    
    # Alternative options
    alternative_responses: List[str] = Field(default_factory=list, description="Alternative responses")
    
    # Meta information
    generation_method: str = Field(description="Generation method")
    confidence: float = Field(ge=0, le=1, description="Generation confidence")
    processing_time: Optional[float] = None

class InterviewAspect(BaseModel):
    """Interview exploration aspect"""
    aspect_id: str = Field(description="Aspect unique identifier")
    aspect_name: str = Field(description="Aspect name")
    focus_area: str = Field(description="Focus area")
    description: str = Field(description="Aspect description")
    priority: int = Field(description="Priority 1-10", ge=1, le=10)
    estimated_questions: int = Field(description="Estimated number of questions", ge=1, le=3)
    
    # Status tracking
    current_depth: int = Field(default=0, description="Current depth")
    max_depth: int = Field(default=3, description="Maximum depth")
    is_completed: bool = Field(default=False, description="Whether completed")
    questions_asked: List[str] = Field(default_factory=list, description="Questions already asked")

class InterviewPlan(BaseModel):
    """Interview plan - tree structure"""
    plan_id: str = Field(description="Plan unique identifier")
    session_id: str = Field(description="Session ID")
    
    # Plan content
    aspects: List[InterviewAspect] = Field(description="List of exploration aspects", max_items=3)
    current_aspect_id: Optional[str] = Field(default=None, description="Currently exploring aspect")
    
    # Plan status
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="Whether plan is active")
    completion_rate: float = Field(default=0.0, description="Completion rate 0-1")
    
    def get_current_aspect(self) -> Optional[InterviewAspect]:
        """Get currently exploring aspect"""
        if not self.current_aspect_id:
            return None
        return next((aspect for aspect in self.aspects if aspect.aspect_id == self.current_aspect_id), None)
    
    def get_next_aspect(self) -> Optional[InterviewAspect]:
        """Get next incomplete aspect"""
        incomplete_aspects = [aspect for aspect in self.aspects if not aspect.is_completed]
        if not incomplete_aspects:
            return None
        return min(incomplete_aspects, key=lambda x: x.priority)
    
    def update_completion_rate(self):
        """Update completion rate"""
        if not self.aspects:
            self.completion_rate = 0.0
            return
        
        total_progress = sum(
            min(aspect.current_depth / aspect.max_depth, 1.0) for aspect in self.aspects
        )
        self.completion_rate = total_progress / len(self.aspects)

class PlanExecutionResult(BaseModel):
    """Plan execution result"""
    action: str = Field(description="Execution action: continue_depth/switch_aspect/complete_plan")
    current_aspect: Optional[InterviewAspect] = None
    next_question_focus: str = Field(description="Next question focus")
    reasoning: str = Field(description="Execution reasoning")
    depth_info: Dict[str, Any] = Field(default_factory=dict, description="Depth information")

class InterviewFlowState(BaseModel):
    """Interview flow state"""
    current_phase: str  # "analysis", "planning", "generation", "response"
    planner_result: Optional[PlannerStrategy] = None
    chatbot_instruction: Optional[ChatbotInstruction] = None
    final_response: Optional[ChatbotResponse] = None
    
    # Added: plan state
    current_plan: Optional[InterviewPlan] = None
    plan_execution: Optional[PlanExecutionResult] = None
    
    # Flow control
    should_continue: bool = True
    next_action: str = "wait_for_input"  # "wait_for_input", "ask_followup", "move_to_next"