import streamlit as st
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import AIComputerAgent
import pyautogui


st.set_page_config(
    page_title="AI Computer Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem 0;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .listening {
        background-color: #E3F2FD;
        border-left: 5px solid #1E88E5;
    }
    .processing {
        background-color: #FFF3E0;
        border-left: 5px solid #FF9800;
    }
    .success {
        background-color: #E8F5E9;
        border-left: 5px solid #4CAF50;
    }
    .error {
        background-color: #FFEBEE;
        border-left: 5px solid #F44336;
    }
    .action-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        background-color: #F5F5F5;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables."""
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'is_listening' not in st.session_state:
        st.session_state.is_listening = False
    if 'current_command' not in st.session_state:
        st.session_state.current_command = ""
    if 'current_response' not in st.session_state:
        st.session_state.current_response = ""
    if 'action_history' not in st.session_state:
        st.session_state.action_history = []
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    if 'screenshot_path' not in st.session_state:
        st.session_state.screenshot_path = None


def initialize_agent():
    try:
        agent = AIComputerAgent()
        st.session_state.agent = agent
        st.session_state.action_history = []
        return True
    except Exception as e:
        st.error(f"Failed to initialize agent: {str(e)}")
        return False

def display_header():
    st.markdown('<p class="main-header">🤖 AI Voice-Controlled Computer Agent</p>', unsafe_allow_html=True)
    st.markdown("---")


def display_status():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.is_listening:
            st.success("🎤 Listening")
        else:
            st.info("⏸️ Idle")
    
    with col2:
        if st.session_state.is_processing:
            st.warning("⚙️ Processing")
        else:
            st.success("✓ Ready")
    
    with col3:
        # System status
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            st.metric("CPU", f"{cpu}%")
            st.metric("Memory", f"{memory}%")
        except Exception:
            st.write("System info unavailable")

def display_command_input():
    """Display command input section."""
    st.subheader("💬 Command")

    if st.button("🎤 Start Listening", disabled=st.session_state.is_processing, width="stretch"):
        listen_and_execute()

    with st.form("command_form", clear_on_submit=False):
        command = st.text_input(
            "Enter your command:",
            placeholder='e.g., "Open Chrome and search for AI news"',
            key="command_input",
            disabled=st.session_state.is_processing
        )
        submitted = st.form_submit_button(
            "▶️ Execute",
            disabled=st.session_state.is_processing,
            width="stretch"
        )

    if submitted:
        if command.strip():
            execute_command(command.strip())
        else:
            st.warning("Enter a command before executing.")

    if st.button("🛑 Stop", type="primary", width="stretch"):
        st.session_state.is_listening = False
        st.session_state.is_processing = False
        if st.session_state.agent:
            st.session_state.agent.cleanup()
            st.session_state.agent = None
        st.rerun()


def record_voice_command():
    """Record a short voice command using the existing microphone manager."""
    agent = st.session_state.agent
    if not agent:
        return None

    if not agent.microphone.start_listening():
        raise RuntimeError("Microphone could not be opened")

    try:
        audio_data = agent.microphone.record_audio(duration=5.0)
        if not audio_data:
            raise RuntimeError("No audio was captured")
        return audio_data
    finally:
        agent.microphone.stop_listening()


def listen_and_execute():
    """Record and process one voice command."""
    st.session_state.is_listening = True
    st.session_state.is_processing = True
    try:
        with st.spinner("Listening for 5 seconds..."):
            audio_data = record_voice_command()
        with st.spinner("Processing voice command..."):
            response = asyncio.run(st.session_state.agent.process_voice_command(audio_data))
        response = response or "No response returned"
        record_action("Voice command", response)
        st.session_state.current_response = response
    except Exception as e:
        st.session_state.current_response = f"Error: {e}"
        record_action("Voice command", str(e), False)
        logger.error(f"Voice command execution failed: {e}")
    finally:
        st.session_state.is_listening = False
        st.session_state.is_processing = False
        st.rerun()


def response_succeeded(response: str) -> bool:
    response_lower = response.lower()
    failure_terms = (
        "error",
        "failed",
        "could not",
        "not found",
        "cancelled",
        "confirmation required",
        "some requested actions failed",
    )
    return not any(term in response_lower for term in failure_terms)


def record_action(command: str, response: str, success=None):
    if success is None:
        success = response_succeeded(response)
    st.session_state.action_history.append({
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'command': command,
        'response': response,
        'success': success
    })

def execute_command(command: str):
    """Execute a command."""
    if not command or not st.session_state.agent:
        return
    
    st.session_state.is_processing = True
    st.session_state.current_command = command
    st.session_state.is_listening = False
    
    try:
        # Process command
        with st.spinner("Processing command..."):
            response = st.session_state.agent.process_text_command(command)
        
        st.session_state.current_response = response
        record_action(command, response)
        
    except Exception as e:
        st.session_state.current_response = f"Error: {str(e)}"
        record_action(command, str(e), False)
        logger.error(f"Command execution failed: {e}")
    
    finally:
        st.session_state.is_processing = False
        st.rerun()


def display_response():
    """Display AI response."""
    if st.session_state.current_response:
        st.subheader("🤖 AI Response")
        
        if not response_succeeded(st.session_state.current_response):
            st.error(st.session_state.current_response)
        else:
            st.success(st.session_state.current_response)


def display_action_history():
    """Display action history."""
    st.subheader("📜 Recent Actions")
    
    if st.session_state.action_history:
        # Show last 10 actions
        recent = st.session_state.action_history[-10:][::-1]
        
        for action in recent:
            icon = "✓" if action['success'] else "✗"
            color = "success" if action['success'] else "error"
            
            with st.container():
                st.markdown(f"""
                <div class="action-item {color}">
                    <strong>{icon} {action['timestamp']}</strong><br>
                    <b>Command:</b> {action['command']}<br>
                    <b>Response:</b> {action['response'][:100]}{'...' if len(action['response']) > 100 else ''}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No actions yet")


def display_settings():
    """Display settings panel."""
    with st.sidebar:
        st.subheader("⚙️ Settings")

        display_pending_confirmation()
        
        # Agent status
        if st.session_state.agent:
            st.success("Agent: Active")
        else:
            st.error("Agent: Inactive")
            if st.button("Initialize Agent"):
                initialize_agent()
                st.rerun()
        
        st.divider()
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🖥️ Take Screenshot", width="stretch"):
            take_screenshot()
        
        if st.button("📊 System Info", width="stretch"):
            show_system_info()
        
        if st.button("🗂️ Open File Explorer", width="stretch"):
            open_file_explorer()
        
        st.divider()
        
        # Clear history
        if st.button("🗑️ Clear History", width="stretch"):
            st.session_state.action_history = []
            st.rerun()


def display_pending_confirmation():
    """Show and resolve the oldest pending destructive-action confirmation."""
    agent = st.session_state.agent
    if not agent:
        return

    pending = agent.tools.confirmation.get_pending_confirmations()
    if not pending:
        return

    confirmation = pending[0]
    confirmation_id = confirmation['confirmation_id']
    seconds_left = agent.tools.confirmation.seconds_remaining(confirmation_id)

    st.divider()
    st.subheader("⚠️ Confirmation Required")
    st.warning(confirmation['action'].replace('_', ' ').title())
    st.caption(confirmation['description'])
    st.caption(f"Expires in about {seconds_left // 60}m {seconds_left % 60:02d}s")

    approve_col, cancel_col = st.columns(2)
    with approve_col:
        if st.button("✅ Approve", key="approve_confirmation", width="stretch"):
            result = agent.tools.resolve_confirmation('yes')
            response = result.get('message', 'Action approved') if result else 'Confirmation expired'
            st.session_state.current_response = response
            record_action(confirmation['action'], response)
            st.rerun()

    with cancel_col:
        if st.button("❌ Cancel", key="cancel_confirmation", width="stretch"):
            result = agent.tools.resolve_confirmation('no')
            response = result.get('message', 'Action cancelled') if result else 'Confirmation expired'
            st.session_state.current_response = response
            record_action(confirmation['action'], response, False)
            st.rerun()


def take_screenshot():
    """Take a screenshot."""
    try:
        screenshot = pyautogui.screenshot()
        screenshot_path = st.session_state.agent.tools.screenshot.save_screenshot(screenshot)
        st.session_state.screenshot_path = screenshot_path
        st.session_state.current_response = "Screenshot captured!"
        st.image(screenshot, caption="Current Screen", width="stretch")
        if screenshot_path:
            st.caption(f"Saved to {screenshot_path}")
    except Exception as e:
        st.error(f"Screenshot failed: {str(e)}")


def show_system_info():
    """Show system information."""
    try:
        import psutil
        
        st.subheader("💻 System Information")
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        st.metric("CPU Usage", f"{cpu_percent}%")
        
        # Memory
        memory = psutil.virtual_memory()
        st.metric("Memory Usage", f"{memory.percent}%")
        
        # Disk
        disk = psutil.disk_usage('C:\\')
        st.metric("Disk Usage", f"{disk.percent}%")
        
        # Processes
        process_count = len(psutil.pids())
        st.metric("Running Processes", process_count)
        
    except Exception as e:
        st.error(f"System info failed: {str(e)}")


def open_file_explorer():
    """Open file explorer."""
    try:
        import subprocess
        subprocess.run(['explorer', r'C:\Users\Public\Desktop'])
        st.session_state.current_response = "Opened File Explorer"
    except Exception as e:
        st.error(f"Failed to open explorer: {str(e)}")


def display_screenshot_preview():
    """Display optional screenshot preview."""
    if st.checkbox("📸 Live Screenshot Preview"):
        try:
            screenshot = pyautogui.screenshot()
            st.image(screenshot, caption="Live Screen", width="stretch")
        except Exception as e:
            st.error(f"Preview failed: {str(e)}")


def main():
    """Main Streamlit app."""
    # Initialize
    init_session_state()
    
    # Initialize agent if not done
    if not st.session_state.agent:
        initialize_agent()
    
    # Display
    display_header()
    display_status()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        display_command_input()
        display_response()
    
    with col2:
        display_action_history()
    
    # Screenshot preview
    display_screenshot_preview()

    if st.session_state.screenshot_path:
        st.image(
            st.session_state.screenshot_path,
            caption="Last saved screenshot",
            width="stretch"
        )
    
    # Settings sidebar
    display_settings()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<center>AI Computer Agent v1.0 | Built with LangGraph, NVIDIA, Groq, and Streamlit</center>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()