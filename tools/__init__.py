"""TARS Execution Tools Package."""
from tools.safety import SafetyValidator
from tools.terminal_tools import run_powershell, run_cmd
from tools.os_tools import (
    launch_application,
    kill_process,
    get_system_telemetry,
    set_system_volume,
    media_control,
    get_running_windows,
    minimize_all_windows,
    read_clipboard,
    write_clipboard,
    lock_workstation,
    open_folder
)
from tools.gui_tools import (
    take_screenshot,
    click_coordinate,
    double_click,
    right_click,
    drag_mouse,
    type_text,
    press_keys,
    scroll_screen,
    get_screen_dimensions,
    switch_window,
    close_active_window
)
from tools.browser_tools import open_url, search_web, fetch_webpage_summary

__all__ = [
    "SafetyValidator",
    "run_powershell",
    "run_cmd",
    "launch_application",
    "kill_process",
    "get_system_telemetry",
    "set_system_volume",
    "media_control",
    "get_running_windows",
    "minimize_all_windows",
    "read_clipboard",
    "write_clipboard",
    "lock_workstation",
    "open_folder",
    "take_screenshot",
    "click_coordinate",
    "double_click",
    "right_click",
    "drag_mouse",
    "type_text",
    "press_keys",
    "scroll_screen",
    "get_screen_dimensions",
    "switch_window",
    "close_active_window",
    "open_url",
    "search_web",
    "fetch_webpage_summary"
]
