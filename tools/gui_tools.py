"""GUI and Computer-Use automation tools for mouse, keyboard, and screen capture."""
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pyautogui

# Safety fail-safe: moving mouse to any screen corner immediately aborts pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


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
    Captures a high-resolution screenshot of the desktop.
    Saves to the screenshots/ directory and returns the absolute filepath.
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
    Moves mouse cursor to (x, y) and performs click(s).
    """
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return {"success": True, "message": f"Clicked at ({x}, {y}) with {button} button ({clicks}x)."}
    except Exception as e:
        return {"success": False, "error": f"Click failed: {str(e)}"}


def double_click(x: int, y: int) -> Dict[str, Any]:
    """Double-clicks at the specified screen coordinate."""
    return click_coordinate(x, y, button="left", clicks=2)


def right_click(x: int, y: int) -> Dict[str, Any]:
    """Right-clicks at the specified screen coordinate."""
    return click_coordinate(x, y, button="right", clicks=1)


def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> Dict[str, Any]:
    """Drags mouse from (start_x, start_y) to (end_x, end_y)."""
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration, button='left')
        return {"success": True, "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."}
    except Exception as e:
        return {"success": False, "error": f"Drag failed: {str(e)}"}


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
    Presses a sequence or combination of keys (e.g. ['ctrl', 'c'] or ['alt', 'tab'] or ['win', 'r']).
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


def switch_window() -> Dict[str, Any]:
    """Switches active window using Alt+Tab."""
    return press_keys(["alt", "tab"])


def close_active_window() -> Dict[str, Any]:
    """Closes the current active window using Alt+F4."""
    return press_keys(["alt", "f4"])
