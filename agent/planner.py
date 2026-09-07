from typing import List, Dict,Optional,Any
from pydantic import BaseModel,Field
from loguru import logger
from langchain_openai import ChatOpenAI
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
    tool_calls: List[ToolCall] = Field(min_length=1, description="At least one tool call to execute")
    explanation: str = Field(description="Explanation of the plan")
    requires_confirmation: bool = Field(description='Whether user confirmation is needed ')

class Planner:

    def __init__(self):
        if settings.nvidia_api_key:
            self.llm = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.nvidia_api_key,
                base_url=settings.nvidia_base_url,
                temperature=0.1,
                max_tokens=2048
            )
            logger.info(f'Using NVIDIA model for planning: {settings.llm_model}')
        elif settings.groq_api_key:
            from langchain_groq import ChatGroq

            self.llm = ChatGroq(
                model='openai/gpt-oss-120b',
                api_key=settings.groq_api_key,
                temperature=0.1,
                max_tokens=2048
            )
            logger.warning('NVIDIA key unavailable; using Groq fallback for planning')
        else:
            raise RuntimeError('NVIDIA_API_KEY is required; GROQ_API_KEY is only an optional fallback')

        self.output_parser = PydanticOutputParser(pydantic_object=ActionPlan)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("system", "Available tools: {tool_descriptions}"),
            ("system", "Return only a JSON object matching this schema. You MUST include at least one tool call for every actionable user request; never return an empty tool_calls list.\n{format_instructions}"),
            ("user", "{command}"),
        ])

        self.chain = self.prompt| self.llm | self.output_parser

    @staticmethod
    def _parse_plan_response(response: Any) -> ActionPlan:
        content = response.content if hasattr(response, 'content') else str(response)
        if isinstance(content, list):
            content = ''.join(
                part.get('text', '') if isinstance(part, dict) else str(part)
                for part in content
            )

        content = str(content).strip()
        fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if fenced:
            content = fenced.group(1)
        else:
            start = content.find('{')
            end = content.rfind('}')
            if start < 0 or end <= start:
                raise ValueError('Model response did not contain a JSON object')
            content = content[start:end + 1]

        payload = json.loads(content)
        if '$defs' in payload or 'properties' in payload:
            raise ValueError('Model returned the ActionPlan schema instead of an action plan')
        return ActionPlan.model_validate(payload)

    def _request_plan(self, request: Dict[str, str]) -> ActionPlan:
        response = (self.prompt | self.llm).invoke(request)
        try:
            return self._parse_plan_response(response)
        except Exception as first_error:
            logger.warning(f'Invalid plan JSON; requesting a corrected action plan: {first_error}')
            correction = (
                'Return one JSON object that is an INSTANCE of the ActionPlan schema. '
                'Never return the schema, $defs, properties, markdown, or explanations outside JSON. '
                'The object must contain tool_calls, explanation, and requires_confirmation.\n\n'
                f'Original request: {request["command"]}\n\n'
                f'Available tools: {request["tool_descriptions"]}'
            )
            corrected_response = self.llm.invoke(correction)
            return self._parse_plan_response(corrected_response)

    def _switch_to_groq_fallback(self) -> bool:
        if not settings.groq_api_key or self.llm.__class__.__name__ == 'ChatGroq':
            return False

        from langchain_groq import ChatGroq

        self.llm = ChatGroq(
            model='openai/gpt-oss-120b',
            api_key=settings.groq_api_key,
            temperature=0.1,
            max_tokens=2048
        )
        self.chain = self.prompt | self.llm | self.output_parser
        logger.warning('NVIDIA authorization failed; switched planning to Groq fallback')
        return True

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

            request = {
                'tool_descriptions': tool_desc,
                'format_instructions': self.output_parser.get_format_instructions(),
                'command': full_command
            }

            try:
                response = self._request_plan(request)
            except Exception as error:
                error_text = str(error).lower()
                provider_error = (
                    '403' in error_text
                    or '404' in error_text
                    or 'authorization' in error_text
                    or 'not found' in error_text
                )
                plan_format_error = (
                    'json' in error_text
                    or 'actionplan' in error_text
                    or 'delimiter' in error_text
                    or 'model response' in error_text
                )
                if not provider_error and not plan_format_error:
                    raise
                if not self._switch_to_groq_fallback():
                    raise
                response = self._request_plan(request)

            logger.info(f"Created plan for: {user_command[:50]}...")
            logger.debug(f"Plan: {response.tool_calls}")

            dangerous_tools = {
                'delete_file',
                'delete_matching_file',
                'move_file',
                'rename_file',
                'shutdown_system',
                'restart_system',
                'lock_system',
            }
            if any(call.tool_name in dangerous_tools for call in response.tool_calls):
                response.requires_confirmation = True

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

            dangerous_tools = {
                'delete_file',
                'delete_matching_file',
                'move_file',
                'rename_file',
                'shutdown_system',
                'restart_system',
                'lock_system',
            }
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
                ("system", "Return only a JSON object matching this schema:\n{format_instructions}"),
                ("user", "Original plan explanation: {explanation}\nOriginal tool calls: {tool_calls}\nFeedback: {feedback}\nReturn a complete revised JSON action plan.")
            ])

            refined_plan = (refinement_prompt | self.llm | self.output_parser).invoke({
                'tool_descriptions': tool_desc,
                'format_instructions': self.output_parser.get_format_instructions(),
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
Use this exact output schema:
{self.output_parser.get_format_instructions()}
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
