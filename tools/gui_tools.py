"""GUI and Computer-Use automation tools for mouse, keyboard, and screen capture."""
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pyautogui

# Safety fail-safe: moving mouse to any corner will abort pyautogui execution
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def get_screen_dimensions() -> Dict[str, int]:
    """Returns the width and height of the primary screen in pixels."""
    width, height = pyautogui.size()
    return {"width": width, "height": height}


def get_mouse_position() -> Dict[str, int]:
    """Returns current mouse cursor X and Y coordinates."""
    x, y = pyautogui.position()
    return {"x": x, "y": y}


def take_screenshot(filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Captures a full-resolution screenshot of the desktop.
    Saves to the screenshots/ folder.
    """
    try:
        screenshots_dir = Path(__file__).resolve().parent.parent / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

        if not filename:
            timestamp = int(time.time())
            filename = f"tars_screen_{timestamp}.png"

        filepath = screenshots_dir / filename
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)

        return {
            "success": True,
            "filepath": str(filepath),
            "width": screenshot.width,
            "height": screenshot.height
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to capture screenshot: {str(e)}"}


def click_coordinate(x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
    """
    Moves mouse cursor smoothly to (x, y) and executes the requested click(s).
    """
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return {"success": True, "message": f"Clicked at ({x}, {y}) with {button} button ({clicks}x)."}
    except Exception as e:
        return {"success": False, "error": f"Click failed: {str(e)}"}


def type_text(text: str, interval: float = 0.01, press_enter: bool = False) -> Dict[str, Any]:
    """
    Types text into the active window. Supports optionally pressing Enter after typing.
    """
    try:
        pyautogui.write(text, interval=interval)
        if press_enter:
            pyautogui.press("enter")
        return {"success": True, "message": f"Typed '{text}' successfully."}
    except Exception as e:
        return {"success": False, "error": f"Typing failed: {str(e)}"}


def press_keys(keys: List[str]) -> Dict[str, Any]:
    """
    Presses a sequence or combination of keys (e.g. ['ctrl', 'c'] or ['alt', 'tab'] or ['enter']).
    """
    try:
        clean_keys = [k.strip().lower() for k in keys]
        if len(clean_keys) == 1:
            pyautogui.press(clean_keys[0])
        else:
            pyautogui.hotkey(*clean_keys)
        return {"success": True, "message": f"Pressed hotkey combo: {' + '.join(clean_keys)}"}
    except Exception as e:
        return {"success": False, "error": f"Key combination failed: {str(e)}"}


def scroll_screen(amount: int) -> Dict[str, Any]:
    """
    Scrolls vertically. Positive number scrolls up, negative scrolls down.
    """
    try:
        pyautogui.scroll(amount)
        direction = "up" if amount > 0 else "down"
        return {"success": True, "message": f"Scrolled {direction} by {abs(amount)} units."}
    except Exception as e:
        return {"success": False, "error": f"Scroll failed: {str(e)}"}
