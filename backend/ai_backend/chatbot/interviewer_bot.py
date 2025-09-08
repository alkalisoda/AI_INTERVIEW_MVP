"""
使用LangChain重构的面试官机器人模块
提供更强大的prompt管理、链式处理和多样化的Question生成策略
"""

import logging
import random
from typing import Dict, Any, List, Optional
from enum import Enum

from langchain.prompts import PromptTemplate, ChatPromptTemplate, FewShotPromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.chains import LLMChain
from langchain.schema.runnable import RunnablePassthrough, RunnableBranch, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationSummaryBufferMemory

from ..config import (
    langchain_manager, 
    get_system_message, 
    create_runnable_config
)
from ..models import PlannerToChbotData, ChatbotResponse, InterviewStrategy
from core.config import settings

logger = logging.getLogger(__name__)

class InterviewStyle(str, Enum):
    """interview style枚举"""
    FORMAL = "formal"
    CASUAL = "casual"  
    CAMPUS = "campus"

class QuestionType(str, Enum):
    """Question类型枚举"""
    CLARIFICATION = "clarification"
    DEEP_DIVE = "deep_dive"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    REFLECTION = "reflection"

class LangChainInterviewerBot:
    """
    基于LangChain的面试官机器人
    使用链式处理、prompt工程和多种生成策略来创建自然的后续Question
    """
    
    def __init__(self):
        # 不同温度的LLM实例用于不同类型的生成
        self.creative_llm = langchain_manager.get_llm(temperature=0.8, max_tokens=150)  # 创造性Question生成
        self.analytical_llm = langchain_manager.get_llm(temperature=0.3, max_tokens=150)  # 分析性Question生成
        self.balanced_llm = langchain_manager.get_llm(temperature=0.7, max_tokens=150)  # 平衡型
        
        # 创建不同的Question生成链
        self.followup_chains = self._create_followup_chains()
        self.template_selector = self._create_template_selector()
        
        # 预定义Question模板和例子
        self.question_templates = self._load_enhanced_templates()
        self.question_examples = self._load_question_examples()
        
        logger.info("LangChain Interviewer Bot initialized")
    
    def _create_followup_chains(self) -> Dict[str, Any]:
        """创建不同类型的后续Question生成链"""
        
        # 1. 深度挖掘链 - 用于获取更详细信息
        deep_dive_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """基于候选人的Answer，生成一个深度挖掘的后续Question。

候选人Answer: {user_answer}
original question: {original_question}
对话背景: {context}
分析重点: {focus_area}
关键主题: {key_themes}

要求：
- 深入探讨候选人提到的具体经验
- 询问更多具体细节、数字、或例子
- 保持 {interview_style} 的语调
- 生成一个自然、对话式的Question

后续Question:""")
        ])
        
        deep_dive_chain = deep_dive_prompt | self.analytical_llm | StrOutputParser()
        
        # 2. 行为探索链 - 关注行为和决策过程
        behavioral_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """基于候选人的Answer，生成一个探索其行为和决策过程的Question。

候选人Answer: {user_answer}
original question: {original_question}
对话背景: {context}
推荐关注点: {focus_area}

请生成一个Question来探索：
- 候选人的决策过程和思考方式
- 其在团队中的具体行为和作用
- 面对挑战时的反应和策略

语调: {interview_style}

后续Question:""")
        ])
        
        behavioral_chain = behavioral_prompt | self.balanced_llm | StrOutputParser()
        
        # 3. 反思学习链 - 关注成长和学习
        reflection_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """基于候选人的Answer，生成一个关注其反思和学习的Question。

候选人Answer: {user_answer}
经验类型: {focus_area}
对话背景: {context}

生成一个Question来探索：
- 候选人从这个经验中学到了什么
- 如何将这些学习应用到未来情况
- 对于类似情况会如何改进

保持 {interview_style} 的专业度。

后续Question:""")
        ])
        
        reflection_chain = reflection_prompt | self.creative_llm | StrOutputParser()
        
        # 4. 情境拓展链 - 探索类似或相关情境
        situational_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """基于候选人分享的经验，询问类似或相关的情境。

候选人的经验: {user_answer}
关键主题: {key_themes}
对话背景: {context}

生成一个Question来探索：
- 类似情况下的其他经验
- 不同背景下的相关技能应用
- 相关挑战的处理方式

语调: {interview_style}
避免重复已经讨论过的内容。

后续Question:""")
        ])
        
        situational_chain = situational_prompt | self.balanced_llm | StrOutputParser()
        
        return {
            "deep_dive": deep_dive_chain,
            "behavioral": behavioral_chain,
            "reflection": reflection_chain,
            "situational": situational_chain
        }
    
    def _create_template_selector(self) -> RunnableBranch:
        """创建模板选择器，根据分析结果选择最佳生成策略"""
        
        def select_chain_type(inputs: Dict[str, Any]) -> str:
            """根据输入选择最合适的链类型"""
            focus_area = inputs.get("focus_area", "general")
            completeness_score = inputs.get("completeness_score", 5)
            specificity_score = inputs.get("specificity_score", 5)
            confidence = inputs.get("confidence", 0.5)
            
            # 策略选择逻辑
            if completeness_score < 6 or specificity_score < 6:
                return "deep_dive"
            elif focus_area in ["leadership", "teamwork", "problem_solving"]:
                return "behavioral"  
            elif confidence > 0.8:
                return "reflection"
            else:
                return "situational"
        
        # 创建条件分支
        selector = RunnableBranch(
            (
                lambda x: select_chain_type(x) == "deep_dive",
                lambda x: self.followup_chains["deep_dive"]
            ),
            (
                lambda x: select_chain_type(x) == "behavioral", 
                lambda x: self.followup_chains["behavioral"]
            ),
            (
                lambda x: select_chain_type(x) == "reflection",
                lambda x: self.followup_chains["reflection"]
            ),
            # 默认情况
            lambda x: self.followup_chains["situational"]
        )
        
        return selector
    
    async def process_planner_data(
        self,
        planner_data: PlannerToChbotData
    ) -> ChatbotResponse:
        """
        处理来自planner的JSON数据并生成回复
        
        Args:
            planner_data: 来自planner的结构化数据
            
        Returns:
            ChatbotResponse: 结构化的回复数据
        """
        try:
            logger.info(f"[{planner_data.session_id}] Processing planner data with strategy: {planner_data.planner_suggestion.recommended_strategy}")
            
            # 根据planner的策略建议选择生成方法
            strategy = planner_data.planner_suggestion.recommended_strategy
            
            # 准备输入数据，兼容现有的generate_followup方法
            analysis_data = {
                "focus_area": strategy.value,
                "completeness_score": planner_data.planner_suggestion.quality_assessment.completeness_score,
                "specificity_score": planner_data.planner_suggestion.quality_assessment.specificity_score,
                "structure_score": planner_data.planner_suggestion.quality_assessment.structure_score,
                "key_themes": planner_data.planner_suggestion.key_themes,
                "missing_elements": planner_data.planner_suggestion.missing_elements,
                "confidence": planner_data.planner_suggestion.confidence,
                "original_question": planner_data.original_question,
                "reasoning": planner_data.planner_suggestion.reasoning
            }
            
            # 调用现有的生成方法
            generation_result = await self.generate_followup(
                analysis=analysis_data,
                user_answer=planner_data.user_input,
                context=planner_data.conversation_context,
                style=planner_data.interview_style,
                session_id=planner_data.session_id
            )
            
            # 将结果转换为结构化的ChatbotResponse
            chatbot_response = ChatbotResponse(
                response_text=generation_result["question"],
                response_type="question",
                strategy_used=strategy,
                focus_area=analysis_data["focus_area"],
                alternative_responses=generation_result.get("alternatives", []),
                generation_method=generation_result.get("generation_method", "langchain_powered"),
                confidence=generation_result.get("confidence", 0.7),
                processing_time=None  # 可以在coordinator中添加
            )
            
            logger.info(f"[{planner_data.session_id}] Successfully generated response using {strategy.value} strategy")
            
            return chatbot_response
            
        except Exception as e:
            logger.error(f"[{planner_data.session_id}] Failed to process planner data: {e}")
            
            # 返回回退响应
            return ChatbotResponse(
                response_text="Can you tell me more about that experience?",
                response_type="question",
                strategy_used=InterviewStrategy.DEEP_DIVE,
                focus_area="general",
                alternative_responses=[],
                generation_method="fallback",
                confidence=0.3
            )
    
    async def process_json_input(
        self,
        json_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理JSON格式的输入数据
        
        Args:
            json_data: 包含用户输入和planner建议的JSON数据
            
        Returns:
            Dict: 包含生成回复的字典
        """
        try:
            # 验证并解析JSON数据
            planner_data = PlannerToChbotData(**json_data)
            
            # 处理数据并生成回复
            response = await self.process_planner_data(planner_data)
            
            # 转换为兼容的字典格式
            return {
                "question": response.response_text,
                "response_type": response.response_type,
                "strategy_used": response.strategy_used.value,
                "focus_area": response.focus_area,
                "alternatives": response.alternative_responses,
                "generation_method": response.generation_method,
                "confidence": response.confidence,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to process JSON input: {e}")
            return {
                "question": "I'd like to hear more about your experience. Can you provide additional details?",
                "response_type": "question",
                "strategy_used": "deep_dive",
                "focus_area": "general",
                "alternatives": [],
                "generation_method": "json_fallback",
                "confidence": 0.3,
                "success": False,
                "error": str(e)
            }

    async def generate_followup(
        self,
        analysis: Dict[str, Any],
        user_answer: str,
        context: str = "",
        style: str = "formal",
        session_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        使用LangChain生成后续Question
        """
        try:
            logger.info(f"[{session_id}] Generating LangChain-powered followup question")
            
            # 准备输入数据
            input_data = {
                "user_answer": user_answer,
                "original_question": analysis.get("original_question", ""),
                "context": context or "无先前对话",
                "focus_area": analysis.get("focus_area", "general"),
                "key_themes": ", ".join(analysis.get("key_themes", [])),
                "interview_style": style,
                "completeness_score": analysis.get("completeness_score", 5),
                "specificity_score": analysis.get("specificity_score", 5),
                "confidence": analysis.get("confidence", 0.5)
            }
            
            # 创建运行配置
            config = create_runnable_config(session_id, task="followup_generation")
            
            # 选择和执行合适的链
            selected_chain_type = self._select_generation_strategy(analysis)
            chain = self.followup_chains[selected_chain_type]
            
            logger.info(f"[{session_id}] Using {selected_chain_type} generation strategy")
            
            # 生成Question
            generated_question = await chain.ainvoke(input_data, config=config)
            
            # 后处理Question
            final_question = self._post_process_question(generated_question, style)
            
            # 不生成备选Question以提高效率
            result = {
                "question": final_question,
                "generation_method": f"langchain_{selected_chain_type}",
                "focus_area": analysis.get("focus_area", "general"),
                "confidence": analysis.get("confidence", 0.5),
                "reasoning": f"Using {selected_chain_type} strategy based on analysis",
                "alternatives": [],  # 空数组以保持API兼容性
                "langchain_powered": True
            }
            
            logger.info(f"[{session_id}] Followup generated: {final_question[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"[{session_id}] LangChain followup generation failed: {e}")
            # 回退到模板生成
            return await self._generate_template_fallback(analysis, user_answer, style, session_id)
    
    def _select_generation_strategy(self, analysis: Dict[str, Any]) -> str:
        """选择生成策略"""
        focus_area = analysis.get("focus_area", "general")
        completeness_score = analysis.get("completeness_score", 5)
        specificity_score = analysis.get("specificity_score", 5)
        confidence = analysis.get("confidence", 0.5)
        
        # 策略选择逻辑
        if completeness_score < 6 or specificity_score < 6:
            return "deep_dive"
        elif focus_area in ["leadership", "teamwork", "problem_solving"]:
            return "behavioral"
        elif confidence > 0.8:
            return "reflection"
        else:
            return "situational"
    
    # 移除备选Question生成方法以提高效率
    
    def _post_process_question(self, question: str, style: str) -> str:
        """后处理生成的Question"""
        if not question:
            return "Can you tell me more about that experience?"
        
        # 清理Question
        cleaned = question.strip()
        
        # 移除可能的前缀
        prefixes_to_remove = [
            "后续Question:", "Follow-up question:", "Question:", "Question:",
            "Here's a follow-up question:", "I'd like to ask:"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                break
        
        # 确保首字母大写
        if cleaned and not cleaned[0].isupper():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # 确保以问号结尾
        if cleaned and not cleaned.endswith('?'):
            cleaned += '?'
        
        # 根据风格调整语气
        if style == "casual" and not cleaned.lower().startswith(("can", "could", "would", "so,")):
            if cleaned.startswith("What") or cleaned.startswith("How"):
                cleaned = "So, " + cleaned.lower()
        elif style == "campus":
            encouraging_starts = ["That's interesting! ", "I'd love to hear more - ", "Great! "]
            if not any(cleaned.startswith(start) for start in encouraging_starts):
                cleaned = random.choice(encouraging_starts) + cleaned.lower()
                if cleaned.endswith('?.'):
                    cleaned = cleaned[:-1]
        
        return cleaned
    
    async def _generate_template_fallback(
        self,
        analysis: Dict[str, Any],
        user_answer: str,
        style: str,
        session_id: str
    ) -> Dict[str, Any]:
        """模板回退生成"""
        logger.info(f"[{session_id}] Using template fallback for followup generation")
        
        focus_area = analysis.get("focus_area", "general")
        templates = self.question_templates.get(focus_area, self.question_templates["general"])
        
        # 选择合适的模板
        selected_template = random.choice(templates)
        
        # 个性化模板
        question = self._personalize_template(selected_template, user_answer)
        
        # 应用风格
        final_question = self._post_process_question(question, style)
        
        return {
            "question": final_question,
            "generation_method": "template_fallback",
            "focus_area": focus_area,
            "confidence": 0.3,
            "reasoning": "Template fallback due to LangChain generation error",
            "alternatives": [],
            "langchain_powered": False
        }
    
    def _personalize_template(self, template: str, user_answer: str) -> str:
        """个性化Question模板"""
        personalized = template
        answer_lower = user_answer.lower()
        
        # 替换模板变量
        replacements = {
            "{situation}": "team situation" if "team" in answer_lower else "project" if "project" in answer_lower else "situation",
            "{experience}": "challenging experience" if "challenge" in answer_lower else "experience",
            "{role}": "leadership role" if "lead" in answer_lower else "role",
            "{outcome}": "result" if "result" in answer_lower else "outcome"
        }
        
        for placeholder, replacement in replacements.items():
            personalized = personalized.replace(placeholder, replacement)
        
        return personalized
    
    def _load_enhanced_templates(self) -> Dict[str, List[str]]:
        """加载增强的Question模板"""
        return {
            "specific_details": [
                "Can you walk me through the specific steps you took in that {situation}?",
                "What exactly was your {role} in that {experience}?",
                "Could you give me more concrete details about how you approached that challenge?",
                "What specific actions did you take, and what was the {outcome}?",
                "Can you quantify the impact of your actions in that situation?"
            ],
            "leadership": [
                "How did you motivate your team during that {experience}?",
                "What leadership approach did you take, and why?",
                "How did you handle any pushback or resistance from team members?",
                "What was the toughest leadership decision you had to make in that situation?",
                "How did you ensure everyone was aligned with your vision?"
            ],
            "problem_solving": [
                "What alternative solutions did you consider before settling on that approach?",
                "How did you identify the root cause of that problem?",
                "What resources or tools did you leverage to solve that challenge?",
                "How did you prioritize different aspects of the problem?",
                "Looking back, what would you do differently if faced with a similar problem?"
            ],
            "teamwork": [
                "How did you ensure effective collaboration with your team members?",
                "What role did you naturally take in the team dynamic?",
                "How did you handle any conflicts or disagreements within the team?",
                "How did you adapt your communication style for different team members?",
                "What did you learn about yourself from working with that particular team?"
            ],
            "results_impact": [
                "What was the measurable impact of your work on that project?",
                "How did stakeholders react to the results you delivered?",
                "What long-term effects did your solution have on the organization?",
                "How do you measure success in situations like that?",
                "What feedback did you receive about the {outcome} you achieved?"
            ],
            "challenges": [
                "What was the biggest obstacle you encountered, and how did you overcome it?",
                "How did you maintain motivation when facing those difficulties?",
                "What support systems or resources did you tap into during tough times?",
                "How did that challenge change your perspective or approach?",
                "What resilience strategies did you develop from that {experience}?"
            ],
            "learning": [
                "What key insights did you gain from that {experience}?",
                "How has that experience shaped your current professional approach?",
                "If you could go back, what would you do differently and why?",
                "What new skills or capabilities did you develop through that process?",
                "How do you apply those lessons in your current work environment?"
            ],
            "general": [
                "Can you elaborate more on that particular aspect?",
                "What was the most significant challenge in that situation?",
                "How did that experience contribute to your professional growth?",
                "What was the key factor in your success with that project?",
                "How do you typically handle similar situations now?"
            ]
        }
    
    def _load_question_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """加载Question生成的示例，用于few-shot学习"""
        return {
            "deep_dive": [
                {
                    "input": "I managed a project team and delivered on time.",
                    "output": "That's great that you delivered on time. Can you walk me through the specific strategies you used to keep the project on track, and what challenges did you encounter along the way?"
                },
                {
                    "input": "I solved a technical problem for our client.",
                    "output": "Interesting! What was the specific technical issue, and can you describe your problem-solving process step by step?"
                }
            ],
            "behavioral": [
                {
                    "input": "I had to make a difficult decision about resource allocation.",
                    "output": "Decision-making under pressure is crucial. What criteria did you use to make that decision, and how did you communicate it to your team?"
                }
            ]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        try:
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "unhealthy",
                    "reason": "Missing OpenAI API key",
                    "langchain_integration": False
                }
            
            # 测试一个简单的链
            test_input = {
                "user_answer": "I led a successful project.",
                "original_question": "Test question",
                "context": "",
                "focus_area": "leadership",
                "key_themes": "leadership",
                "interview_style": "formal",
                "completeness_score": 7,
                "specificity_score": 6,
                "confidence": 0.8
            }
            
            # 创建测试配置
            config = create_runnable_config("health_check", task="health_check")
            test_result = await self.followup_chains["behavioral"].ainvoke(test_input, config=config)
            
            return {
                "status": "healthy",
                "langchain_integration": True,
                "available_chains": list(self.followup_chains.keys()),
                "template_categories": list(self.question_templates.keys()),
                "features": [
                    "multi_strategy_generation",
                    "style_adaptation", 
                    "alternative_generation",
                    "template_fallback"
                ]
            }
            
        except Exception as e:
            logger.error(f"LangChain interviewer bot health check failed: {e}")
            return {
                "status": "unhealthy",
                "reason": str(e),
                "langchain_integration": False
            }