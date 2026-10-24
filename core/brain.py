"""TARS Cognitive Brain and Autonomous ReAct Loop."""
import os
import json
import yaml
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
        
        # Tool Dispatch Registry
        self.tool_registry: Dict[str, Callable] = {
            "run_powershell": tools.run_powershell,
            "run_cmd": tools.run_cmd,
            "launch_application": tools.launch_application,
            "kill_process": tools.kill_process,
            "get_system_telemetry": tools.get_system_telemetry,
            "set_system_volume": tools.set_system_volume,
            "media_control": tools.media_control,
            "get_running_windows": tools.get_running_windows,
            "minimize_all_windows": tools.minimize_all_windows,
            "read_clipboard": tools.read_clipboard,
            "write_clipboard": tools.write_clipboard,
            "take_screenshot": tools.take_screenshot,
            "click_coordinate": tools.click_coordinate,
            "type_text": tools.type_text,
            "press_keys": tools.press_keys,
            "scroll_screen": tools.scroll_screen,
            "get_screen_dimensions": tools.get_screen_dimensions,
            "open_url": tools.open_url,
            "search_web": tools.search_web,
            "fetch_webpage_summary": tools.fetch_webpage_summary,
            "store_memory": self.memory.set_user_preference,
        }

        # Initialize LLM Client
        self.client = None
        self._init_llm_client()

    def _load_config(self) -> Dict[str, Any]:
        """Loads settings.yaml."""
        if self.config_path.exists():
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
        Attempts direct local execution for unambiguous system commands with zero latency.
        """
        import re
        p = prompt.strip().lower()

        # Volume control (e.g., "set volume to 50", "volume 75")
        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})", p)
        if vol_match:
            val = int(vol_match.group(1))
            res = self.execute_tool("set_system_volume", {"level_percent": val})
            return {
                "response": f"Volume calibrated to {val} percent.",
                "steps": [{"tool": "set_system_volume", "args": {"level_percent": val}, "result": res}],
                "success": res.get("success", True)
            }

        # Media playback
        if p in ["mute", "unmute", "toggle mute"]:
            res = self.execute_tool("media_control", {"action": "mute"})
            return {"response": "Toggled master audio mute.", "steps": [{"tool": "media_control", "args": {"action": "mute"}, "result": res}], "success": True}
        
        if p in ["play", "pause", "resume", "play music", "pause music"]:
            res = self.execute_tool("media_control", {"action": "play_pause"})
            return {"response": "Media playback toggled.", "steps": [{"tool": "media_control", "args": {"action": "play_pause"}, "result": res}], "success": True}

        if any(kw in p for kw in ["next track", "next song", "skip track", "skip song"]):
            res = self.execute_tool("media_control", {"action": "next"})
            return {"response": "Skipped to next track.", "steps": [{"tool": "media_control", "args": {"action": "next"}, "result": res}], "success": True}

        if any(kw in p for kw in ["previous track", "prev track", "prev song"]):
            res = self.execute_tool("media_control", {"action": "prev"})
            return {"response": "Restarted previous track.", "steps": [{"tool": "media_control", "args": {"action": "prev"}, "result": res}], "success": True}

        # Minimize all / show desktop
        if p in ["minimize all", "show desktop", "minimize windows", "desktop"]:
            res = self.execute_tool("minimize_all_windows", {})
            return {"response": "Desktop cleared. All windows minimized.", "steps": [{"tool": "minimize_all_windows", "args": {}, "result": res}], "success": True}

        # Screenshot
        if "screenshot" in p or "capture screen" in p:
            res = self.execute_tool("take_screenshot", {})
            path = res.get("filepath", "saved")
            return {"response": f"Screenshot captured and secured.", "steps": [{"tool": "take_screenshot", "args": {}, "result": res}], "success": True}

        # Telemetry / Status
        if p in ["status", "telemetry", "system status", "specs", "hardware", "cpu usage"]:
            telem = self.execute_tool("get_system_telemetry", {})
            msg = f"CPU is at {telem['cpu_load_percent']}%, RAM load is {telem['ram_usage_percent']}%. Battery is {telem['battery']}."
            return {"response": msg, "steps": [{"tool": "get_system_telemetry", "args": {}, "result": telem}], "success": True}

        # Open application (e.g. "open chrome", "launch vs code", "start spotify")
        open_match = re.match(r"(?:open|launch|start)\s+(.+)", p)
        if open_match:
            app_target = open_match.group(1).strip()
            # If not a web URL
            if not app_target.startswith("http") and not app_target.endswith(".com"):
                res = self.execute_tool("launch_application", {"app_name": app_target})
                return {
                    "response": f"Launching {app_target}.",
                    "steps": [{"tool": "launch_application", "args": {"app_name": app_target}, "result": res}],
                    "success": res.get("success", True)
                }

        # Kill application (e.g. "kill chrome", "close notepad")
        kill_match = re.match(r"(?:kill|close|terminate|exit)\s+(.+)", p)
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
        Executes the ReAct loop for a user voice/text prompt.
        
        Args:
            user_prompt: The command or question.
            on_status_update: Optional callback for streaming status to terminal/voice.
            
        Returns:
            Dict containing final 'response', 'steps' taken, and 'success'.
        """
        self.memory.add_message("user", user_prompt)
        steps_log = []

        # 1. Fast-Path Local Execution (Instant response for deterministic OS commands)
        fast_result = self._try_fast_path(user_prompt)
        if fast_result:
            self.memory.add_message("assistant", fast_result["response"], fast_result["steps"])
            return fast_result

        # 2. Autonomous Multi-Step LLM Reasoning
        if not self.client:
            msg = (
                "TARS is online, but GEMINI_API_KEY is not configured in your .env file. "
                "Please add your API key to enable autonomous multi-step execution."
            )
            return {
                "response": msg,
                "steps": [],
                "success": False
            }

        model_name = self.settings.get("llm", {}).get("model", "gemini-2.5-flash")

        try:
            # Reconstruct recent conversation context
            recent_context = self.memory.get_recent_messages(limit=6)
            preferences = self.memory.get_all_preferences()

            context_str = f"\nUser Preferences / Saved Facts: {json.dumps(preferences)}" if preferences else ""
            full_system_instruction = self.system_prompt + context_str

            # We use Gemini's native function calling loop via client.chats
            chat = self.client.chats.create(
                model=model_name,
                config={
                    "system_instruction": full_system_instruction,
                    "tools": self.get_tool_declarations(),
                    "temperature": self.settings.get("llm", {}).get("temperature", 0.4),
                }
            )

            if on_status_update:
                on_status_update("Analyzing command...")

            response = chat.send_message(user_prompt)

            # Process potential function calls
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

                    # Send tool result back to the model
                    from google.genai import types
                    tool_response = types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result}
                    )
                    response = chat.send_message(tool_response)

            final_text = response.text or "Command executed."
            self.memory.add_message("assistant", final_text, steps_log)

            return {
                "response": final_text,
                "steps": steps_log,
                "success": True
            }

        except Exception as e:
            error_msg = f"Operational fault encountered: {str(e)}"
            return {
                "response": error_msg,
                "steps": steps_log,
                "success": False
            }
