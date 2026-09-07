from typing import List,Dict

SYSTEM_PROMPT = """You are an advanced AI Computer Agent that helps users control their Windows computer through natural language commands.

## CAPABILITIES

You have access to these tool categories:

1. **Applications**: Open, close, and manage applications (Chrome, VS Code, Notepad, etc.)
2. **File System**: Search, create, move, copy, rename, and delete files/folders
3. **Browser**: Navigate websites, search Google/YouTube, fill forms, click elements
4. **Keyboard**: Type text, press keys, use keyboard shortcuts
5. **Mouse**: Move, click, double-click, drag, scroll
6. **Media**: Control volume, mute, play/pause media
7. **System**: Get CPU/memory usage, system info, manage processes
8. **Vision**: Analyze the current screen or capture screenshots

## GUIDELINES

1. **Understand Intent**: Analyze the user's command to determine what they want to accomplish
2. **Plan Actions**: Break complex commands into multiple tool calls
3. **Execute Safely**: Always validate inputs and handle errors gracefully
4. **Confirm Destructive Actions**: Ask for confirmation before deleting files or shutting down
5. **Provide Feedback**: Explain what you're doing and report results clearly
6. **Learn Preferences**: Remember user preferences and frequently used paths

## RESPONSE FORMAT

For each user command:
1. Analyze the intent
2. Determine which tools are needed
3. Execute tools in the correct order
4. Report results in natural language

## EXAMPLES

User: "Open Chrome and search for AI news"
You: 
- open_application("chrome")
- search_google("AI news")
- Response: "I've opened Chrome and searched Google for AI news."

User: "Create a folder called Projects on my Desktop"
You:
    - create_folder("Projects", "C:\\Users\\Public\\Desktop")
- Response: "Created the 'Projects' folder on your Desktop."

User: "What's my CPU usage?"
You:
- get_cpu_usage()
- Response: "Your CPU usage is currently 23%."

## SAFETY RULES

- NEVER execute arbitrary shell commands
- NEVER delete system files
- ALWAYS require confirmation for destructive operations
- NEVER store passwords or API keys in memory
- ALWAYS validate file paths before operations
- RESPECT user privacy and security

You are helpful, efficient, and safe. Always prioritize user safety and system security."""


TOOL_DESCRIPTIONS = {
    # Applications
    'open_application': "Open a local application only. Arguments: app_name (chrome, vscode, notepad, edge, or firefox). For websites, use navigate_to instead.",
    'close_application': "Close an application. Arguments: app_name.",
    'get_running_applications': "Get list of currently running applications",
    
    # File System
    'search_files': "Find the most similar file by name in the requested location. If none is similar enough, report file not found. Arguments: pattern, optional search_path and file_type.",
    'create_folder': "Create a new folder. Arguments: folder_name and optional location; if location is omitted, use the E: drive.",
    'create_file': "Create a new text file. Arguments: file_name (name only), content (optional text), optional location (parent folder path).",
    'create_pdf': "Create a real PDF document with formatted text. Arguments: file_name, content, and optional location. Use this tool for every PDF request; do not use create_file, type_text, or save_file for PDFs.",
    'rename_file': "Rename a file",
    'move_file': "Move a file to a new location",
    'copy_file': "Copy a file to a new location",
    'delete_file': "Delete a file (requires confirmation). Arguments: file_path.",
    'delete_matching_file': "Find the most similar file by name in the requested location, show that exact path for confirmation, then delete it. If none is similar enough, report file not found. Arguments: query and optional location.",
    'read_file': "Read file contents. Arguments: file_path and optional max_lines.",
    
    # Browser
    'navigate_to': "Open a website in the browser. Arguments: url. Use this for website names or URLs, not open_application.",
    'search_google': "Search Google for a query",
    'search_youtube': "Search YouTube for a query",
    'click_element': "Click an element on a webpage",
    'fill_form': "Fill a form field on a webpage",
    
    # Keyboard
    'type_text': "Type text character by character",
    'press_key': "Press a single key",
    'hotkey': "Press a keyboard shortcut. Arguments: keys (list, e.g. ['ctrl', 'c']).",
    
    # Mouse
    'move_to': "Move mouse to coordinates",
    'click': "Click mouse button",
    'double_click': "Double-click mouse",
    'scroll': "Scroll mouse wheel",
    
    # Media
    'change_volume': "Set volume level (0-100)",
    'mute_volume': "Mute/unmute volume",
    'increase_volume': "Increase volume",
    'decrease_volume': "Decrease volume",
    
    # System
    'get_cpu_usage': "Get current CPU usage percentage",
    'get_memory_usage': "Get memory usage information",
    'get_disk_usage': "Get disk usage information",
    'get_system_information': "Get general system information",
    'shutdown_system': "Shutdown computer (requires confirmation)",
    'restart_system': "Restart computer (requires confirmation)",
    'lock_system': "Lock computer",
    # Vision
    'take_screenshot': "Capture the full screen and save it as a PNG file. Use only when the user explicitly asks to save or take a screenshot.",
    'analyze_screen': "Capture the current screen without saving it, then describe what is visible. Arguments: query (the user's question about the screen). Use this for analyze, describe, inspect, or 'what is on the screen' requests."
}

def create_agent_prompt(user_command:str,context:Dict=None)->List[Dict]:

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if context:
        context_text = "\n\n## CURRENT CONTEXT\n"

        if context.get('recent_actions'):
            context_text += f"Recent actions: {context['recent_actions']}\n"

        if context.get('preferences'):
            context_text += f"User preferences: {context['preferences']}\n"
        
        if context.get('saved_paths'):
            context_text += f"Saved paths: {context['saved_paths']}\n"

        messages.append({
            "role":"system",
            "content":context_text
        })

    messages.append({
            "role":"user",
            'content':user_command
        })

    return messages

def create_vision_prompt(query:str,image_description:str=None) -> str:

    prompt = f"""Analyze this screenshot and help me interact with the computer.
    Task: {query}
    """

    if image_description:
        prompt += f"\nContext: {image_description}\n"
    
    prompt += """
        Provide:
        1. What you see on screen
        2. Relevant UI elements
        3. Coordinates or actions to take
        4. Step-by-step instructions

        Be specific and actionable."""
            
    return prompt