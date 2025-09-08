"""
AI Backend数据模型
定义planner和chatbot之间的数据交互格式
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class InterviewStrategy(str, Enum):
    """面试策略类型"""
    DEEP_DIVE = "deep_dive"  # 深入挖掘细节
    BEHAVIORAL_EXPLORE = "behavioral_explore"  # 探索行为表现
    SITUATIONAL_TEST = "situational_test"  # 情境测试
    COMPETENCY_ASSESS = "competency_assess"  # 能力评估
    REFLECTION_GUIDE = "reflection_guide"  # 反思引导
    CHALLENGE_PROBE = "challenge_probe"  # 挑战探究
    FOLLOW_THREAD = "follow_thread"  # 跟进主线

class ResponseQuality(BaseModel):
    """Answer质量评估"""
    completeness_score: int = Field(ge=1, le=10, description="完整性评分")
    specificity_score: int = Field(ge=1, le=10, description="具体性评分")
    structure_score: int = Field(ge=1, le=10, description="结构性评分")
    depth_score: int = Field(ge=1, le=10, description="深度评分")
    overall_score: float = Field(ge=1, le=10, description="综合评分")

class InterviewContext(BaseModel):
    """面试上下文信息"""
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_question_index: int = 0
    interview_style: str = "formal"
    total_questions: int = 3
    time_elapsed: Optional[float] = None

class PlannerStrategy(BaseModel):
    """Planner输出的策略信息"""
    # 基础分析
    quality_assessment: ResponseQuality
    key_themes: List[str] = Field(description="识别到的关键主题")
    missing_elements: List[str] = Field(description="缺失的重要信息")
    strengths: List[str] = Field(description="Answer的优点")
    
    # 策略决策
    recommended_strategy: InterviewStrategy = Field(description="推荐的面试策略")
    priority_areas: List[str] = Field(description="优先探索的领域")
    follow_up_directions: List[str] = Field(description="后续Question方向")
    
    # 元信息
    reasoning: str = Field(description="策略选择的理由")
    confidence: float = Field(ge=0, le=1, description="策略置信度")
    urgency: int = Field(ge=1, le=5, description="策略紧急度")

class PlannerToChbotData(BaseModel):
    """Planner传递给Chatbot的JSON数据格式"""
    user_input: str = Field(description="用户输入（文本或语音识别结果）")
    planner_suggestion: PlannerStrategy = Field(description="Planner的策略建议")
    
    # 上下文信息
    conversation_context: str = Field(default="", description="conversation context")
    original_question: str = Field(default="", description="original question")
    interview_style: str = Field(default="formal", description="interview style")
    
    # 会话信息
    session_id: str = Field(description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

class ChatbotInstruction(BaseModel):
    """Chatbot指令信息"""
    strategy: PlannerStrategy
    user_input: str
    context: InterviewContext
    session_id: str
    
    # 生成约束
    max_length: int = 200
    tone: str = "professional"
    language: str = "en"

class ChatbotResponse(BaseModel):
    """Chatbot回复信息"""
    # 主要输出
    response_text: str = Field(description="生成的回复文本")
    response_type: str = Field(description="回复类型：question/statement/guidance")
    
    # 策略执行
    strategy_used: InterviewStrategy = Field(description="实际使用的策略")
    focus_area: str = Field(description="回复重点关注的领域")
    
    # 备选方案
    alternative_responses: List[str] = Field(default_factory=list, description="备选回复")
    
    # 元信息
    generation_method: str = Field(description="生成方法")
    confidence: float = Field(ge=0, le=1, description="生成置信度")
    processing_time: Optional[float] = None

class InterviewAspect(BaseModel):
    """面试探索方面"""
    aspect_id: str = Field(description="方面唯一标识")
    aspect_name: str = Field(description="方面名称")
    focus_area: str = Field(description="关注领域")
    description: str = Field(description="方面描述")
    priority: int = Field(description="优先级 1-10", ge=1, le=10)
    estimated_questions: int = Field(description="预估Question数量", ge=1, le=3)
    
    # 状态跟踪
    current_depth: int = Field(default=0, description="当前深度")
    max_depth: int = Field(default=3, description="最大深度")
    is_completed: bool = Field(default=False, description="是否已完成")
    questions_asked: List[str] = Field(default_factory=list, description="已问Question")

class InterviewPlan(BaseModel):
    """面试计划 - 树状结构"""
    plan_id: str = Field(description="计划唯一标识")
    session_id: str = Field(description="Session ID")
    
    # 计划内容
    aspects: List[InterviewAspect] = Field(description="探索方面列表", max_items=3)
    current_aspect_id: Optional[str] = Field(default=None, description="当前探索的方面")
    
    # 计划状态
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="计划是否激活")
    completion_rate: float = Field(default=0.0, description="完成率 0-1")
    
    def get_current_aspect(self) -> Optional[InterviewAspect]:
        """获取当前探索的方面"""
        if not self.current_aspect_id:
            return None
        return next((aspect for aspect in self.aspects if aspect.aspect_id == self.current_aspect_id), None)
    
    def get_next_aspect(self) -> Optional[InterviewAspect]:
        """获取下一个未完成的方面"""
        incomplete_aspects = [aspect for aspect in self.aspects if not aspect.is_completed]
        if not incomplete_aspects:
            return None
        return min(incomplete_aspects, key=lambda x: x.priority)
    
    def update_completion_rate(self):
        """更新完成率"""
        if not self.aspects:
            self.completion_rate = 0.0
            return
        
        total_progress = sum(
            min(aspect.current_depth / aspect.max_depth, 1.0) for aspect in self.aspects
        )
        self.completion_rate = total_progress / len(self.aspects)

class PlanExecutionResult(BaseModel):
    """计划执行结果"""
    action: str = Field(description="执行动作: continue_depth/switch_aspect/complete_plan")
    current_aspect: Optional[InterviewAspect] = None
    next_question_focus: str = Field(description="下一个Question的关注点")
    reasoning: str = Field(description="执行推理")
    depth_info: Dict[str, Any] = Field(default_factory=dict, description="深度信息")

class InterviewFlowState(BaseModel):
    """面试流程状态"""
    current_phase: str  # "analysis", "planning", "generation", "response"
    planner_result: Optional[PlannerStrategy] = None
    chatbot_instruction: Optional[ChatbotInstruction] = None
    final_response: Optional[ChatbotResponse] = None
    
    # 新增：计划状态
    current_plan: Optional[InterviewPlan] = None
    plan_execution: Optional[PlanExecutionResult] = None
    
    # 流程控制
    should_continue: bool = True
    next_action: str = "wait_for_input"  # "wait_for_input", "ask_followup", "move_to_next"