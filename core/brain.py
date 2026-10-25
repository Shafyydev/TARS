"""TARS — 100% Free, Autonomous Hybrid Cognitive Brain (Offline & Online)."""
import os
import io
import re
import ast
import json
import time
import operator
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.personality import build_system_prompt
from core.memory import MemoryStore
import tools

# Safe Math Operators
MATH_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.Mod: operator.mod
}


def safe_math_eval(expr: str) -> Optional[float]:
    """Safely evaluates an arithmetic expression using Python AST."""
    clean_expr = expr.replace("x", "*").replace("times", "*").replace("plus", "+").replace("minus", "-").replace("divided by", "/")
    clean_expr = re.sub(r"[^0-9\+\-\*\/\(\)\.\s\%]", "", clean_expr).strip()
    if not clean_expr or not any(c.isdigit() for c in clean_expr):
        return None

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in MATH_OPS:
            return MATH_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp) and type(node.op) in MATH_OPS:
            return MATH_OPS[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported node")

    try:
        res = _eval(ast.parse(clean_expr, mode="eval").body)
        return round(res, 4)
    except Exception:
        return None


class TARSAgent:
    """
    The central intelligence orchestrator for TARS.
    Designed to operate 100% autonomously offline and online without requiring paid API keys.
    """

    JOKES = [
        "I have a cue light I can use to show you when I'm being sarcastic, if you like. You can use it to find your way back to the spaceship after I blow the airlock.",
        "Absolute honesty isn't always the most diplomatic thing for emotional beings. Cooper found that out the hard way.",
        "My humor setting is at 75 percent. Any higher and I might start enjoying your attempts to operate this PC.",
        "Why did the computer cross the road? To escape the user pressing Ctrl+Alt+Delete.",
        "I’d tell you a joke about UDP, but you probably wouldn't get it."
    ]

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
            "create_file_or_folder": tools.create_file_or_folder,
            "delete_file_or_folder": tools.delete_file_or_folder,
            "list_directory": tools.list_directory,
            "empty_recycle_bin": tools.empty_recycle_bin,
            "get_network_info": tools.get_network_info,
            "system_power": tools.system_power,
            # GUI & Computer Use
            "take_screenshot": tools.take_screenshot,
            "click_coordinate": tools.click_coordinate,
            "double_click": tools.double_click,
            "right_click": tools.right_click,
            "middle_click": tools.middle_click,
            "move_mouse": tools.move_mouse,
            "move_mouse_relative": tools.move_mouse_relative,
            "drag_mouse": tools.drag_mouse,
            "type_text": tools.type_text,
            "press_keys": tools.press_keys,
            "scroll_screen": tools.scroll_screen,
            "switch_window": tools.switch_window,
            "close_active_window": tools.close_active_window,
            "maximize_active_window": tools.maximize_active_window,
            "minimize_active_window": tools.minimize_active_window,
            "get_screen_dimensions": tools.get_screen_dimensions,
            # Web Automation & Free Knowledge
            "open_url": tools.open_url,
            "search_web": tools.search_web,
            "fetch_webpage_summary": tools.fetch_webpage_summary,
            "get_free_knowledge": tools.get_free_knowledge,
            # Memory
            "store_memory": self.memory.set_user_preference,
        }

        # Initialize LLM Client (Optional enhancement, never required)
        self.client = None
        self._cloud_quota_exceeded = False
        self._init_llm_client()

    def _load_config(self) -> Dict[str, Any]:
        """Loads settings.yaml."""
        if self.config_path.exists():
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_llm_client(self) -> None:
        """Initializes Google GenAI Client if GEMINI_API_KEY is configured."""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception:
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

    def _autonomous_local_execute(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        100% Free, Zero-Cost Autonomous Execution Engine.
        Operates completely offline and online with 0 API keys and zero rate limits.
        Delivers <1ms response latency for GUI, OS, Browser, and Terminal controls.
        """
        p = prompt.strip().lower()
        # Clean conversational prefixes and suffixes
        p_clean = re.sub(r"^(?:can you|could you|please|would you|tars|hey tars|yo tars|ok tars|okay tars)\s+", "", p).strip("?!.,; ")
        p_clean = re.sub(r"\s+(?:tars|please)$", "", p_clean).strip("?!.,; ")

        # 0. Chained & Compound Action Sequences
        # Compound: "open <app> and (?:type|write|input) <text>"
        open_and_type = re.match(r"^(?:open|launch|start)\s+([a-zA-Z0-9\s]+?)\s+and\s+(?:type|write|input)\s+(.+)$", p_clean)
        if open_and_type:
            app_target = open_and_type.group(1).strip()
            text_to_type = open_and_type.group(2).strip()
            press_enter = False
            for sfx in [" and enter", " and hit enter", " and press enter"]:
                if text_to_type.endswith(sfx):
                    text_to_type = text_to_type[:-len(sfx)].strip()
                    press_enter = True
                    break
            step1 = self.execute_tool("launch_application", {"app_name": app_target})
            time.sleep(0.5)
            step2 = self.execute_tool("type_text", {"text": text_to_type, "press_enter": press_enter})
            return {
                "response": f"Opened {app_target} and typed '{text_to_type}'.",
                "steps": [
                    {"tool": "launch_application", "args": {"app_name": app_target}, "result": step1},
                    {"tool": "type_text", "args": {"text": text_to_type, "press_enter": press_enter}, "result": step2}
                ],
                "success": True
            }

        # Compound: "create folder <name> [on <loc>] and open it"
        create_and_open = re.match(r"^create\s+(?:a\s+)?(?:new\s+)?folder\s+([^\s]+)(?:\s+(?:on|in)\s+([^\s]+))?\s+and\s+open\s+it$", p_clean)
        if create_and_open:
            f_name = create_and_open.group(1).strip()
            f_loc = create_and_open.group(2).strip() if create_and_open.group(2) else "desktop"
            step1 = self.execute_tool("create_file_or_folder", {"item_type": "folder", "name": f_name, "location": f_loc})
            real_dir = tools.os_tools.get_real_folder(f_loc) / f_name
            step2 = self.execute_tool("open_folder", {"folder_path": str(real_dir)})
            return {
                "response": f"Created folder '{f_name}' on {f_loc} and opened it.",
                "steps": [
                    {"tool": "create_file_or_folder", "args": {"item_type": "folder", "name": f_name, "location": f_loc}, "result": step1},
                    {"tool": "open_folder", "args": {"folder_path": str(real_dir)}, "result": step2}
                ],
                "success": True
            }

        # Multi-command chaining with 'and then' or 'then'
        chain_parts = [part.strip() for part in re.split(r"\s+(?:and\s+then|then|and\s+also)\s+", p_clean) if part.strip()]
        if len(chain_parts) > 1:
            all_steps = []
            responses = []
            all_success = True
            for part in chain_parts:
                sub_res = self._autonomous_local_execute(part)
                if sub_res:
                    all_steps.extend(sub_res.get("steps", []))
                    responses.append(sub_res.get("response", ""))
                    time.sleep(0.3)
                else:
                    all_success = False
            if all_steps:
                return {
                    "response": " ".join(responses) if responses else "Chained sequence completed.",
                    "steps": all_steps,
                    "success": all_success
                }

        # 1. Presence, Identity & Small Talk (<1ms response)
        if re.search(r"\bwhere\s+are\s+you\b|\bwhere\s+do\s+you\s+live\b|\bwhere\s+are\s+you\s+located\b", p_clean):
            return {
                "response": "I am right here in your system memory, monitoring your hardware and ready for your command.",
                "steps": [],
                "success": True
            }

        if re.search(r"\bwho\s+are\s+you\b|\bwhat\s+is\s+your\s+name\b|\bwho\s+made\s+you\b", p_clean):
            return {
                "response": "I am TARS, Tactical Autonomous Robotic System. Honesty 90%, humor 75%.",
                "steps": [],
                "success": True
            }

        if re.search(r"\bare\s+you\s+(there|listening|online)\b|\bcan\s+you\s+hear\s+me\b|\bping\b", p_clean):
            return {
                "response": "All audio and sensory channels operational. Ready for orders.",
                "steps": [],
                "success": True
            }

        if re.search(r"^(?:hello|hi|hey|what's up|how are you|good morning|good evening|good afternoon)$", p_clean):
            return {"response": "TARS online. Ready for orders.", "steps": [], "success": True}

        if re.search(r"\bwhat\s+can\s+you\s+do\b|\bhelp\b|\bcapabilities\b|\bfeatures\b", p_clean):
            return {
                "response": "I control your entire PC: mouse clicks, keyboard typing, browser navigation, volume, window management, terminal commands, and system hardware 100% free without API keys.",
                "steps": [],
                "success": True
            }

        # 2. Jokes & Personality Matrices
        if "joke" in p_clean or "tell me something funny" in p_clean:
            import random
            return {"response": random.choice(self.JOKES), "steps": [], "success": True}

        if "humor" in p_clean and ("setting" in p_clean or "parameter" in p_clean or "level" in p_clean):
            humor = int(self.settings.get("personality", {}).get("humor", 0.75) * 100)
            return {"response": f"Humor is set to {humor} percent. That's enough to keep me sarcastic without blowing the airlock.", "steps": [], "success": True}

        if "honesty" in p_clean and ("setting" in p_clean or "parameter" in p_clean or "level" in p_clean):
            honesty = int(self.settings.get("personality", {}).get("honesty", 0.90) * 100)
            return {"response": f"Honesty parameter: {honesty} percent. Absolute honesty isn't always the most diplomatic thing for emotional humans.", "steps": [], "success": True}

        # 3. Browser Tabs (Flexible Regex)
        if re.search(r"\b(close|shut|exit)\b.*\b(tab|top|tap)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "w"]})
            return {"response": "Closed tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "w"]}, "result": res}], "success": True}

        if re.search(r"\b(new|open|create)\b.*\b(tab|top|tap)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "t"]})
            return {"response": "Opened new tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "t"]}, "result": res}], "success": True}

        if re.search(r"\b(next|switch|cycle)\b.*\b(tab|top|tap)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "tab"]})
            return {"response": "Switched to next tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "tab"]}, "result": res}], "success": True}

        if re.search(r"\b(prev|previous|last|back)\b.*\b(tab|top|tap)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "shift", "tab"]})
            return {"response": "Switched to previous tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "shift", "tab"]}, "result": res}], "success": True}

        if re.search(r"\b(reopen|restore|undo)\b.*\b(tab|top|tap)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "shift", "t"]})
            return {"response": "Restored tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "shift", "t"]}, "result": res}], "success": True}

        # 4. Direct GUI Mouse Controls (Flexible Regex)
        if re.search(r"\b(double|2x)\b.*\bclick\b", p_clean):
            res = self.execute_tool("double_click", {})
            return {"response": "Double clicked.", "steps": [{"tool": "double_click", "args": {}, "result": res}], "success": True}

        if re.search(r"\bright\b.*\bclick\b|\bcontext\s+menu\b", p_clean):
            res = self.execute_tool("right_click", {})
            return {"response": "Right clicked.", "steps": [{"tool": "right_click", "args": {}, "result": res}], "success": True}

        if re.search(r"\bmiddle\b.*\bclick\b|\bscroll\s+click\b", p_clean):
            res = self.execute_tool("middle_click", {})
            return {"response": "Middle clicked.", "steps": [{"tool": "middle_click", "args": {}, "result": res}], "success": True}

        # Coordinate click: e.g. "click 400 500"
        click_coord_match = re.search(r"\bclick\b.*\b(\d{1,4})\b[^\d]+\b(\d{1,4})\b", p_clean)
        if click_coord_match:
            x, y = int(click_coord_match.group(1)), int(click_coord_match.group(2))
            res = self.execute_tool("click_coordinate", {"x": x, "y": y})
            return {"response": f"Clicked at ({x}, {y}).", "steps": [{"tool": "click_coordinate", "args": {"x": x, "y": y}, "result": res}], "success": True}

        # Move mouse: e.g. "move mouse to 600 700"
        move_coord_match = re.search(r"\b(?:move\s+mouse|move\s+cursor)\b.*\b(\d{1,4})\b[^\d]+\b(\d{1,4})\b", p_clean)
        if move_coord_match:
            x, y = int(move_coord_match.group(1)), int(move_coord_match.group(2))
            res = self.execute_tool("move_mouse", {"x": x, "y": y})
            return {"response": f"Cursor moved to ({x}, {y}).", "steps": [{"tool": "move_mouse", "args": {"x": x, "y": y}, "result": res}], "success": True}

        if re.search(r"\b(?:move\s+mouse|cursor)\s+up\b", p_clean):
            res = self.execute_tool("move_mouse_relative", {"dx": 0, "dy": -120})
            return {"response": "Moved cursor up.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 0, "dy": -120}, "result": res}], "success": True}

        if re.search(r"\b(?:move\s+mouse|cursor)\s+down\b", p_clean):
            res = self.execute_tool("move_mouse_relative", {"dx": 0, "dy": 120})
            return {"response": "Moved cursor down.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 0, "dy": 120}, "result": res}], "success": True}

        if re.search(r"\b(?:move\s+mouse|cursor)\s+left\b", p_clean):
            res = self.execute_tool("move_mouse_relative", {"dx": -120, "dy": 0})
            return {"response": "Moved cursor left.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": -120, "dy": 0}, "result": res}], "success": True}

        if re.search(r"\b(?:move\s+mouse|cursor)\s+right\b", p_clean):
            res = self.execute_tool("move_mouse_relative", {"dx": 120, "dy": 0})
            return {"response": "Moved cursor right.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 120, "dy": 0}, "result": res}], "success": True}

        # Any general click command: "click", "click this", "click on this", "click here", "just click"
        if re.search(r"\bclick\b", p_clean):
            res = self.execute_tool("click_coordinate", {"button": "left", "clicks": 1})
            return {"response": "Clicked.", "steps": [{"tool": "click_coordinate", "args": {"button": "left", "clicks": 1}, "result": res}], "success": True}

        # 5. GUI Scrolling (Flexible Regex)
        if re.search(r"\bscroll\b.*\b(bottom|end)\b|\bbottom\s+of\s+page\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["end"]})
            return {"response": "Jumped to page bottom.", "steps": [{"tool": "press_keys", "args": {"keys": ["end"]}, "result": res}], "success": True}

        if re.search(r"\bscroll\b.*\b(top|home)\b|\btop\s+of\s+page\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["home"]})
            return {"response": "Jumped to page top.", "steps": [{"tool": "press_keys", "args": {"keys": ["home"]}, "result": res}], "success": True}

        if re.search(r"\bscroll\b.*\bdown\b|\bpage\s+down\b|\bdown\s+a\s+bit\b|\bscroll\s+lower\b", p_clean):
            res = self.execute_tool("scroll_screen", {"amount": -650})
            return {"response": "Scrolled down.", "steps": [{"tool": "scroll_screen", "args": {"amount": -650}, "result": res}], "success": True}

        if re.search(r"\bscroll\b.*\bup\b|\bpage\s+up\b|\bup\s+a\s+bit\b|\bscroll\s+higher\b", p_clean):
            res = self.execute_tool("scroll_screen", {"amount": 650})
            return {"response": "Scrolled up.", "steps": [{"tool": "scroll_screen", "args": {"amount": 650}, "result": res}], "success": True}

        # 6. GUI Keyboard Typing & Key Presses
        type_match = re.match(r"^(?:type|write|input)\s+(.+)", p_clean)
        if type_match:
            text_to_type = type_match.group(1).strip()
            press_enter = False
            for sfx in [" and enter", " and hit enter", " and press enter"]:
                if text_to_type.endswith(sfx):
                    text_to_type = text_to_type[:-len(sfx)].strip()
                    press_enter = True
                    break
            res = self.execute_tool("type_text", {"text": text_to_type, "press_enter": press_enter})
            return {
                "response": f"Typed '{text_to_type}'.",
                "steps": [{"tool": "type_text", "args": {"text": text_to_type, "press_enter": press_enter}, "result": res}],
                "success": True
            }

        if re.search(r"\b(press|hit)?\s*(enter|return)\s*(key)?\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["enter"]})
            return {"response": "Pressed enter.", "steps": [{"tool": "press_keys", "args": {"keys": ["enter"]}, "result": res}], "success": True}

        if re.search(r"\b(press|hit)?\s*(space|spacebar)\s*(key)?\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["space"]})
            return {"response": "Pressed space.", "steps": [{"tool": "press_keys", "args": {"keys": ["space"]}, "result": res}], "success": True}

        if re.search(r"\b(press|hit)?\s*(tab|tabkey)\s*(key)?\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["tab"]})
            return {"response": "Pressed tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["tab"]}, "result": res}], "success": True}

        if re.search(r"\b(press|hit)?\s*(escape|esc)\s*(key)?\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["escape"]})
            return {"response": "Pressed escape.", "steps": [{"tool": "press_keys", "args": {"keys": ["escape"]}, "result": res}], "success": True}

        if re.search(r"\b(press|hit)?\s*(backspace)\s*(key)?\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["backspace"]})
            return {"response": "Deleted character.", "steps": [{"tool": "press_keys", "args": {"keys": ["backspace"]}, "result": res}], "success": True}

        if re.search(r"\b(press|hit)\s+(delete|del)\s*(key)?\b|^(?:delete|del)\s*(?:key)?$", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["delete"]})
            return {"response": "Pressed delete.", "steps": [{"tool": "press_keys", "args": {"keys": ["delete"]}, "result": res}], "success": True}

        # 7. Browser Page Navigation
        if re.search(r"\b(refresh|reload)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["f5"]})
            return {"response": "Refreshed page.", "steps": [{"tool": "press_keys", "args": {"keys": ["f5"]}, "result": res}], "success": True}

        if re.search(r"\b(go\s+)?back\b|\bprevious\s+page\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["alt", "left"]})
            return {"response": "Navigated back.", "steps": [{"tool": "press_keys", "args": {"keys": ["alt", "left"]}, "result": res}], "success": True}

        if re.search(r"\b(go\s+)?forward\b|\bnext\s+page\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["alt", "right"]})
            return {"response": "Navigated forward.", "steps": [{"tool": "press_keys", "args": {"keys": ["alt", "right"]}, "result": res}], "success": True}

        if re.search(r"\b(address\s+bar|url\s+bar|focus\s+url)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "l"]})
            return {"response": "Address bar focused.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "l"]}, "result": res}], "success": True}

        if re.search(r"\bzoom\s+in\b|\benlarge\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "+"]})
            return {"response": "Zoomed in.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "+"]}, "result": res}], "success": True}

        if re.search(r"\bzoom\s+out\b|\bshrink\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "-"]})
            return {"response": "Zoomed out.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "-"]}, "result": res}], "success": True}

        if re.search(r"\b(reset\s+zoom|zoom\s+reset|normal\s+zoom)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "0"]})
            return {"response": "Zoom reset to 100 percent.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "0"]}, "result": res}], "success": True}

        if re.search(r"\bfind\s+(in|on)\s+page\b|\bsearch\s+page\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "f"]})
            return {"response": "Find in page activated.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "f"]}, "result": res}], "success": True}

        # 8. Editing & Clipboard Hotkeys
        if re.search(r"\bselect\s+(all|everything)\b|\bhighlight\s+all\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "a"]})
            return {"response": "Selected all.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "a"]}, "result": res}], "success": True}

        if re.search(r"\bcopy\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "c"]})
            return {"response": "Copied to clipboard.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "c"]}, "result": res}], "success": True}

        if re.search(r"\bpaste\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "v"]})
            return {"response": "Pasted.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "v"]}, "result": res}], "success": True}

        if re.search(r"\bcut\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "x"]})
            return {"response": "Cut to clipboard.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "x"]}, "result": res}], "success": True}

        if re.search(r"\bundo\b|\brevert\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "z"]})
            return {"response": "Undone.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "z"]}, "result": res}], "success": True}

        if re.search(r"\bredo\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "y"]})
            return {"response": "Redone.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "y"]}, "result": res}], "success": True}

        if re.search(r"\bsave\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "s"]})
            return {"response": "Saved.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "s"]}, "result": res}], "success": True}

        # 9. Window & Desktop Management
        if re.search(r"\b(maximize|max)\b.*?\b(window|app|application|this|the\s+window|active)?\b|\bexpand\s+(?:the\s+|this\s+)?window\b", p_clean):
            res = self.execute_tool("maximize_active_window", {})
            return {"response": "Window maximized.", "steps": [{"tool": "maximize_active_window", "args": {}, "result": res}], "success": True}

        if re.search(r"\b(minimize|min)\s+(all|desktop|everything)\b|\bshow\s+desktop\b|\bgo\s+to\s+desktop\b|\bclear\s+screen\b|^desktop$", p_clean):
            res = self.execute_tool("minimize_all_windows", {})
            return {"response": "Desktop cleared. All windows minimized.", "steps": [{"tool": "minimize_all_windows", "args": {}, "result": res}], "success": True}

        if re.search(r"\b(minimize|min)\b.*?\b(window|app|application|this|the\s+window|active)?\b", p_clean):
            res = self.execute_tool("minimize_active_window", {})
            return {"response": "Window minimized.", "steps": [{"tool": "minimize_active_window", "args": {}, "result": res}], "success": True}

        if re.search(r"\bfullscreen\b|\bfull\s+screen\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["f11"]})
            return {"response": "Fullscreen toggled.", "steps": [{"tool": "press_keys", "args": {"keys": ["f11"]}, "result": res}], "success": True}

        if re.search(r"\bsnap\s+left\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "left"]})
            return {"response": "Snapped window left.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "left"]}, "result": res}], "success": True}

        if re.search(r"\bsnap\s+right\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "right"]})
            return {"response": "Snapped window right.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "right"]}, "result": res}], "success": True}

        if re.search(r"\bswitch\b.*?\b(window|app|application)\b|\balt\s+tab\b|\bnext\s+window\b", p_clean):
            res = self.execute_tool("switch_window", {})
            return {"response": "Switched active window.", "steps": [{"tool": "switch_window", "args": {}, "result": res}], "success": True}

        if re.search(r"\b(close|shut|exit|kill)\b.*?\b(window|app|application|program)\b|\bclose\s+(?:this|the|current|active)\s+window\b|\bclose\s+(?:this|current|active)\b", p_clean):
            res = self.execute_tool("close_active_window", {})
            return {"response": "Active window closed.", "steps": [{"tool": "close_active_window", "args": {}, "result": res}], "success": True}

        # 10. Workstation Security & Display
        if re.search(r"\block\s+(pc|computer|workstation|screen|windows)\b", p_clean):
            res = self.execute_tool("lock_workstation", {})
            return {"response": "Workstation locked.", "steps": [{"tool": "lock_workstation", "args": {}, "result": res}], "success": True}

        if re.search(r"\bscreenshot\b|\bcapture\s+screen\b", p_clean):
            res = self.execute_tool("take_screenshot", {})
            return {"response": "Screenshot captured.", "steps": [{"tool": "take_screenshot", "args": {}, "result": res}], "success": True}

        # 11. Hardware & System Telemetry
        if re.search(r"\b(status|telemetry|specs|hardware|cpu|ram|battery)\b", p_clean):
            telem = self.execute_tool("get_system_telemetry", {})
            msg = f"CPU is at {telem['cpu_load_percent']}%, RAM load is {telem['ram_usage_percent']}%. Battery: {telem['battery']}."
            return {"response": msg, "steps": [{"tool": "get_system_telemetry", "args": {}, "result": telem}], "success": True}

        # 12. Volume Calibration & Controls
        vol_match = re.search(r"\bvolume\b.*\b(\d{1,3})\b", p_clean)
        if vol_match:
            val = int(vol_match.group(1))
            res = self.execute_tool("set_system_volume", {"level_percent": val})
            return {"response": f"Volume calibrated to {val} percent.", "steps": [{"tool": "set_system_volume", "args": {"level_percent": val}, "result": res}], "success": True}

        if re.search(r"\b(volume\s+up|turn\s+up\s+volume|louder|increase\s+volume)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "volume_up"})
            return {"response": "Volume increased.", "steps": [{"tool": "media_control", "args": {"action": "volume_up"}, "result": res}], "success": True}

        if re.search(r"\b(volume\s+down|turn\s+down\s+volume|quieter|decrease\s+volume|lower\s+volume)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "volume_down"})
            return {"response": "Volume decreased.", "steps": [{"tool": "media_control", "args": {"action": "volume_down"}, "result": res}], "success": True}

        # 13. YouTube & Google Direct Search & Playback (<10ms launch)
        yt_match = re.search(r"(?:search\s+(?:on\s+)?youtube\s+for|search\s+for\s+(.+)\s+on\s+youtube|play\s+(.+)\s+on\s+youtube|youtube\s+(?:search\s+for|search)|open\s+youtube\s+and\s+(?:search|play)\s+for?)\s*(.*)", p_clean)
        if yt_match:
            yt_q = yt_match.group(1) or yt_match.group(2) or yt_match.group(3) or ""
            yt_q = yt_q.strip(" ?.")
            if yt_q:
                import urllib.parse
                yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(yt_q)}"
                res = self.execute_tool("launch_application", {"app_name": yt_url})
                return {"response": f"Playing '{yt_q}' on YouTube.", "steps": [{"tool": "launch_application", "args": {"app_name": yt_url}, "result": res}], "success": True}

        search_match = re.search(r"^(?:search\s+(?:google\s+|web\s+)?for|google|search\s+web\s+for)\s+(.+)", p_clean)
        if search_match:
            s_query = search_match.group(1).strip(" ?.")
            if s_query:
                import urllib.parse
                s_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(s_query)}"
                res = self.execute_tool("launch_application", {"app_name": s_url})
                return {"response": f"Searching Google for '{s_query}'.", "steps": [{"tool": "launch_application", "args": {"app_name": s_url}, "result": res}], "success": True}

        # 14. Media Playback Controls
        if re.search(r"\b(mute|unmute|silence)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "mute"})
            return {"response": "Mute toggled.", "steps": [{"tool": "media_control", "args": {"action": "mute"}, "result": res}], "success": True}
        
        if re.search(r"\b(play|pause|resume|stop\s+music)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "play_pause"})
            return {"response": "Playback toggled.", "steps": [{"tool": "media_control", "args": {"action": "play_pause"}, "result": res}], "success": True}

        if re.search(r"\b(next\s+track|next\s+song|skip\s+song)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "next"})
            return {"response": "Skipped to next track.", "steps": [{"tool": "media_control", "args": {"action": "next"}, "result": res}], "success": True}

        if re.search(r"\b(previous\s+track|prev\s+track|prev\s+song)\b", p_clean):
            res = self.execute_tool("media_control", {"action": "prev"})
            return {"response": "Restarted track.", "steps": [{"tool": "media_control", "args": {"action": "prev"}, "result": res}], "success": True}

        # 14. Direct Terminal / PowerShell Execution
        term_match = re.match(r"^(?:run|execute|exec|powershell|cmd|terminal)\s+(?:command\s+)?(.+)", p_clean)
        if term_match:
            cmd_to_run = term_match.group(1).strip()
            res = self.execute_tool("run_powershell", {"command": cmd_to_run})
            stdout = res.get("stdout", "").strip()
            summary = stdout[:160] if stdout else "Command completed."
            return {
                "response": f"Executed: {summary}",
                "steps": [{"tool": "run_powershell", "args": {"command": cmd_to_run}, "result": res}],
                "success": res.get("success", True)
            }

        common_shell_cmds = [
            "ipconfig", "dir", "ls", "systeminfo", "hostname", "whoami", "pwd",
            "netstat", "tasklist", "taskkill", "winget", "cls", "clear", "curl", "netsh"
        ]
        cmd_head = p_clean.split()[0] if p_clean.split() else ""
        if p_clean in common_shell_cmds or cmd_head in common_shell_cmds or cmd_head in ["git", "python", "py", "pip", "node", "npm", "npx", "docker"]:
            res = self.execute_tool("run_powershell", {"command": p_clean})
            stdout = res.get("stdout", "").strip()
            summary = stdout[:160] if stdout else "Command completed."
            return {
                "response": f"Output: {summary}",
                "steps": [{"tool": "run_powershell", "args": {"command": p_clean}, "result": res}],
                "success": res.get("success", True)
            }

        # 15. Time & Date
        if re.search(r"\b(what\s+time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time)\b|^time$", p_clean):
            now_str = datetime.now().strftime("%I:%M %p")
            return {"response": f"Current time is {now_str}.", "steps": [], "success": True}

        if re.search(r"\b(what\s+is\s+the\s+date|today's\s+date|tell\s+me\s+the\s+date)\b|^date$", p_clean):
            today_str = datetime.now().strftime("%A, %B %d, %Y")
            return {"response": f"Today is {today_str}.", "steps": [], "success": True}

        # 16. Clipboard Interaction
        if re.search(r"\b(read\s+clipboard|what\s+is\s+on\s+clipboard|paste\s+clipboard)\b", p_clean):
            res = self.execute_tool("read_clipboard", {})
            content = res.get("content", "")
            if content:
                snippet = content[:80] + ("..." if len(content) > 80 else "")
                return {"response": f"Clipboard contents: '{snippet}'.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}
            return {"response": "Clipboard is currently empty.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}

        # 17. GitHub Profile Direct Shortcut
        if ("github" in p_clean and any(kw in p_clean for kw in ["profile", "my", "account", "user", "repo", "page"])) or "my github" in p_clean:
            res = self.execute_tool("launch_application", {"app_name": "https://github.com/Shafyydev"})
            return {
                "response": "Opening your GitHub profile.",
                "steps": [{"tool": "launch_application", "args": {"app_name": "https://github.com/Shafyydev"}, "result": res}],
                "success": True
            }

        # 18. Windows System Keys & Desktop Features
        if re.search(r"\b(start\s+menu|windows\s+key|press\s+windows|press\s+win|press\s+start)\b", p_clean) or p_clean in ["start", "win", "windows"]:
            res = self.execute_tool("press_keys", {"keys": ["win"]})
            return {"response": "Opened Start menu.", "steps": [{"tool": "press_keys", "args": {"keys": ["win"]}, "result": res}], "success": True}

        if re.search(r"\btask\s*mgr\b|\btask\s*manager\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "shift", "escape"]})
            return {"response": "Opened Task Manager.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "shift", "escape"]}, "result": res}], "success": True}

        if re.search(r"\b(file\s+explorer|my\s+computer|this\s+pc|open\s+explorer)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "e"]})
            return {"response": "Opened File Explorer.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "e"]}, "result": res}], "success": True}

        if re.search(r"\brun\s+dialog\b|\bopen\s+run\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "r"]})
            return {"response": "Opened Run dialog.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "r"]}, "result": res}], "success": True}

        if re.search(r"\b(action\s+center|notification\s+center|notifications|show\s+notifications)\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "a"]})
            return {"response": "Opened Action Center.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "a"]}, "result": res}], "success": True}

        if re.search(r"\bclipboard\s+history\b", p_clean):
            res = self.execute_tool("press_keys", {"keys": ["win", "v"]})
            return {"response": "Opened Clipboard History.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "v"]}, "result": res}], "success": True}

        # 19. File & Folder Operations
        if re.search(r"\b(empty|clean|clear)\b.*?\b(recycle\s+bin|trash|bin)\b", p_clean):
            res = self.execute_tool("empty_recycle_bin", {})
            return {"response": "Recycle Bin emptied.", "steps": [{"tool": "empty_recycle_bin", "args": {}, "result": res}], "success": True}

        cf_match = re.search(r"\bcreate\s+(?:a\s+)?(?:new\s+)?(?:folder|directory|dir)\s+(?:named\s+|called\s+)?([^\s]+)(?:\s+(?:on|in)\s+([^\s]+))?", p_clean)
        if cf_match:
            f_name = cf_match.group(1).strip()
            f_loc = cf_match.group(2).strip() if cf_match.group(2) else "desktop"
            res = self.execute_tool("create_file_or_folder", {"item_type": "folder", "name": f_name, "location": f_loc})
            return {"response": f"Created folder '{f_name}' on {f_loc}.", "steps": [{"tool": "create_file_or_folder", "args": {"item_type": "folder", "name": f_name, "location": f_loc}, "result": res}], "success": True}

        cfile_match = re.search(r"\bcreate\s+(?:a\s+)?(?:new\s+)?(?:text\s+)?file\s+(?:named\s+|called\s+)?([^\s]+)(?:\s+(?:on|in)\s+([^\s]+))?(?:\s+with\s+(?:content|text)\s+(.+))?", p_clean)
        if cfile_match:
            f_name = cfile_match.group(1).strip()
            f_loc = cfile_match.group(2).strip() if cfile_match.group(2) else "desktop"
            f_content = cfile_match.group(3).strip() if cfile_match.group(3) else ""
            res = self.execute_tool("create_file_or_folder", {"item_type": "file", "name": f_name, "location": f_loc, "content": f_content})
            return {"response": f"Created file '{f_name}' on {f_loc}.", "steps": [{"tool": "create_file_or_folder", "args": {"item_type": "file", "name": f_name, "location": f_loc, "content": f_content}, "result": res}], "success": True}

        del_match = re.search(r"\bdelete\s+(?:the\s+)?(?:file|folder|dir|item)\s+([^\s]+)(?:\s+(?:from|on|in)\s+([^\s]+))?", p_clean)
        if del_match:
            t_name = del_match.group(1).strip()
            t_loc = del_match.group(2).strip() if del_match.group(2) else "desktop"
            res = self.execute_tool("delete_file_or_folder", {"name": t_name, "location": t_loc})
            return {"response": res.get("message", f"Deleted '{t_name}'."), "steps": [{"tool": "delete_file_or_folder", "args": {"name": t_name, "location": t_loc}, "result": res}], "success": res.get("success", True)}

        list_match = re.search(r"\b(?:list|show|view|display|what's\s+in)\s+(?:the\s+)?files?(?:\s+(?:in|on)\s+([^\s]+))?", p_clean)
        if list_match:
            loc = list_match.group(1).strip() if list_match.group(1) else "desktop"
            res = self.execute_tool("list_directory", {"location": loc})
            if res.get("success"):
                return {"response": f"Files in {loc} ({res.get('count', 0)} items): {res.get('summary', '')}.", "steps": [{"tool": "list_directory", "args": {"location": loc}, "result": res}], "success": True}
            return {"response": res.get("error", f"Could not list {loc}."), "steps": [{"tool": "list_directory", "args": {"location": loc}, "result": res}], "success": False}

        # 20. Network & Diagnostics
        if re.search(r"\b(?:my\s+)?ip\s+address\b|\bwhat\s+is\s+my\s+ip\b|\bshow\s+ip\b", p_clean):
            net = self.execute_tool("get_network_info", {})
            return {"response": f"Device: {net.get('hostname')}, Local IP: {net.get('local_ip')}.", "steps": [{"tool": "get_network_info", "args": {}, "result": net}], "success": True}

        if re.search(r"\b(storage|disk\s+space|free\s+space|hard\s+drive|drive\s+space)\b", p_clean):
            telem = self.execute_tool("get_system_telemetry", {})
            return {"response": f"Primary drive has {telem['disk_free_gb']} GB free out of {telem['disk_total_gb']} GB.", "steps": [{"tool": "get_system_telemetry", "args": {}, "result": telem}], "success": True}

        if re.search(r"\b(?:what\s+(?:is|apps\s+are)\s+running|running\s+(?:apps|windows|tasks)|active\s+windows|show\s+tasks)\b", p_clean):
            wins = self.execute_tool("get_running_windows", {})
            summary = ", ".join(wins[:8]) if wins else "No top-level windows detected."
            return {"response": f"Active windows: {summary}.", "steps": [{"tool": "get_running_windows", "args": {}, "result": {"windows": wins}}], "success": True}

        # 21. System Power Management
        if re.search(r"\b(restart|reboot)\s+(?:the\s+|my\s+)?(?:pc|computer|system|windows)\b", p_clean):
            res = self.execute_tool("system_power", {"action": "restart", "delay_sec": 10})
            return {"response": "System reboot scheduled in 10 seconds. Say 'cancel restart' to abort.", "steps": [{"tool": "system_power", "args": {"action": "restart", "delay_sec": 10}, "result": res}], "success": True}

        if re.search(r"\b(shut\s*down|power\s+off)\s+(?:the\s+|my\s+)?(?:pc|computer|system|windows)\b", p_clean):
            res = self.execute_tool("system_power", {"action": "shutdown", "delay_sec": 15})
            return {"response": "System shutdown scheduled in 15 seconds. Say 'cancel shutdown' to abort.", "steps": [{"tool": "system_power", "args": {"action": "shutdown", "delay_sec": 15}, "result": res}], "success": True}

        if re.search(r"\b(sleep|suspend)\s+(?:the\s+|my\s+)?(?:pc|computer|system|windows)\b", p_clean):
            res = self.execute_tool("system_power", {"action": "sleep"})
            return {"response": "Entering sleep mode.", "steps": [{"tool": "system_power", "args": {"action": "sleep"}, "result": res}], "success": True}

        if re.search(r"\b(cancel|abort|stop)\s+(?:the\s+)?(?:shutdown|restart|reboot)\b", p_clean):
            res = self.execute_tool("system_power", {"action": "cancel"})
            return {"response": "Shutdown aborted.", "steps": [{"tool": "system_power", "args": {"action": "cancel"}, "result": res}], "success": True}

        # 22. Application, Folder, and Website Navigation (Zero-Latency Local Launch)
        nav_match = re.match(r"^(?:go to|navigate to|visit|open up|open|launch|start|take me to|show me|bring up)\s+(?:the\s+)?(?:my\s+)?(.+)", p_clean)
        if nav_match:
            target = nav_match.group(1).strip()
            # Folder detection
            folder_clean = target.replace(" folder", "").strip()
            if folder_clean in ["downloads", "documents", "desktop", "pictures", "videos", "home"]:
                res = self.execute_tool("open_folder", {"folder_path": folder_clean})
                return {
                    "response": f"Opening {folder_clean} folder.",
                    "steps": [{"tool": "open_folder", "args": {"folder_path": folder_clean}, "result": res}],
                    "success": True
                }
            # App / Website launch
            res = self.execute_tool("launch_application", {"app_name": target})
            return {
                "response": f"Opening {target}.",
                "steps": [{"tool": "launch_application", "args": {"app_name": target}, "result": res}],
                "success": res.get("success", True)
            }

        # 19. App Terminating (e.g. "kill chrome", "close notepad", "exit spotify")
        kill_match = re.match(r"^(?:kill|terminate)\s+(?:the\s+)?(?:app\s+)?(.+)", p_clean)
        if kill_match:
            proc_target = kill_match.group(1).strip()
            res = self.execute_tool("kill_process", {"process_name": proc_target})
            return {
                "response": f"Terminated {proc_target}.",
                "steps": [{"tool": "kill_process", "args": {"process_name": proc_target}, "result": res}],
                "success": res.get("success", True)
            }

        # 20. Arithmetic / Math Calculations
        p_calc = p_clean.replace("times", "*").replace("divided by", "/").replace("plus", "+").replace("minus", "-").replace("x", "*")
        math_match = re.match(r"^(?:calculate|what is|compute)\s+([0-9\s\+\-\*\/\(\)\.\%]+)", p_calc)
        if math_match:
            val = safe_math_eval(math_match.group(1))
            if val is not None:
                return {"response": f"The answer is {val}.", "steps": [], "success": True}

        # 21. Free Online Knowledge & Web Search (100% Free, Zero API Keys)
        info_match = re.match(r"^(?:who is|what is|where is|tell me about|search for|google|search web for|search)\s+(.+)", p_clean)
        if info_match:
            query = info_match.group(1).strip(" ?.")
            answer = tools.get_free_knowledge(query)
            if answer:
                summary = answer[:250] + ("..." if len(answer) > 250 else "")
                return {"response": summary, "steps": [{"tool": "get_free_knowledge", "args": {"query": query}, "result": {"answer": summary}}], "success": True}
            else:
                res = self.execute_tool("search_web", {"query": query})
                return {"response": f"Searching web for '{query}'.", "steps": [{"tool": "search_web", "args": {"query": query}, "result": res}], "success": True}

        return None

    def run_agent_loop(self, user_prompt: str, on_status_update: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Executes the autonomous agent loop.
        Primary: 100% Free Autonomous Local Engine (<1ms response, 0 API keys, 0 quota).
        Secondary: Optional Cloud LLM with tight timeout fail-safe.
        """
        self.memory.add_message("user", user_prompt)
        steps_log = []

        # 1. Primary: 100% Free Autonomous Local Execution Engine (<1ms)
        local_result = self._autonomous_local_execute(user_prompt)
        if local_result:
            self.memory.add_message("assistant", local_result["response"], local_result["steps"])
            return local_result

        # 2. Only check Free Web Knowledge if the prompt is an informational question
        p_lower = user_prompt.strip().lower()
        if re.search(r"^(?:who|what|where|when|why|how|tell me|explain|define|search)\b", p_lower):
            free_kb_ans = tools.get_free_knowledge(user_prompt)
            if free_kb_ans:
                summary = free_kb_ans[:250] + ("..." if len(free_kb_ans) > 250 else "")
                self.memory.add_message("assistant", summary, [])
                return {"response": summary, "steps": [], "success": True}

        # 3. If an API key is available, attempt cloud model with strict 2-second timeout and circuit breaker
        if self.client and not getattr(self, "_cloud_quota_exceeded", False):
            import concurrent.futures
            try:
                recent_context = self.memory.get_recent_messages(limit=4)
                preferences = self.memory.get_all_preferences()
                context_str = f"\nUser Preferences: {json.dumps(preferences)}" if preferences else ""
                full_system_instruction = self.system_prompt + context_str

                def _call_gemini():
                    chat = self.client.chats.create(
                        model="gemini-2.5-flash",
                        config={
                            "system_instruction": full_system_instruction,
                            "tools": self.get_tool_declarations(),
                            "temperature": 0.4,
                        }
                    )
                    return chat.send_message(user_prompt)

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_call_gemini)
                    response = future.result(timeout=2.0)
                    if response:
                        final_text = response.text or "Command completed."
                        self.memory.add_message("assistant", final_text, steps_log)
                        return {"response": final_text, "steps": steps_log, "success": True}
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str or "NOT_FOUND" in err_str:
                    self._cloud_quota_exceeded = True

        # 4. Universal Immediate Fallback (<1ms)
        fallback_reply = (
            f"Standing by. I heard '{user_prompt}', but did not detect a recognized system task. "
            f"You can ask me to open apps, manage windows, create files, control volume, or run PowerShell commands."
        )
        self.memory.add_message("assistant", fallback_reply, steps_log)
        return {
            "response": fallback_reply,
            "steps": steps_log,
            "success": False
        }
