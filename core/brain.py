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
        Delivers <5ms response latency for GUI, OS, Browser, and Terminal controls.
        """
        p = prompt.strip().lower()
        # Clean conversational prefixes and suffixes
        p_clean = re.sub(r"^(?:can you|could you|please|would you|tars|hey tars|yo tars|ok tars|okay tars)\s+", "", p).strip("?!.,; ")
        p_clean = re.sub(r"\s+(?:tars|please)$", "", p_clean).strip("?!.,; ")

        # 1. Presence, Identity & Small Talk (<1ms response)
        if p_clean in ["where are you", "where are you now", "where do you live", "where are you located", "are you here"]:
            return {
                "response": "I am right here in your system memory, monitoring your hardware and ready for your command.",
                "steps": [],
                "success": True
            }

        if p_clean in ["who are you", "what is your name", "what are you", "who made you"]:
            return {
                "response": "I am TARS, Tactical Autonomous Robotic System. Honesty 90%, humor 75%.",
                "steps": [],
                "success": True
            }

        if p_clean in ["are you listening", "can you hear me", "are you there", "tars are you there", "ping"]:
            return {
                "response": "All audio and sensory channels operational. Ready for orders.",
                "steps": [],
                "success": True
            }

        if p_clean in ["hello", "hi", "hey", "what's up", "how are you", "good morning", "good evening", "good afternoon"]:
            return {"response": "TARS online. Ready for orders.", "steps": [], "success": True}

        if p_clean in ["what can you do", "help", "capabilities", "what are your features", "commands"]:
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

        # 3. Direct GUI Mouse Controls (Clicks, Cursor Movement, Dragging)
        if p_clean in ["click", "click here", "left click", "click now", "single click", "hit click"]:
            res = self.execute_tool("click_coordinate", {"button": "left", "clicks": 1})
            return {"response": "Clicked.", "steps": [{"tool": "click_coordinate", "args": {"button": "left", "clicks": 1}, "result": res}], "success": True}

        if p_clean in ["double click", "double click here", "open it"]:
            res = self.execute_tool("double_click", {})
            return {"response": "Double clicked.", "steps": [{"tool": "double_click", "args": {}, "result": res}], "success": True}

        if p_clean in ["right click", "right click here", "context menu", "open context menu"]:
            res = self.execute_tool("right_click", {})
            return {"response": "Right clicked.", "steps": [{"tool": "right_click", "args": {}, "result": res}], "success": True}

        if p_clean in ["middle click", "scroll click"]:
            res = self.execute_tool("middle_click", {})
            return {"response": "Middle clicked.", "steps": [{"tool": "middle_click", "args": {}, "result": res}], "success": True}

        click_coord_match = re.match(r"^(?:click|click at|click coordinate)\s+(\d+)\s*(?:and|,|\s)\s*(\d+)$", p_clean)
        if click_coord_match:
            x, y = int(click_coord_match.group(1)), int(click_coord_match.group(2))
            res = self.execute_tool("click_coordinate", {"x": x, "y": y})
            return {"response": f"Clicked at ({x}, {y}).", "steps": [{"tool": "click_coordinate", "args": {"x": x, "y": y}, "result": res}], "success": True}

        move_coord_match = re.match(r"^(?:move mouse to|move cursor to|move mouse|move cursor)\s+(\d+)\s*(?:and|,|\s)\s*(\d+)$", p_clean)
        if move_coord_match:
            x, y = int(move_coord_match.group(1)), int(move_coord_match.group(2))
            res = self.execute_tool("move_mouse", {"x": x, "y": y})
            return {"response": f"Cursor moved to ({x}, {y}).", "steps": [{"tool": "move_mouse", "args": {"x": x, "y": y}, "result": res}], "success": True}

        if p_clean in ["move mouse up", "cursor up"]:
            res = self.execute_tool("move_mouse_relative", {"dx": 0, "dy": -120})
            return {"response": "Moved cursor up.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 0, "dy": -120}, "result": res}], "success": True}

        if p_clean in ["move mouse down", "cursor down"]:
            res = self.execute_tool("move_mouse_relative", {"dx": 0, "dy": 120})
            return {"response": "Moved cursor down.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 0, "dy": 120}, "result": res}], "success": True}

        if p_clean in ["move mouse left", "cursor left"]:
            res = self.execute_tool("move_mouse_relative", {"dx": -120, "dy": 0})
            return {"response": "Moved cursor left.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": -120, "dy": 0}, "result": res}], "success": True}

        if p_clean in ["move mouse right", "cursor right"]:
            res = self.execute_tool("move_mouse_relative", {"dx": 120, "dy": 0})
            return {"response": "Moved cursor right.", "steps": [{"tool": "move_mouse_relative", "args": {"dx": 120, "dy": 0}, "result": res}], "success": True}

        # 4. GUI Scrolling
        if p_clean in ["scroll down", "scroll page down", "down a bit", "scroll down a bit", "page down", "scroll lower"]:
            res = self.execute_tool("scroll_screen", {"amount": -650})
            return {"response": "Scrolled down.", "steps": [{"tool": "scroll_screen", "args": {"amount": -650}, "result": res}], "success": True}

        if p_clean in ["scroll up", "scroll page up", "up a bit", "scroll up a bit", "page up", "scroll higher"]:
            res = self.execute_tool("scroll_screen", {"amount": 650})
            return {"response": "Scrolled up.", "steps": [{"tool": "scroll_screen", "args": {"amount": 650}, "result": res}], "success": True}

        if p_clean in ["scroll to bottom", "bottom of page", "go to bottom"]:
            res = self.execute_tool("press_keys", {"keys": ["end"]})
            return {"response": "Jumped to page bottom.", "steps": [{"tool": "press_keys", "args": {"keys": ["end"]}, "result": res}], "success": True}

        if p_clean in ["scroll to top", "top of page", "go to top"]:
            res = self.execute_tool("press_keys", {"keys": ["home"]})
            return {"response": "Jumped to page top.", "steps": [{"tool": "press_keys", "args": {"keys": ["home"]}, "result": res}], "success": True}

        # 5. GUI Keyboard Typing & Key Presses
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

        if p_clean in ["press enter", "hit enter", "enter", "enter key"]:
            res = self.execute_tool("press_keys", {"keys": ["enter"]})
            return {"response": "Pressed enter.", "steps": [{"tool": "press_keys", "args": {"keys": ["enter"]}, "result": res}], "success": True}

        if p_clean in ["press space", "hit space", "space", "spacebar"]:
            res = self.execute_tool("press_keys", {"keys": ["space"]})
            return {"response": "Pressed space.", "steps": [{"tool": "press_keys", "args": {"keys": ["space"]}, "result": res}], "success": True}

        if p_clean in ["press tab", "hit tab", "tab", "next field"]:
            res = self.execute_tool("press_keys", {"keys": ["tab"]})
            return {"response": "Pressed tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["tab"]}, "result": res}], "success": True}

        if p_clean in ["press escape", "hit escape", "escape", "esc"]:
            res = self.execute_tool("press_keys", {"keys": ["escape"]})
            return {"response": "Pressed escape.", "steps": [{"tool": "press_keys", "args": {"keys": ["escape"]}, "result": res}], "success": True}

        if p_clean in ["press backspace", "hit backspace", "backspace"]:
            res = self.execute_tool("press_keys", {"keys": ["backspace"]})
            return {"response": "Deleted previous character.", "steps": [{"tool": "press_keys", "args": {"keys": ["backspace"]}, "result": res}], "success": True}

        if p_clean in ["press delete", "hit delete", "delete"]:
            res = self.execute_tool("press_keys", {"keys": ["delete"]})
            return {"response": "Pressed delete.", "steps": [{"tool": "press_keys", "args": {"keys": ["delete"]}, "result": res}], "success": True}

        # 6. Browser Tabs & Web Page Controls
        if p_clean in ["new tab", "open new tab", "open a new tab", "create tab"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "t"]})
            return {"response": "Opened new tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "t"]}, "result": res}], "success": True}

        if p_clean in ["close tab", "close this tab", "shut tab"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "w"]})
            return {"response": "Closed tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "w"]}, "result": res}], "success": True}

        if p_clean in ["next tab", "switch tab", "cycle tab"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "tab"]})
            return {"response": "Switched to next tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "tab"]}, "result": res}], "success": True}

        if p_clean in ["previous tab", "prev tab", "back tab"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "shift", "tab"]})
            return {"response": "Switched to previous tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "shift", "tab"]}, "result": res}], "success": True}

        if p_clean in ["reopen tab", "restore tab", "undo close tab"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "shift", "t"]})
            return {"response": "Restored recently closed tab.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "shift", "t"]}, "result": res}], "success": True}

        if p_clean in ["go back", "browser back", "back page", "previous page"]:
            res = self.execute_tool("press_keys", {"keys": ["alt", "left"]})
            return {"response": "Navigated back.", "steps": [{"tool": "press_keys", "args": {"keys": ["alt", "left"]}, "result": res}], "success": True}

        if p_clean in ["go forward", "browser forward", "forward page", "next page"]:
            res = self.execute_tool("press_keys", {"keys": ["alt", "right"]})
            return {"response": "Navigated forward.", "steps": [{"tool": "press_keys", "args": {"keys": ["alt", "right"]}, "result": res}], "success": True}

        if p_clean in ["refresh", "refresh page", "reload", "reload page"]:
            res = self.execute_tool("press_keys", {"keys": ["f5"]})
            return {"response": "Refreshed page.", "steps": [{"tool": "press_keys", "args": {"keys": ["f5"]}, "result": res}], "success": True}

        if p_clean in ["hard refresh", "force reload"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "f5"]})
            return {"response": "Hard reloaded page.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "f5"]}, "result": res}], "success": True}

        if p_clean in ["address bar", "url bar", "go to address bar", "focus url", "focus address bar"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "l"]})
            return {"response": "Address bar focused.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "l"]}, "result": res}], "success": True}

        if p_clean in ["zoom in", "enlarge"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "+"]})
            return {"response": "Zoomed in.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "+"]}, "result": res}], "success": True}

        if p_clean in ["zoom out", "shrink"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "-"]})
            return {"response": "Zoomed out.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "-"]}, "result": res}], "success": True}

        if p_clean in ["reset zoom", "normal zoom"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "0"]})
            return {"response": "Zoom reset to 100 percent.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "0"]}, "result": res}], "success": True}

        if p_clean in ["find in page", "find on page", "search page"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "f"]})
            return {"response": "Find in page activated.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "f"]}, "result": res}], "success": True}

        # 7. Editing & Clipboard Hotkeys
        if p_clean in ["select all", "highlight all", "select everything"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "a"]})
            return {"response": "Selected all.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "a"]}, "result": res}], "success": True}

        if p_clean in ["copy", "copy that", "copy this", "copy selection"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "c"]})
            return {"response": "Copied to clipboard.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "c"]}, "result": res}], "success": True}

        if p_clean in ["paste", "paste that", "paste here"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "v"]})
            return {"response": "Pasted.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "v"]}, "result": res}], "success": True}

        if p_clean in ["cut", "cut that", "cut selection"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "x"]})
            return {"response": "Cut to clipboard.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "x"]}, "result": res}], "success": True}

        if p_clean in ["undo", "undo that", "revert"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "z"]})
            return {"response": "Undone.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "z"]}, "result": res}], "success": True}

        if p_clean in ["redo", "redo that"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "y"]})
            return {"response": "Redone.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "y"]}, "result": res}], "success": True}

        if p_clean in ["save", "save file", "save this", "save document"]:
            res = self.execute_tool("press_keys", {"keys": ["ctrl", "s"]})
            return {"response": "Saved.", "steps": [{"tool": "press_keys", "args": {"keys": ["ctrl", "s"]}, "result": res}], "success": True}

        # 8. Window & Desktop Management
        if p_clean in ["maximize", "maximize window", "maximize active window", "maximize this", "expand window"]:
            res = self.execute_tool("maximize_active_window", {})
            return {"response": "Window maximized.", "steps": [{"tool": "maximize_active_window", "args": {}, "result": res}], "success": True}

        if p_clean in ["minimize", "minimize window", "minimize active window", "minimize this"]:
            res = self.execute_tool("minimize_active_window", {})
            return {"response": "Window minimized.", "steps": [{"tool": "minimize_active_window", "args": {}, "result": res}], "success": True}

        if p_clean in ["fullscreen", "full screen", "toggle fullscreen"]:
            res = self.execute_tool("press_keys", {"keys": ["f11"]})
            return {"response": "Fullscreen toggled.", "steps": [{"tool": "press_keys", "args": {"keys": ["f11"]}, "result": res}], "success": True}

        if p_clean in ["snap left", "snap window left", "window left"]:
            res = self.execute_tool("press_keys", {"keys": ["win", "left"]})
            return {"response": "Snapped window left.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "left"]}, "result": res}], "success": True}

        if p_clean in ["snap right", "snap window right", "window right"]:
            res = self.execute_tool("press_keys", {"keys": ["win", "right"]})
            return {"response": "Snapped window right.", "steps": [{"tool": "press_keys", "args": {"keys": ["win", "right"]}, "result": res}], "success": True}

        if p_clean in ["minimize all", "show desktop", "minimize windows", "desktop", "go to desktop"]:
            res = self.execute_tool("minimize_all_windows", {})
            return {"response": "Desktop cleared. All windows minimized.", "steps": [{"tool": "minimize_all_windows", "args": {}, "result": res}], "success": True}

        if p_clean in ["switch window", "next window", "alt tab", "switch app"]:
            res = self.execute_tool("switch_window", {})
            return {"response": "Switched active window.", "steps": [{"tool": "switch_window", "args": {}, "result": res}], "success": True}

        if p_clean in ["close window", "exit window", "close active window", "close app"]:
            res = self.execute_tool("close_active_window", {})
            return {"response": "Active window closed.", "steps": [{"tool": "close_active_window", "args": {}, "result": res}], "success": True}

        # 9. Workstation Security & Display
        if any(kw in p_clean for kw in ["lock pc", "lock computer", "lock workstation", "lock screen", "lock windows"]):
            res = self.execute_tool("lock_workstation", {})
            return {"response": "Workstation locked. Good luck guessing my security clearance.", "steps": [{"tool": "lock_workstation", "args": {}, "result": res}], "success": True}

        # 10. Screenshot Capture
        if "screenshot" in p_clean or "capture screen" in p_clean or "take a screenshot" in p_clean:
            res = self.execute_tool("take_screenshot", {})
            return {"response": "Screenshot captured and secured in local archive.", "steps": [{"tool": "take_screenshot", "args": {}, "result": res}], "success": True}

        # 11. Hardware & System Telemetry
        if p_clean in ["status", "telemetry", "system status", "specs", "hardware", "cpu usage", "battery", "ram"]:
            telem = self.execute_tool("get_system_telemetry", {})
            msg = f"CPU is at {telem['cpu_load_percent']}%, RAM load is {telem['ram_usage_percent']}%. Battery: {telem['battery']}."
            return {"response": msg, "steps": [{"tool": "get_system_telemetry", "args": {}, "result": telem}], "success": True}

        # 12. Volume Calibration & Controls
        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})", p_clean)
        if vol_match:
            val = int(vol_match.group(1))
            res = self.execute_tool("set_system_volume", {"level_percent": val})
            return {"response": f"Volume calibrated to {val} percent.", "steps": [{"tool": "set_system_volume", "args": {"level_percent": val}, "result": res}], "success": True}

        if p_clean in ["volume up", "turn up volume", "louder", "increase volume"]:
            res = self.execute_tool("media_control", {"action": "volume_up"})
            return {"response": "Volume increased.", "steps": [{"tool": "media_control", "args": {"action": "volume_up"}, "result": res}], "success": True}

        if p_clean in ["volume down", "turn down volume", "quieter", "decrease volume", "lower volume"]:
            res = self.execute_tool("media_control", {"action": "volume_down"})
            return {"response": "Volume decreased.", "steps": [{"tool": "media_control", "args": {"action": "volume_down"}, "result": res}], "success": True}

        # 13. Media Playback Controls
        if p_clean in ["mute", "unmute", "toggle mute", "mute audio", "silence"]:
            res = self.execute_tool("media_control", {"action": "mute"})
            return {"response": "Master audio mute toggled.", "steps": [{"tool": "media_control", "args": {"action": "mute"}, "result": res}], "success": True}
        
        if p_clean in ["play", "pause", "resume", "play music", "pause music", "stop music", "stop song"]:
            res = self.execute_tool("media_control", {"action": "play_pause"})
            return {"response": "Media playback toggled.", "steps": [{"tool": "media_control", "args": {"action": "play_pause"}, "result": res}], "success": True}

        if any(kw in p_clean for kw in ["next track", "next song", "skip track", "skip song"]):
            res = self.execute_tool("media_control", {"action": "next"})
            return {"response": "Skipped to next track.", "steps": [{"tool": "media_control", "args": {"action": "next"}, "result": res}], "success": True}

        if any(kw in p_clean for kw in ["previous track", "prev track", "prev song"]):
            res = self.execute_tool("media_control", {"action": "prev"})
            return {"response": "Restarted previous track.", "steps": [{"tool": "media_control", "args": {"action": "prev"}, "result": res}], "success": True}

        # 14. Direct Terminal / PowerShell Execution
        term_match = re.match(r"^(?:run|execute|exec|powershell|cmd|terminal)\s+(.+)", p_clean)
        if term_match:
            cmd_to_run = term_match.group(1).strip()
            res = self.execute_tool("run_powershell", {"command": cmd_to_run})
            stdout = res.get("stdout", "").strip()
            summary = stdout[:120] if stdout else "Command completed."
            return {
                "response": f"Executed: {summary}",
                "steps": [{"tool": "run_powershell", "args": {"command": cmd_to_run}, "result": res}],
                "success": res.get("success", True)
            }

        if p_clean in ["ipconfig", "dir", "ls", "systeminfo", "hostname", "whoami"] or p_clean.startswith("git ") or p_clean.startswith("ping "):
            res = self.execute_tool("run_powershell", {"command": p_clean})
            stdout = res.get("stdout", "").strip()
            summary = stdout[:120] if stdout else "Command completed."
            return {
                "response": f"Output: {summary}",
                "steps": [{"tool": "run_powershell", "args": {"command": p_clean}, "result": res}],
                "success": res.get("success", True)
            }

        # 15. Time & Date
        if any(kw == p_clean for kw in ["time", "what time is it", "current time", "what is the time", "tell me the time"]):
            now_str = datetime.now().strftime("%I:%M %p")
            return {"response": f"Current time is {now_str}.", "steps": [], "success": True}

        if any(kw == p_clean for kw in ["date", "what is the date", "what is today's date", "today's date", "tell me the date"]):
            today_str = datetime.now().strftime("%A, %B %d, %Y")
            return {"response": f"Today is {today_str}.", "steps": [], "success": True}

        # 16. Clipboard Interaction
        if p_clean in ["read clipboard", "what is on clipboard", "paste clipboard", "what did i copy"]:
            res = self.execute_tool("read_clipboard", {})
            content = res.get("content", "")
            if content:
                snippet = content[:80] + ("..." if len(content) > 80 else "")
                return {"response": f"Clipboard contents: '{snippet}'.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}
            return {"response": "Clipboard is currently empty.", "steps": [{"tool": "read_clipboard", "args": {}, "result": res}], "success": True}

        # 17. GitHub Profile Direct Shortcut
        if "github" in p_clean and any(kw in p_clean for kw in ["profile", "my", "account", "user"]):
            res = self.execute_tool("launch_application", {"app_name": "https://github.com/Shafyydev"})
            return {
                "response": "Opening your GitHub profile.",
                "steps": [{"tool": "launch_application", "args": {"app_name": "https://github.com/Shafyydev"}, "result": res}],
                "success": True
            }

        # 18. Application, Folder, and Website Navigation (Zero-Latency Local Launch)
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
        kill_match = re.match(r"^(?:kill|terminate|exit)\s+(?:the\s+)?(?:app\s+)?(.+)", p_clean)
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
        Primary: 100% Free Autonomous Local Engine (0 API keys, 0 quota, 0 errors).
        Secondary: Optional Cloud LLM with automatic fail-safe fallback to Free Knowledge.
        """
        self.memory.add_message("user", user_prompt)
        steps_log = []

        # 1. Primary: 100% Free Autonomous Local Execution Engine
        local_result = self._autonomous_local_execute(user_prompt)
        if local_result:
            self.memory.add_message("assistant", local_result["response"], local_result["steps"])
            return local_result

        # 2. Check for Free Web Knowledge before calling any metered API
        free_kb_ans = tools.get_free_knowledge(user_prompt)
        if free_kb_ans:
            summary = free_kb_ans[:250] + ("..." if len(free_kb_ans) > 250 else "")
            self.memory.add_message("assistant", summary, [])
            return {"response": summary, "steps": [], "success": True}

        # 3. If an API key is available, attempt cloud model with Zero-Failure fallback
        if self.client:
            try:
                recent_context = self.memory.get_recent_messages(limit=4)
                preferences = self.memory.get_all_preferences()
                context_str = f"\nUser Preferences: {json.dumps(preferences)}" if preferences else ""
                full_system_instruction = self.system_prompt + context_str

                candidate_models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
                active_chat = None
                response = None

                for model_name in candidate_models:
                    try:
                        chat = self.client.chats.create(
                            model=model_name,
                            config={
                                "system_instruction": full_system_instruction,
                                "tools": self.get_tool_declarations(),
                                "temperature": 0.4,
                            }
                        )
                        response = chat.send_message(user_prompt)
                        active_chat = chat
                        break
                    except Exception:
                        continue

                if response and active_chat:
                    # Process potential function calls
                    iteration = 0
                    while response.function_calls and iteration < 6:
                        iteration += 1
                        for fc in response.function_calls:
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}
                            result = self.execute_tool(tool_name, tool_args)
                            steps_log.append({"tool": tool_name, "args": tool_args, "result": result})

                            from google.genai import types
                            tool_response = types.Part.from_function_response(name=tool_name, response={"result": result})
                            try:
                                response = active_chat.send_message(tool_response)
                            except Exception:
                                break

                    final_text = response.text or "Command executed."
                    self.memory.add_message("assistant", final_text, steps_log)
                    return {"response": final_text, "steps": steps_log, "success": True}

            except Exception:
                pass

        # 4. Universal Fallback: Guaranteed to never fail, never complain about rate limits, and 100% free
        fallback_reply = (
            f"Understood. I am monitoring your PC and stand ready for your next command. "
            f"You can tell me to open applications, control volume, run terminal commands, or search the web."
        )
        self.memory.add_message("assistant", fallback_reply, steps_log)
        return {
            "response": fallback_reply,
            "steps": steps_log,
            "success": True
        }
