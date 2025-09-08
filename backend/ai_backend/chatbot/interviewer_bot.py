"""
Interviewer bot module refactored using LangChain
Provides more powerful prompt management, chain processing and diverse question generation strategies
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
    """Interview style enumeration"""
    FORMAL = "formal"
    CASUAL = "casual"  
    CAMPUS = "campus"

class QuestionType(str, Enum):
    """Question type enumeration"""
    CLARIFICATION = "clarification"
    DEEP_DIVE = "deep_dive"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    REFLECTION = "reflection"

class LangChainInterviewerBot:
    """
    LangChain-based interviewer bot
    Uses chain processing, prompt engineering and multiple generation strategies to create natural follow-up questions
    """
    
    def __init__(self):
        # Different temperature LLM instances for different types of generation
        self.creative_llm = langchain_manager.get_llm(temperature=0.8, max_tokens=150)  # Creative question generation
        self.analytical_llm = langchain_manager.get_llm(temperature=0.3, max_tokens=150)  # Analytical question generation
        self.balanced_llm = langchain_manager.get_llm(temperature=0.7, max_tokens=150)  # Balanced type
        
        # Create different question generation chains
        self.followup_chains = self._create_followup_chains()
        self.template_selector = self._create_template_selector()
        
        # Predefined question templates and examples
        self.question_templates = self._load_enhanced_templates()
        self.question_examples = self._load_question_examples()
        
        logger.info("LangChain Interviewer Bot initialized")
    
    def _create_followup_chains(self) -> Dict[str, Any]:
        """Create different types of follow-up question generation chains"""
        
        # 1. Deep dive chain - for getting more detailed information
        deep_dive_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """Based on the candidate's answer, generate a deep-dive follow-up question.

Candidate answer: {user_answer}
Original question: {original_question}
Conversation background: {context}
Analysis focus: {focus_area}
Key themes: {key_themes}

Requirements:
- Explore the specific experiences mentioned by the candidate in depth
- Ask for more specific details, numbers, or examples
- Maintain {interview_style} tone
- Generate a natural, conversational question

Follow-up question:""")
        ])
        
        deep_dive_chain = deep_dive_prompt | self.analytical_llm | StrOutputParser()
        
        # 2. Behavioral exploration chain - focus on behavior and decision-making process
        behavioral_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """Based on the candidate's answer, generate a question that explores their behavior and decision-making process.

Candidate answer: {user_answer}
Original question: {original_question}
Conversation background: {context}
Recommended focus: {focus_area}

Please generate a question to explore:
- The candidate's decision-making process and thinking approach
- Their specific behavior and role in teams
- Their reactions and strategies when facing challenges

Tone: {interview_style}

Follow-up question:""")
        ])
        
        behavioral_chain = behavioral_prompt | self.balanced_llm | StrOutputParser()
        
        # 3. Reflection and learning chain - focus on growth and learning
        reflection_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """Based on the candidate's answer, generate a question that focuses on their reflection and learning.

Candidate answer: {user_answer}
Experience type: {focus_area}
Conversation background: {context}

Generate a question to explore:
- What the candidate learned from this experience
- How to apply these learnings to future situations
- How they would improve in similar situations

Maintain {interview_style} professionalism.

Follow-up question:""")
        ])
        
        reflection_chain = reflection_prompt | self.creative_llm | StrOutputParser()
        
        # 4. Situational expansion chain - explore similar or related situations
        situational_prompt = ChatPromptTemplate.from_messages([
            get_system_message("interview_chatbot"),
            ("human", """Based on the experience shared by the candidate, ask about similar or related situations.

Candidate's experience: {user_answer}
Key themes: {key_themes}
Conversation background: {context}

Generate a question to explore:
- Other experiences in similar situations
- Application of related skills in different contexts
- How related challenges were handled

Tone: {interview_style}
Avoid repeating content already discussed.

Follow-up question:""")
        ])
        
        situational_chain = situational_prompt | self.balanced_llm | StrOutputParser()
        
        return {
            "deep_dive": deep_dive_chain,
            "behavioral": behavioral_chain,
            "reflection": reflection_chain,
            "situational": situational_chain
        }
    
    def _create_template_selector(self) -> RunnableBranch:
        """Create template selector to choose the best generation strategy based on analysis results"""
        
        def select_chain_type(inputs: Dict[str, Any]) -> str:
            """Select the most appropriate chain type based on input"""
            focus_area = inputs.get("focus_area", "general")
            completeness_score = inputs.get("completeness_score", 5)
            specificity_score = inputs.get("specificity_score", 5)
            confidence = inputs.get("confidence", 0.5)
            
            # Strategy selection logic
            if completeness_score < 6 or specificity_score < 6:
                return "deep_dive"
            elif focus_area in ["leadership", "teamwork", "problem_solving"]:
                return "behavioral"  
            elif confidence > 0.8:
                return "reflection"
            else:
                return "situational"
        
        # Create conditional branches
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
            # Default case
            lambda x: self.followup_chains["situational"]
        )
        
        return selector
    
    async def process_planner_data(
        self,
        planner_data: PlannerToChbotData
    ) -> ChatbotResponse:
        """
        Process JSON data from planner and generate response
        
        Args:
            planner_data: Structured data from planner
            
        Returns:
            ChatbotResponse: Structured response data
        """
        try:
            logger.info(f"[{planner_data.session_id}] Processing planner data with strategy: {planner_data.planner_suggestion.recommended_strategy}")
            
            # Select generation method based on planner's strategy recommendation
            strategy = planner_data.planner_suggestion.recommended_strategy
            
            # Prepare input data, compatible with existing generate_followup method
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
            
            # Call existing generation method
            generation_result = await self.generate_followup(
                analysis=analysis_data,
                user_answer=planner_data.user_input,
                context=planner_data.conversation_context,
                style=planner_data.interview_style,
                session_id=planner_data.session_id
            )
            
            # Convert results to structured ChatbotResponse
            chatbot_response = ChatbotResponse(
                response_text=generation_result["question"],
                response_type="question",
                strategy_used=strategy,
                focus_area=analysis_data["focus_area"],
                alternative_responses=generation_result.get("alternatives", []),
                generation_method=generation_result.get("generation_method", "langchain_powered"),
                confidence=generation_result.get("confidence", 0.7),
                processing_time=None  # Can be added in coordinator
            )
            
            logger.info(f"[{planner_data.session_id}] Successfully generated response using {strategy.value} strategy")
            
            return chatbot_response
            
        except Exception as e:
            logger.error(f"[{planner_data.session_id}] Failed to process planner data: {e}")
            
            # Return fallback response
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
        Process JSON format input data
        
        Args:
            json_data: JSON data containing user input and planner recommendations
            
        Returns:
            Dict: Dictionary containing generated response
        """
        try:
            # Validate and parse JSON data
            planner_data = PlannerToChbotData(**json_data)
            
            # Process data and generate response
            response = await self.process_planner_data(planner_data)
            
            # Convert to compatible dictionary format
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
        Generate follow-up questions using LangChain
        """
        try:
            logger.info(f"[{session_id}] Generating LangChain-powered followup question")
            
            # Prepare input data
            input_data = {
                "user_answer": user_answer,
                "original_question": analysis.get("original_question", ""),
                "context": context or "No previous conversation",
                "focus_area": analysis.get("focus_area", "general"),
                "key_themes": ", ".join(analysis.get("key_themes", [])),
                "interview_style": style,
                "completeness_score": analysis.get("completeness_score", 5),
                "specificity_score": analysis.get("specificity_score", 5),
                "confidence": analysis.get("confidence", 0.5)
            }
            
            # Create run configuration
            config = create_runnable_config(session_id, task="followup_generation")
            
            # Select and execute appropriate chain
            selected_chain_type = self._select_generation_strategy(analysis)
            chain = self.followup_chains[selected_chain_type]
            
            logger.info(f"[{session_id}] Using {selected_chain_type} generation strategy")
            
            # Generate question
            generated_question = await chain.ainvoke(input_data, config=config)
            
            # Post-process question
            final_question = self._post_process_question(generated_question, style)
            
            # Don't generate alternative questions to improve efficiency
            result = {
                "question": final_question,
                "generation_method": f"langchain_{selected_chain_type}",
                "focus_area": analysis.get("focus_area", "general"),
                "confidence": analysis.get("confidence", 0.5),
                "reasoning": f"Using {selected_chain_type} strategy based on analysis",
                "alternatives": [],  # Empty array to maintain API compatibility
                "langchain_powered": True
            }
            
            logger.info(f"[{session_id}] Followup generated: {final_question[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"[{session_id}] LangChain followup generation failed: {e}")
            # Fall back to template generation
            return await self._generate_template_fallback(analysis, user_answer, style, session_id)
    
    def _select_generation_strategy(self, analysis: Dict[str, Any]) -> str:
        """Select generation strategy"""
        focus_area = analysis.get("focus_area", "general")
        completeness_score = analysis.get("completeness_score", 5)
        specificity_score = analysis.get("specificity_score", 5)
        confidence = analysis.get("confidence", 0.5)
        
        # Strategy selection logic
        if completeness_score < 6 or specificity_score < 6:
            return "deep_dive"
        elif focus_area in ["leadership", "teamwork", "problem_solving"]:
            return "behavioral"
        elif confidence > 0.8:
            return "reflection"
        else:
            return "situational"
    
    # Remove alternative question generation methods to improve efficiency
    
    def _post_process_question(self, question: str, style: str) -> str:
        """Post-process generated question"""
        if not question:
            return "Can you tell me more about that experience?"
        
        # Clean question
        cleaned = question.strip()
        
        # Remove possible prefixes
        prefixes_to_remove = [
            "Follow-up question:", "Question:", "Question:",
            "Here's a follow-up question:", "I'd like to ask:"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                break
        
        # Ensure first letter is capitalized
        if cleaned and not cleaned[0].isupper():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Ensure ends with question mark
        if cleaned and not cleaned.endswith('?'):
            cleaned += '?'
        
        # Adjust tone based on style
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
        """Template fallback generation"""
        logger.info(f"[{session_id}] Using template fallback for followup generation")
        
        focus_area = analysis.get("focus_area", "general")
        templates = self.question_templates.get(focus_area, self.question_templates["general"])
        
        # Select appropriate template
        selected_template = random.choice(templates)
        
        # Personalize template
        question = self._personalize_template(selected_template, user_answer)
        
        # Apply style
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
        """Personalize question template"""
        personalized = template
        answer_lower = user_answer.lower()
        
        # Replace template variables
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
        """Load enhanced question templates"""
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
        """Load question generation examples for few-shot learning"""
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
            
            # Test a simple chain
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
            
            # Create test configuration
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