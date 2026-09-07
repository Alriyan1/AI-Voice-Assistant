from typing import TypedDict,List,Dict,Any,Optional
from pathlib import Path
from langgraph.graph import StateGraph,END
from loguru import logger
from agent.planner import Planner,ActionPlan
from agent.memory import AgentMemory
from agent.prompts import create_agent_prompt
import time

class AgentState(TypedDict):

    user_command: str
    context: Dict
    plan: Optional[ActionPlan]
    execution_results: List[Dict]
    response: str
    requires_confirmation: bool
    confirmed: bool
    error: Optional[str]

class VoiceAgent:

    def __init__(self,tools_manager):
        self.tools = tools_manager
        self.planner = Planner()
        self.memory = AgentMemory()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:

        graph = StateGraph(AgentState)

        graph.add_node('understand',self.understand_command)
        graph.add_node('plan',self.create_plan)
        graph.add_node('check_confirmation',self.check_confirmation)
        graph.add_node('execute',self.execute_plan)
        graph.add_node('verify',self.verify_results)
        graph.add_node('respond',self.generate_response)
        graph.add_node('handle_error',self.handle_error)

        graph.set_entry_point('understand')
        graph.add_edge('understand','plan')
        graph.add_edge('plan','check_confirmation')
        graph.add_conditional_edges(
            'check_confirmation',
            self.route_confirmation
        )        
        graph.add_edge('execute','verify')
        graph.add_edge('verify','respond')
        graph.add_edge('respond',END)
        graph.add_edge('handle_error','respond')

        graph.add_conditional_edges(
            'verify',
            self.route_retry
        )

        return graph.compile()

    def understand_command(self,state:AgentState)->AgentState:

        logger.info(f"Understanding command: {state['user_command']}")

        context = self.memory.get_context_for_agent()
        state['context'] = context

        self.memory.add_to_short_term({
            'command':state['user_command'],
            'timestamp': time.monotonic()
        })

        return state

    def create_plan(self,state: AgentState)->AgentState:

        logger.info('Creating action plan')

        plan = self.planner.create_plan(
            state['user_command'],
            state['context']
        )

        if plan:
            if self.planner.validate_plan(plan):
                if self._is_screen_analysis_request(state['user_command']):
                    plan.tool_calls = [
                        type(plan.tool_calls[0])(
                            tool_name='analyze_screen',
                            arguments={'query': state['user_command']},
                            description='Capture and analyze the current screen'
                        )
                    ]
                elif self._is_delete_request(state['user_command']):
                    first_call = plan.tool_calls[0]
                    if first_call.tool_name == 'search_files':
                        query = first_call.arguments.get('query', state['user_command'])
                        plan.tool_calls = [
                            type(first_call)(
                                tool_name='delete_matching_file',
                                arguments={'query': query},
                                description='Find and delete the matching Desktop file'
                            )
                        ]
                        plan.requires_confirmation = True
                elif self._is_pdf_request(state['user_command']):
                    first_call = plan.tool_calls[0]
                    content = first_call.arguments.get(
                        'content',
                        f"{state['user_command']}\n\nCreated by AI Voice Assistant."
                    )
                    plan.tool_calls = [
                        type(first_call)(
                            tool_name='create_pdf',
                            arguments={
                                'file_name': first_call.arguments.get(
                                    'file_name', 'document.pdf'
                                ),
                                'content': content,
                                'location': first_call.arguments.get(
                                        'location', r'C:\Users\Public\Desktop'
                                )
                            },
                            description='Create the requested PDF document'
                        )
                    ]
                state['plan'] = plan
                state['requires_confirmation'] = plan.requires_confirmation
            else:
                state['error'] = "Invalid plan generation"
        else:
            state['error'] = "Failed to create plan"

        return state

    @staticmethod
    def _is_screen_analysis_request(command: str) -> bool:
        command_lower = command.lower()
        analysis_terms = ('analyze', 'analyse', 'describe', 'inspect', 'what is on')
        screen_terms = ('screen', 'window', 'display', 'desktop')
        return (
            any(term in command_lower for term in analysis_terms)
            and any(term in command_lower for term in screen_terms)
        )

    @staticmethod
    def _is_delete_request(command: str) -> bool:
        return any(term in command.lower() for term in ('delete', 'remove', 'erase'))

    @staticmethod
    def _is_pdf_request(command: str) -> bool:
        command_lower = command.lower()
        return 'pdf' in command_lower or 'portable document' in command_lower

    def check_confirmation(self,state:AgentState)->AgentState:
        state['confirmed'] = True
        return state

    def execute_plan(self,state:AgentState)-> AgentState:
        logger.info("Executing plan")

        results = []
        plan = state['plan']

        if not plan:
            state['error'] = "No plan to execute"

            return state

        for tool_call in plan.tool_calls:
            try:
                result = self.tools.execute_tool(
                    tool_call.tool_name,
                    tool_call.arguments
                )
                result_success = (
                    result.get('success', False)
                    if isinstance(result, dict)
                    else getattr(result, 'success', True)
                )

                results.append({
                    'tool': tool_call.tool_name,
                    'arguments': tool_call.arguments,
                    'result':result,
                    'success': result_success
                })

                self.memory.log_action(
                    state['user_command'],
                    tool_call.tool_name,
                    tool_call.arguments,
                    str(result),
                    result_success
                )

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append({
                    'tool': tool_call.tool_name,
                    'error': str(e),
                    'success':False
                })

        state['execution_results'] = results
        return state

    def verify_results(self,state:AgentState)->AgentState:

        logger.info('Verifying results')

        results = state.get('execution_results', [])

        if not results:
            state['error'] = "No results to verify"
            state['response'] = "I ran the plan, but no tool results were returned to verify."
            return state

        failed = [r for r in results if not r.get('success', False)]
        if failed:
            confirmation = next(
                (
                    result for result in failed
                    if isinstance(result.get('result'), dict)
                    and result['result'].get('confirmation_id')
                ),
                None
            )
            if confirmation:
                state['error'] = 'Awaiting tool confirmation'
                state['response'] = confirmation['result'].get(
                    'message', 'Please confirm before I continue.'
                )
                return state
            logger.warning(f"{len(failed)} tool(s) failed")
            state['error'] = f"{len(failed)} tool(s) failed during execution"
            state['response'] = "Some requested actions failed. I should retry or report the partial result clearly."
            return state

        state['error'] = None
        state['response'] = "The requested actions were completed successfully."
        return state

    def generate_response(self,state:AgentState)->AgentState:
        logger.info('Generating response')

        results = state['execution_results']

        if state.get('error') in {'Awaiting user confirmation', 'Awaiting tool confirmation'}:
            response = state.get('response', 'Please confirm before I continue.')
        elif state.get('error'):
            response = f"I encountered an error: {state['error']}"

        elif not results:
            response = "I'm ready to help! What would you like me to do?"
        else:

            response_parts = []

            for result in results:
                if result.get('success'):
                    tool_name = result['tool']
                    result_data = result.get('result',{})
                    if hasattr(result_data, 'model_dump'):
                        result_data = result_data.model_dump()

                    if isinstance(result_data,dict):
                        msg = result_data.get('message',f"Completed {tool_name}")
                    else:
                        msg = f"Completed {tool_name}"

                    response_parts.append(msg)

                else:
                    result_data = result.get('result')
                    if hasattr(result_data, 'message'):
                        error = result_data.message
                    elif isinstance(result_data, dict):
                        error = result_data.get('message', result.get('error', 'Unknown error'))
                    else:
                        error = result.get('error', 'Unknown error')
                    response_parts.append(f"Failed: {error}")

            response = " ".join(response_parts)

        state['response'] = response

        self.memory.db.save_conversation(
            state['user_command'],
            response,
            [r['tool'] for r in results],
            all(r.get('success',False) for r in results)
        )

        return state

    def handle_error(self,state:AgentState) -> AgentState:
        logger.error(f"Error: {state.get('error')}")
        state['response'] = f"I encountered an error: {state.get('error')}"
        return state

    def route_confirmation(self,state:AgentState)->str:
        if state.get('error') and state['error'] != 'Awaiting user confirmation':
            return 'handle_error'

        if state['requires_confirmation'] and not state.get('confirmed',False):
            return 'respond' # Ask for confirmation

        return 'execute'

    def route_retry(self, state: AgentState) -> str:
        return "respond"

    def process_command(self, user_command: str) -> str:

        try:
            initial_state = AgentState(
                user_command=user_command,
                context={},
                plan=None,
                execution_results=[],
                response="",
                requires_confirmation=False,
                confirmed=False,
                error=None
            )
            
            result = self.graph.invoke(initial_state)
            return result['response']
            
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            return f"I encountered an error: {str(e)}"