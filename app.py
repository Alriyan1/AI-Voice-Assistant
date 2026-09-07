import asyncio
import inspect
from pathlib import Path
import threading
from typing import Dict,Any,Optional
from loguru import logger
from config.settings import settings
from speech.stt import SpeechToText
from speech.microphone import MicrophoneManager
from speech.tts import TextToSpeech
from agent.graph import VoiceAgent
from tools.applications import ApplicationTools
from tools.filesystem import FilesystemTools
from tools.browser import BrowserTools
from tools.keyboard import KeyboardTools
from tools.mouse import MouseTools
from tools.media import MediaTools
from tools.system import SystemTools
from vision.screen_analyzer import ScreenAnalyzer
from vision.screenshot import ScreenshotManager
from security.permission import PermissionManager
from security.confirmation import ConfirmationManager


class ToolsManager:

    def __init__(self):
        """Initialize tools manager."""
        self.applications = ApplicationTools()
        self.filesystem = FilesystemTools()
        self.browser = BrowserTools()
        self.keyboard = KeyboardTools()
        self.mouse = MouseTools()
        self.media = MediaTools()
        self.system = SystemTools()
        self.screenshot = ScreenshotManager()
        self.screen_analyzer = ScreenAnalyzer()
        self.permissions = PermissionManager()
        self.confirmation = ConfirmationManager()
        self._async_loop = None
        self._async_thread = None
        self._confirmed_result = None
        
        # Tool mapping
        self.tools = {
            # Applications
            'open_application': self.applications.open_application,
            'close_application': self.applications.close_application,
            'get_running_applications': self.applications.get_running_applications,
            
            # Filesystem
            'search_files': self.filesystem.search_files,
            'create_folder': self.filesystem.create_folder,
            'create_file': self.filesystem.create_file,
            'create_pdf': self.filesystem.create_pdf,
            'rename_file': self.filesystem.rename_file,
            'move_file': self.filesystem.move_file,
            'copy_file': self.filesystem.copy_file,
            'delete_file': self.filesystem.delete_file,
            'delete_matching_file': self.filesystem.delete_matching_file,
            'read_file': self.filesystem.read_file,
            
            # Browser (async)
            'navigate_to': self.browser.navigate_to,
            'search_google': self.browser.search_google,
            'search_youtube': self.browser.search_youtube,
            'click_element': self.browser.click_element,
            'fill_form': self.browser.fill_form,
            
            # Keyboard
            'type_text': self.keyboard.type_text,
            'press_key': self.keyboard.press_key,
            'hotkey': self.keyboard.hotkey,
            
            # Mouse
            'move_to': self.mouse.move_to,
            'click': self.mouse.click,
            'double_click': self.mouse.double_click,
            'scroll': self.mouse.scroll,
            
            # Media
            'change_volume': self.media.change_volume,
            'mute_volume': self.media.mute_volume,
            'increase_volume': self.media.increase_volume,
            'decrease_volume': self.media.decrease_volume,
            
            # System
            'get_cpu_usage': self.system.get_cpu_usage,
            'get_memory_usage': self.system.get_memory_usage,
            'get_disk_usage': self.system.get_disk_usage,
            'get_system_information': self.system.get_system_information,
            'shutdown_system': self.system.shutdown_system,
            'restart_system': self.system.restart_system,
            'lock_system': self.system.lock_system,

            # Screenshot
            'take_screenshot': self.take_screenshot,
            'analyze_screen': self.analyze_screen,
        }

    def take_screenshot(self) -> Dict[str, Any]:
        """Capture the full screen and save it as a PNG file."""
        filepath = self.screenshot.capture_and_save()
        if filepath:
            return {
                'success': True,
                'message': f'Screenshot captured and saved to {filepath}',
                'path': filepath,
            }

        return {
            'success': False,
            'message': 'Screenshot capture failed',
        }

    def analyze_screen(self, query: str = "Describe what is on the screen") -> Dict[str, Any]:
        """Capture the current screen and return a vision-model description."""
        image = self.screenshot.capture_screen()
        if image is None:
            return {
                'success': False,
                'message': 'Could not capture the screen for analysis',
            }

        analysis = self.screen_analyzer.analyzer_screen(image, query)
        if analysis:
            return {
                'success': True,
                'message': analysis,
            }

        return {
            'success': False,
            'message': 'The screen was captured, but vision analysis failed',
        }

    def execute_tool(self,tool_name: str,arguments:Dict)->Any:

        try:
            arguments = dict(arguments)
            if (
                tool_name == 'press_key'
                and str(arguments.get('key', '')).lower().replace('_', '')
                in {'printscreen', 'prtsc', 'prtscr'}
            ):
                logger.info('Redirecting Print Screen request to direct screenshot capture')
                tool_name = 'take_screenshot'
                arguments = {}

            if tool_name == 'create_file' and 'path' in arguments and 'file_name' not in arguments:
                target_path = Path(arguments.pop('path'))
                arguments['file_name'] = target_path.name
                arguments.setdefault('location', str(target_path.parent))
            elif tool_name == 'search_files':
                if 'query' in arguments and 'pattern' not in arguments:
                    arguments['pattern'] = arguments.pop('query')
                if 'location' in arguments and 'search_path' not in arguments:
                    arguments['search_path'] = arguments.pop('location')
            elif tool_name in {'read_file', 'delete_file'} and 'path' in arguments:
                arguments['file_path'] = arguments.pop('path')
            if tool_name in {'open_application', 'close_application'} and 'application_name' in arguments:
                arguments['app_name'] = arguments.pop('application_name')

            if tool_name == 'delete_file' and arguments.get('file_path'):
                resolved_path = self.filesystem._resolve_file_path(arguments['file_path'])
                if not resolved_path.exists():
                    closest = self.filesystem.find_best_file(
                        query=resolved_path.name,
                        location=str(resolved_path.parent)
                    )
                    if closest.success and closest.path:
                        resolved_path = Path(closest.path)
                arguments['file_path'] = str(resolved_path)

            if tool_name == 'delete_matching_file':
                match = self.filesystem.find_best_file(
                    query=arguments.get('query', ''),
                    location=arguments.get('location')
                )
                if not match.success or not match.path:
                    return match.model_dump()
                tool_name = 'delete_file'
                arguments = {
                    'file_path': match.path,
                    'require_confirmation': True,
                }

            permission = self.permissions.check_permission(
                tool_name,
                arguments.get('app_name') or arguments.get('file_path')
            )

            if not permission.allowed:
                logger.warning(f"Permission denied: {tool_name}")
                return {'success': False,'message':permission.reason}

            tool_func = self.tools.get(tool_name)
            if not tool_func:
                logger.error(f"Unknown tool: {tool_name}")
                return {'success': False, 'message': f'Unknown tool: {tool_name}'}

            if permission.requires_confirmation:
                logger.info(f"Confirmation required: {tool_name}")

                def execute_after_confirmation():
                    confirmed_arguments = dict(arguments)
                    if tool_name in {'delete_file', 'delete_matching_file'}:
                        confirmed_arguments['require_confirmation'] = False
                    self._confirmed_result = tool_func(**confirmed_arguments)

                confirmation_id = self._run_async(
                    self.confirmation.request_confirmation(
                        action=tool_name,
                        description=f"Arguments: {arguments}",
                        callback=execute_after_confirmation
                    )
                )
                if not confirmation_id:
                    return {
                        'success': False,
                        'message': 'Unable to request confirmation'
                    }

                return {
                    'success': False,
                    'message': f'Confirmation required before executing this tool. Say yes to continue (ID: {confirmation_id})',
                    'confirmation_id': confirmation_id
                }
            
            if tool_name == 'hotkey' and 'keys' in arguments:
                result = tool_func(*arguments['keys'])
            else:
                result = tool_func(**arguments)
            if inspect.isawaitable(result):
                result = self._run_async(result)
            
            self.permissions.log_action(
                tool_name,
                str(arguments),
                result.get('success', False)
                if isinstance(result, dict)
                else getattr(result, 'success', True),
                "user_command"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {'success': False, 'message': str(e)}

    def resolve_confirmation(self, answer: str) -> Optional[Dict[str, Any]]:
        """Approve or deny the oldest pending confirmation from a user reply."""
        answer_lower = answer.lower().strip()
        pending = self.confirmation.get_pending_confirmations()
        if not pending:
            return None

        confirmation_id = pending[0]['confirmation_id']
        affirmative = (
            answer_lower in {'yes', 'y', 'confirm', 'proceed', 'do it'}
            or answer_lower.startswith(('yes ', 'yes,', 'confirm ', 'proceed '))
        )
        negative = (
            answer_lower in {'no', 'n', 'cancel', 'stop'}
            or answer_lower.startswith(('no ', 'no,', 'cancel ', 'stop '))
        )

        if affirmative:
            self._confirmed_result = None
            approved = self.confirmation.confirm(confirmation_id)
            if approved and self._confirmed_result is not None:
                result = self._confirmed_result
                return result.model_dump() if hasattr(result, 'model_dump') else result
            return {'success': False, 'message': 'The confirmed action could not be completed'}

        if negative:
            self.confirmation.deny(confirmation_id)
            return {'success': False, 'message': 'Action cancelled'}

        return None

    def _run_async(self, awaitable: Any) -> Any:
        if self._async_loop is None:
            self._async_loop = asyncio.new_event_loop()
            self._async_thread = threading.Thread(
                target=self._async_loop.run_forever,
                daemon=True
            )
            self._async_thread.start()

        future = asyncio.run_coroutine_threadsafe(awaitable, self._async_loop)
        return future.result()

    async def execute_async_tool(self, tool_name: str, arguments: Dict) -> Any:
        try:
            if tool_name == 'navigate_to':
                return await self.browser.navigate_to(arguments['url'])
            elif tool_name == 'search_google':
                return await self.browser.search_google(arguments['query'])
            elif tool_name == 'search_youtube':
                return await self.browser.search_youtube(arguments['query'])
            else:
                return self.execute_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Async tool failed: {e}")
            return {'success': False, 'message': str(e)}


class AIComputerAgent:

    def __init__(self):
        logger.info('Initializing AI Computer Agent')

        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.microphone = MicrophoneManager()
        self.tools = ToolsManager()
        self.agent = VoiceAgent(self.tools)

        logger.info("AI Computer Agent initialized")

    async def process_voice_command(self,audio_data:bytes)->Optional[str]:

        try:
            text = self.stt.transcribe_audio(audio_data)

            if not text:
                return 'I could not understand your command. Please try again.'

            logger.info(f"Transcribed: {text}")

            confirmation_result = self.tools.resolve_confirmation(text)
            if confirmation_result is not None:
                response = confirmation_result.get('message', 'Confirmation handled')
                await self.tts.speak(response)
                return response

            response = self.agent.process_command(text)

            await self.tts.speak(response)

            return response

        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            return f"I encountered an error: {str(e)}"


    def process_text_command(self,text:str)->str:
        try:
            confirmation_result = self.tools.resolve_confirmation(text)
            if confirmation_result is not None:
                response = confirmation_result.get('message', 'Confirmation handled')
                asyncio.run(self.tts.speak(response))
                return response

            response = self.agent.process_command(text)

            asyncio.run(self.tts.speak(response))

            return response

        except Exception as e:
            logger.error(f"Text command processing failed: {e}")
            return f"I encountered an error: {str(e)}"

    def start_listening(self)->None:

        try:
            if not self.microphone.start_listening():
                print('Microphone could not be opened. Use --list-devices to inspect available inputs.')
                return

            logger.info("Listening started. Speak your command...")
            print('Listening for 5 seconds... speak now.')

            audio_data = self.microphone.record_audio(duration=5.0)

            if audio_data:
                response = asyncio.run(self.process_voice_command(audio_data))
                print(f"AI: {response}")
            else:
                print('No audio was captured. Check Windows microphone permissions and input device.')

        except Exception as e:
            logger.error(f"Listening failed: {e}")
        finally:
            self.microphone.stop_listening()


    def cleanup(self)->None:

        logger.info("Cleaning up resources")
        self.microphone.cleanup()
        asyncio.run(self.tools.browser.close())


def main():
    import sys

    logger.add(
        settings.log_dir / 'agent.log',
        level=settings.log_level,
        rotation='10 MB'
    )

    agent = AIComputerAgent()

    try:
        if len(sys.argv) > 1 and sys.argv[1].lower() in {'--voice', '-v'}:
            agent.start_listening()
        elif len(sys.argv) > 1 and sys.argv[1].lower() == '--list-devices':
            for device in agent.microphone.list_devices():
                print(f"[{device['index']}] {device['name']} ({device['channels']} input channels)")
        elif len(sys.argv) > 1:
            command = ' '.join(sys.argv[1:])
            print(f"Processing: {command}")
            response = agent.process_text_command(command)
            print(f"AI: {response}")
        else:
            print("=" * 60)
            print("🤖 AI Voice-Controlled Computer Agent")
            print("=" * 60)
            print("\nCommands:")
            print("  - Speak a command (5 seconds to speak)")
            print("  - Type 'quit' to exit")
            print("  - Type 'help' for examples")
            print("=" * 60)

            while True:
                try:
                    print("\n🎤 Listening... (or type command)")
                    user_input = input("> ").strip()

                    if user_input.lower() in ['quit','exit','q']:
                        print('Goodbye')
                        break

                    if user_input.lower() == 'help':
                        print("\nExample commands:")
                        print("  - Open Chrome")
                        print("  - Search YouTube for Python tutorials")
                        print("  - Create a folder called Projects on Desktop")
                        print("  - What's my CPU usage?")
                        print("  - Take a screenshot")
                        print("  - Mute the computer")
                        print("  - Open VS Code and type Hello World")
                        continue

                    if not user_input:
                        agent.start_listening()
                    else:
                        response = agent.process_text_command(user_input)
                        print(f"\n🤖 AI: {response}")

                except KeyboardInterrupt:
                    print("\n\nInterruped. Goodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    print(f"Error: {str(e)}")

    finally:
        agent.cleanup()

if __name__ == "__main__":
    main()
