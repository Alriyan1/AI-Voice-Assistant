from typing import List, Dict,Optional,Any
from pydantic import BaseModel,Field
from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from config.settings import settings
from agent.prompts import SYSTEM_PROMPT,TOOL_DESCRIPTIONS
import json
import re

class ToolCall(BaseModel):

    tool_name: str = Field(description="Name of the tool to call")
    arguments: Dict[str,Any] = Field(description="Argument for the tool")
    description: str = Field(description="Human-readable description of what this tool call does")

class ActionPlan(BaseModel):
    tool_calls: List[ToolCall] = Field(description="List of tool calls to execute")
    explanation: str = Field(description="Explanation of the plan")
    requires_confirmation: bool = Field(description='Whether user confirmation is needed ')

class Planner:

    def __init__(self):
        self.llm = ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            temperature=0.1,
            max_tokens=2048
        )

        self.output_parser = PydanticOutputParser(pydantic_object=ActionPlan)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("system", "Available tools: {tool_descriptions}"),
            ("user", "{command}"),
            ("system", "Respond with a JSON action plan.")
        ])

        self.chain = self.prompt| self.llm | self.output_parser

    def create_plan(self,user_command:str,context:Dict=None)->Optional[ActionPlan]:

        try:
            tool_desc = "\n".join([
                f"- {name}: {desc}"
                for name,desc in TOOL_DESCRIPTIONS.items()
            ])

            full_command = user_command
            if context: 
                context_str = f"\n\nContext: {json.dumps(context,indent=2)}"
                full_command += context_str

            response = self.chain.invoke({
                'tool_descriptions':tool_desc,
                'command':full_command
            })

            logger.info(f"Created plan for: {user_command[:50]}...")
            logger.debug(f"Plan: {response.tool_calls}")

            return response

        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            return None

    def validate_plan(self,plan:ActionPlan)->bool:

        try:
            if not isinstance(plan, ActionPlan):
                logger.warning("Plan validation failed: invalid plan object")
                return False

            if not plan.tool_calls:
                logger.warning("Plan validation failed: no tool calls")
                return False

            dangerous_tools = {'delete_file','shutdown_system','restart_system'}
            for tool_call in plan.tool_calls:
                if tool_call.tool_name not in TOOL_DESCRIPTIONS:
                    logger.warning(f"Unknown tool: {tool_call.tool_name}")
                    return False

                if tool_call.tool_name in dangerous_tools and not plan.requires_confirmation:
                    logger.warning(f"Dangerous tool without confirmation: {tool_call.tool_name}")
                    return False

            logger.info("Plan validated successfully")
            return True

        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            return False

    def refine_plan(
            self,
            plan: ActionPlan,
            feedback: str
    )->Optional[ActionPlan]:

        try:
            if plan is None:
                logger.warning("Cannot refine a None plan")
                return None

            tool_desc = "\n".join([
                f"- {name}: {desc}"
                for name, desc in TOOL_DESCRIPTIONS.items()
            ])

            refinement_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are refining an action plan based on user feedback. Keep the user's objective and revise the tool sequence, arguments, and confirmation requirement where needed. Only use the provided tools."),
                ("system", "Available tools: {tool_descriptions}"),
                ("user", "Original plan explanation: {explanation}\nOriginal tool calls: {tool_calls}\nFeedback: {feedback}\nReturn a complete revised JSON action plan.")
            ])

            refined_plan = (refinement_prompt | self.llm | self.output_parser).invoke({
                'tool_descriptions': tool_desc,
                'explanation': plan.explanation,
                'tool_calls': json.dumps([tool_call.model_dump() for tool_call in plan.tool_calls], indent=2),
                'feedback': feedback,
            })

            if not self.validate_plan(refined_plan):
                logger.warning("Refined plan is invalid; keeping the original plan")
                return plan

            logger.info("Plan refined based on feedback")
            return refined_plan

        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            try:
                raw_response = self.llm.invoke(
                    f"""
Original plan: {plan.explanation}
Tool calls: {json.dumps([tool_call.model_dump() for tool_call in plan.tool_calls], indent=2)}
Feedback: {feedback}

Refine the plan to address the feedback. Return improved JSON plan.
"""
                )
                raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                if match:
                    raw_text = match.group(1)
                refined_plan = self.output_parser.parse(raw_text)

                if not self.validate_plan(refined_plan):
                    logger.warning("Fallback refined plan is invalid; keeping the original plan")
                    return plan

                logger.info("Plan refined successfully from fallback parsing")
                return refined_plan

            except Exception as fallback_error:
                logger.error(f"Fallback plan refinement failed: {fallback_error}")
                return plan
