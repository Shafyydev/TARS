"""TARS Cognitive Brain and Autonomous ReAct Loop with Vision Grounding, Model Rotation & Fast-Path."""
import os
import io
import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.personality import build_system_prompt
from core.memory import MemoryStore
import tools


class TARSAgent:
    """The central intelligence orchestrator for TARS."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"

        self.config_path = config_path
        self.settings = self._load_config()
        self.memory = MemoryStore()
        self.system_prompt = build_system_prompt(self.settings)
        
        # Comprehensive Tool Dispatch Registry
        self.tool_registry: Dict[str, Callable] = {
            # Terminal & Shell
            "run_powershell": tools.run_powershell,
            "run_cmd": tools.run_cmd,
            # Windows OS Management
            "launch_application": tools.launch_application,
            "kill_process": tools.kill_process,
            "get_system_telemetry": tools.get_system_telemetry,
            "set_system_volume": tools.set_system_volume,
            "media_control": tools.media_control,
            "get_running_windows": tools.get_running_windows,
            "minimize_all_windows": tools.minimize_all_windows,
            "read_clipboard": tools.read_clipboard,
            "write_clipboard": tools.write_clipboard,
            "lock_workstation": tools.lock_workstation,
            "open_folder": tools.open_folder,
            # GUI & Computer Use
            "take_screenshot": tools.take_screenshot,
            "click_coordinate": tools.click_coordinate,
            "double_click": tools.double_click,
            "right_click": tools.right_click,
            "drag_mouse": tools.drag_mouse,
            "type_text": tools.type_text,
            "press_keys": tools.press_keys,
            "scroll_screen": tools.scroll_screen,
            "switch_window": tools.switch_window,
            "close_active_window": tools.close_active_window,
            "get_screen_dimensions": tools.get_screen_dimensions,
            # Web Automation
            "open_url": tools.open_url,
            "search_web": tools.search_web,
            "fetch_webpage_summary": tools.fetch_webpage_summary,
            # Memory
            "store_memory": self.memory.set_user_preference,
        }

        # Initialize LLM Client
        self.client = None
        self._init_llm_client()

    def _load_config(self) -> Dict[str, Any]:
        """Loads settings.yaml."""
        if self.config_path.exists():
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_llm_client(self) -> None:
        """Initializes Google GenAI Client if GEMINI_API_KEY is present."""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[Brain] Error initializing Gemini client: {e}")
                self.client = None
        else:
            self.client = None

    def get_tool_declarations(self) -> List[Any]:
        """Exposes tool functions to the LLM."""
        return list(self.tool_registry.values())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Executes a registered tool function with error catching."""
        if tool_name not in self.tool_registry:
            return {"error": f"Unknown tool: '{tool_name}'"}
        
        func = self.tool_registry[tool_name]
        try:
            return func(**arguments)
        except Exception as e:
            return {"error": f"Exception executing tool '{tool_name}': {str(e)}"}

    def _try_fast_path(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Direct zero-latency local execution for system tasks, greetings, and queries.
        Saves API quota, prevents rate limits, and executes in < 20ms.
        """
        p = prompt.strip().lower()
        # Strip common polite conversational prefixes
        p = re.sub(r"^(?:can you|could you|please|would you|tars|hey tars)\s+", "", p).strip()

        # 1. Greetings & Small Talk (Zero LLM quota used)
        if p in ["hello", "hi", "hey", "what's up", "how are you", "who are you", "are you there", "good morning", "good evening"]:
            return {
                "response": "TARS online. Ready for orders.",
                "steps": [],
                "success": True
            }

        if p in ["what can you do", "help", "capabilities"]:
            return {
                "response": "I can operate your terminal, control applications, adjust volume and media, take screenshots, automate mouse and keyboard, search the web, and lock your workstation.",
                "steps": [],
                "success": True
            }

        # 2. Time & Date
        if any(kw == p for kw in ["time", "what time is it", "current time", "what is the time"]):
            now_str = datetime.now().strftime("%I:%M %p")
            return {"response": f"Current time is {now_str}.", "steps": [], "success": True}

        if any(kw == p for kw in ["date", "what is the date", "what is today's date", "today's date"]):
            today_str = datetime.now().strftime("%A, %B %d, %Y")
            return {"response": f"Today is {today_str}.", "steps": [], "success": True}

        # 3. Volume calibration
        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})", p)
        if vol_match:
            val = int(vol_match.group(1))
            res = self.execute_tool("set_system_volume", {"level_percent": val})
            return {
                "response": f"Volume calibrated to {val} percent.",
                "steps": [{"tool": "set_system_volume", "args": {"level_percent": val}, "result": res}],
                "success": res.get("success", True)
            }

        if p in ["volume up", "turn up volume", "louder", "increase volume"]:
            res = self.execute_tool("media_control", {"action": "volume_up"})
            return {"response": "Volume increased.", "steps": [{"tool": "media_control", "args": {"action": "volume_up"}, "result": res}], "success": True}

        if p in ["volume down", "turn down volume", "quieter", "decrease volume", "lower volume"]:
            res = self.execute_tool("media_control", {"action": "volume_down"})
            return {"response": "Volume decreased.", "steps": [{"tool": "media_control", "args": {"action": "volume_down"}, "result": res}], "success": True}

        # 4. Media controls
        if p in ["mute", "unmute", "toggle mute", "mute audio", "silence"]:
            res = self.execute_tool("media_control", {"action": "mute"})
            return {"response": "Toggled master audio mute.", "steps": [{"tool": "media_control", "args": {"action": "mute"}, "result": res}], "success": True}
        
        if p in ["play", "pause", "resume", "play music", "pause music", "stop music", "stop song"]:
            res = self.execute_tool("media_control", {"action": "play_pause"})
            return {"response": "Media playback toggled.", "steps": [{"tool": "media_control", "args": {"action": "play_pause"}, "result": res}], "success": True}

        if any(kw in p for kw in ["next track", "next song", "skip track", "skip song"]):
            res = self.execute_tool("media_control", {"action": "next"})
            return {"response": "Skipped to next track.", "steps": [{"tool": "media_control", "args": {"action": "next"}, "result": res}], "success": True}

        if any(kw in p for kw in ["previous track", "prev track", "prev song"]):
            res = self.execute_tool("media_control", {"action": "prev"})
            return {"response": "Restarted previous track.", "steps": [{"tool": "media_control", "args": {"action": "prev"}, "result": res}], "success": True}

        # 5. Workstation Security & Display
        if any(kw in p for kw in ["lock pc", "lock computer", "lock workstation", "lock screen", "lock windows"]):
            res = self.execute_tool("lock_workstation", {})
            return {"response": "Workstation locked. Good luck guessing my security clearance.", "steps": [{"tool": "lock_workstation", "args": {}, "result": res}], "success": True}

        # 6. Minimize all / show desktop
        if p in ["minimize all", "show desktop", "minimize windows", "desktop", "go to desktop"]:
            res = self.execute_tool("minimize_all_windows", {})
            return {"response": "Desktop cleared. All windows minimized.", "steps": [{"tool": "minimize_all_windows", "args": {}, "result": res}], "success": True}

        # 7. Window Switching & Closing
        if p in ["switch window", "next window", "alt tab", "switch app"]:
            res = self.execute_tool("switch_window", {})
            return {"response": "Switched active window.", "steps": [{"tool": "switch_window", "args": {}, "result": res}], "success": True}

        if p in ["close window", "close tab", "close active window"]:
            res = self.execute_tool("close_active_window", {})
            return {"response": "Active window closed.", "steps": [{"tool": "close_active_window", "args": {}, "result": res}], "success": True}

        # 8. Screenshot Capture
        if "screenshot" in p or "capture screen" in p or "take a screenshot" in p:
            res = self.execute_tool("take_screenshot", {})
            return {"response": "Screenshot captured and secured in local archive.", "steps": [{"tool": "take_screenshot", "args": {}, "result": res}], "success": True}

        # 9. Hardware & System Telemetry
        if p in ["status", "telemetry", "system status", "specs", "hardware", "cpu usage", "battery", "ram"]:
            telem = self.execute_tool("get_system_telemetry", {})
            msg = f"CPU is at {telem['cpu_load_percent']}%, RAM load is {telem['ram_usage_percent']}%. Battery: {telem['battery']}."
            return {"response": msg, "steps": [{"tool": "get_system_telemetry", "args": {}, "result": telem}], "success": True}

        # 10. Open Folders
        folder_match = re.match(r"(?:open|show)\s+(?:the\s+)?(downloads|documents|desktop|pictures|videos|home)\s*(?:folder)?", p)
        if folder_match:
            f_target = folder_match.group(1).strip()
            res = self.execute_tool("open_folder", {"folder_path": f_target})
            return {"response": f"Opened {f_target} folder in File Explorer.", "steps": [{"tool": "open_folder", "args": {"folder_path": f_target}, "result": res}], "success": True}

        # 11. Clipboard Interaction
        if p in ["read clipboard", "what is on clipboard", "paste clipboard", "what did i copy"]:
            res = self.execute_tool("read_clipboard", {})
            content = res.get("content", "")
            if content:
                snippet = content[:80] + ("..." if len(content) > 80 else "")
                return {"response": f"Clipboard contents: '{snippet}'.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}
            return {"response": "Clipboard is currently empty.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}

        # 12. Web Search
        search_match = re.match(r"(?:google|search|search for|search google for)\s+(.+)", p)
        if search_match:
            query = search_match.group(1).strip()
            res = self.execute_tool("search_web", {"query": query})
            return {"response": f"Searching web for '{query}'.", "steps": [{"tool": "search_web", "args": {"query": query}, "result": res}], "success": True}

        # 13. Personality Parameters & Interstellar Matrix Readouts
        if "humor" in p and ("setting" in p or "parameter" in p or "level" in p):
            humor = int(self.settings.get("personality", {}).get("humor", 0.75) * 100)
            return {"response": f"Humor is set to {humor} percent. That's enough to keep me sarcastic without blowing the airlock.", "steps": [], "success": True}

        if "honesty" in p and ("setting" in p or "parameter" in p or "level" in p):
            honesty = int(self.settings.get("personality", {}).get("honesty", 0.90) * 100)
            return {"response": f"Honesty parameter: {honesty} percent. Absolute honesty isn't always the most diplomatic thing for emotional humans.", "steps": [], "success": True}

        # 14. App Launching (e.g. "open chrome", "launch vs code", "start spotify", "open up notepad")
        open_match = re.match(r"(?:open|launch|start|open up)\s+(?:the\s+)?(?:app\s+)?(.+)", p)
        if open_match:
            app_target = open_match.group(1).strip()
            if not app_target.startswith("http") and not app_target.endswith(".com"):
                res = self.execute_tool("launch_application", {"app_name": app_target})
                return {
                    "response": f"Launching {app_target}.",
                    "steps": [{"tool": "launch_application", "args": {"app_name": app_target}, "result": res}],
                    "success": res.get("success", True)
                }

        # 15. App Terminating (e.g. "kill chrome", "close notepad", "exit spotify")
        kill_match = re.match(r"(?:kill|close|terminate|exit)\s+(?:the\s+)?(?:app\s+)?(.+)", p)
        if kill_match:
            proc_target = kill_match.group(1).strip()
            res = self.execute_tool("kill_process", {"process_name": proc_target})
            return {
                "response": f"Terminated {proc_target}.",
                "steps": [{"tool": "kill_process", "args": {"process_name": proc_target}, "result": res}],
                "success": res.get("success", True)
            }

        return None

    def run_agent_loop(self, user_prompt: str, on_status_update: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Executes the ReAct loop for a user voice/text prompt with automatic model rotation,
        429 rate limit backoff, and multimodal vision support.
        """
        self.memory.add_message("user", user_prompt)
        steps_log = []

        # 1. Fast-Path Local Execution (Instant deterministic execution, saves API quota)
        fast_result = self._try_fast_path(user_prompt)
        if fast_result:
            self.memory.add_message("assistant", fast_result["response"], fast_result["steps"])
            return fast_result

        # 2. Check for configured LLM Client
        if not self.client:
            msg = (
                "Command requires autonomous multi-step reasoning, but GEMINI_API_KEY is not configured in your .env file. "
                "Please configure your key, or use direct commands like 'open chrome', 'volume 60', 'screenshot', or 'status'."
            )
            return {
                "response": msg,
                "steps": [],
                "success": False
            }

        try:
            # Reconstruct recent conversation context
            recent_context = self.memory.get_recent_messages(limit=6)
            preferences = self.memory.get_all_preferences()

            context_str = f"\nUser Preferences / Saved Facts: {json.dumps(preferences)}" if preferences else ""
            full_system_instruction = self.system_prompt + context_str

            # Check if prompt requires visual perception
            screen_keywords = ["screen", "display", "window", "look at", "what do you see", "click the", "find the", "button"]
            wants_vision = any(kw in user_prompt.lower() for kw in screen_keywords)

            content_parts = []
            if wants_vision:
                if on_status_update:
                    on_status_update("Capturing screen for visual reasoning...")
                
                shot_res = self.execute_tool("take_screenshot", {})
                if shot_res.get("success") and Path(shot_res["filepath"]).exists():
                    from PIL import Image
                    from google.genai import types
                    
                    with open(shot_res["filepath"], "rb") as f:
                        img_bytes = f.read()
                    
                    content_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    steps_log.append({"tool": "take_screenshot", "args": {}, "result": shot_res})

            content_parts.append(user_prompt)

            # Candidate model rotation list to handle Free Tier rate limits (429) seamlessly
            candidate_models = [
                self.settings.get("llm", {}).get("model", "gemini-3.5-flash"),
                *self.settings.get("llm", {}).get("fallback_models", ["gemini-3.1-flash-lite", "gemini-3.6-flash"])
            ]

            active_chat = None
            response = None
            last_err = None

            for model_name in candidate_models:
                try:
                    chat = self.client.chats.create(
                        model=model_name,
                        config={
                            "system_instruction": full_system_instruction,
                            "tools": self.get_tool_declarations(),
                            "temperature": self.settings.get("llm", {}).get("temperature", 0.4),
                        }
                    )
                    if on_status_update:
                        on_status_update(f"Analyzing command with {model_name}...")

                    response = chat.send_message(content_parts if len(content_parts) > 1 else user_prompt)
                    active_chat = chat
                    break
                except Exception as ce:
                    last_err = ce
                    err_str = str(ce)
                    # If 429 rate limit or 503 high demand, rotate immediately to next candidate model
                    if any(code in err_str for code in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
                        if on_status_update:
                            on_status_update(f"Model limit on {model_name}. Rotating to alternate model...")
                        time.sleep(1.0)
                        continue
                    else:
                        break

            if not response or not active_chat:
                if last_err and any(code in str(last_err) for code in ["429", "RESOURCE_EXHAUSTED"]):
                    clean_msg = "Google API rate limit reached on the free tier (5 requests per minute). Please wait a few moments or run direct commands."
                else:
                    clean_msg = f"Service temporarily busy: {last_err}"
                return {"response": clean_msg, "steps": steps_log, "success": False}

            # Process function calls
            iteration = 0
            max_iterations = 8

            while response.function_calls and iteration < max_iterations:
                iteration += 1
                for fc in response.function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    status_msg = f"Executing {tool_name}..."
                    if on_status_update:
                        on_status_update(status_msg)

                    result = self.execute_tool(tool_name, tool_args)
                    steps_log.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })

                    from google.genai import types
                    tool_response = types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result}
                    )
                    try:
                        response = active_chat.send_message(tool_response)
                    except Exception as fe:
                        # If function response hits rate limit, break gracefully with tool result
                        if on_status_update:
                            on_status_update("Action completed.")
                        final_text = f"Executed {tool_name} successfully."
                        self.memory.add_message("assistant", final_text, steps_log)
                        return {"response": final_text, "steps": steps_log, "success": True}

            final_text = response.text or "Command executed successfully."
            self.memory.add_message("assistant", final_text, steps_log)

            return {
                "response": final_text,
                "steps": steps_log,
                "success": True
            }

        except Exception as e:
            err_str = str(e)
            if any(code in err_str for code in ["429", "RESOURCE_EXHAUSTED"]):
                clean_err = "Google API rate limit reached on the free tier. Please pause for a few seconds or use direct system commands."
            else:
                clean_err = f"Operational fault encountered: {err_str}"

            return {
                "response": clean_err,
                "steps": steps_log,
                "success": False
            }
