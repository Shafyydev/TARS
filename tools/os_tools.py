"""Operating System and hardware management tools for Windows."""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import psutil

# Predefined application & web destination mappings for fast voice launching
COMMON_APPS = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "browser": "start chrome",
    "firefox": "start firefox",
    "edge": "start msedge",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "terminal": "start wt",
    "powershell": "start powershell",
    "cmd": "start cmd",
    "spotify": "start spotify:",
    "discord": "start discord:",
    "slack": "start slack:",
    "telegram": "start telegram:",
    "whatsapp": "start whatsapp:",
    "steam": "start steam:",
    "explorer": "explorer",
    "files": "explorer",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "settings": "start ms-settings:",
    "control panel": "control",
    "paint": "mspaint",
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    "obs": "start obs64",
    # Websites & Quick Web Destinations
    "github": "start https://github.com",
    "my github": "start https://github.com/Shafyydev",
    "my profile github": "start https://github.com/Shafyydev",
    "profile github": "start https://github.com/Shafyydev",
    "github profile": "start https://github.com/Shafyydev",
    "youtube": "start https://youtube.com",
    "google": "start https://google.com",
    "gmail": "start https://mail.google.com",
    "mail": "start https://mail.google.com",
    "email": "start https://mail.google.com",
    "chatgpt": "start https://chat.openai.com",
    "reddit": "start https://reddit.com",
    "twitter": "start https://x.com",
    "x": "start https://x.com",
    "linkedin": "start https://linkedin.com",
    "instagram": "start https://instagram.com",
    "netflix": "start https://netflix.com",
    "amazon": "start https://amazon.com",
}


def launch_application(app_name: str) -> Dict[str, Any]:
    """
    Launches an application or web destination by common name or executable path.
    """
    clean_name = app_name.strip().lower()

    # Smart GitHub profile resolution
    if "github" in clean_name and any(kw in clean_name for kw in ["profile", "my", "account", "user"]):
        cmd = "start https://github.com/Shafyydev"
        clean_name = "GitHub profile (Shafyydev)"
    elif clean_name in COMMON_APPS:
        cmd = COMMON_APPS[clean_name]
    elif any(clean_name.endswith(ext) for ext in [".com", ".org", ".io", ".net", ".dev", ".edu", ".gov"]) or clean_name.startswith("http"):
        url = clean_name if clean_name.startswith("http") else f"https://{clean_name}"
        cmd = f"start {url}"
    else:
        # Fallback to direct Windows start
        cmd = f"start \"\" \"{app_name}\""

    try:
        subprocess.Popen(cmd, shell=True)
        return {"success": True, "message": f"Successfully launched {clean_name}."}
    except Exception as e:
        return {"success": False, "error": f"Failed to launch {app_name}: {str(e)}"}


def kill_process(process_name: str) -> Dict[str, Any]:
    """
    Terminates running processes matching the given name (e.g. 'chrome.exe' or 'notepad').
    """
    clean_name = process_name.strip().lower()
    if not clean_name.endswith(".exe"):
        clean_name += ".exe"

    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == clean_name:
                proc.kill()
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed_count > 0:
        return {"success": True, "message": f"Terminated {killed_count} instances of {clean_name}."}
    return {"success": False, "message": f"No running process found matching '{clean_name}'."}


def get_system_telemetry() -> Dict[str, Any]:
    """
    Collects real-time hardware metrics: CPU, RAM, Disk, and Battery.
    """
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    battery = psutil.sensors_battery()

    battery_info = "No battery detected (Desktop)"
    if battery:
        charging = "Plugged in" if battery.power_plugged else "Discharging"
        battery_info = f"{battery.percent}% ({charging})"

    return {
        "cpu_load_percent": cpu_usage,
        "ram_used_gb": round(memory.used / (1024 ** 3), 2),
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "ram_usage_percent": memory.percent,
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "battery": battery_info
    }


def set_system_volume(level_percent: int) -> Dict[str, Any]:
    """
    Sets the Windows master audio endpoint volume (0 to 100).
    """
    level_percent = max(0, min(100, level_percent))
    
    # Try pycaw first if available
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        # pycaw scalar volume is 0.0 to 1.0
        volume.SetMasterVolumeLevelScalar(level_percent / 100.0, None)
        return {"success": True, "message": f"Master volume set to {level_percent}%."}
    except Exception:
        # Fallback using PowerShell
        try:
            ps_vol = f"""
            $obj = New-Object -ComObject WScript.Shell
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            $steps = [math]::Round({level_percent} / 2)
            1..$steps | ForEach-Object {{ $obj.SendKeys([char]175) }}
            """
            subprocess.run(["powershell", "-Command", ps_vol], capture_output=True, timeout=5)
            return {"success": True, "message": f"Volume adjusted to ~{level_percent}% via fallback."}
        except Exception as e:
            return {"success": False, "error": f"Could not adjust volume: {e}"}


def media_control(action: str) -> Dict[str, Any]:
    """
    Sends virtual media keys: 'play_pause', 'next', 'prev', 'stop', 'volume_up', 'volume_down', 'mute'.
    """
    key_codes = {
        "play_pause": 0xB3,
        "next": 0xB0,
        "prev": 0xB1,
        "stop": 0xB2,
        "volume_up": 0xAF,
        "volume_down": 0xAE,
        "mute": 0xAD
    }
    
    action_clean = action.strip().lower()
    if action_clean not in key_codes:
        return {"success": False, "error": f"Unknown media action: {action}. Valid options: {list(key_codes.keys())}"}

    import ctypes
    vk = key_codes[action_clean]
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0) # Key down
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0) # Key up
    return {"success": True, "message": f"Executed media action: {action_clean}"}


def get_running_windows() -> List[str]:
    """
    Returns a list of titles of all currently visible top-level application windows.
    """
    try:
        import win32gui
        windows = []
        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and len(title.strip()) > 1:
                    windows.append(title.strip())
        win32gui.EnumWindows(enum_handler, None)
        return windows[:25]
    except Exception:
        try:
            res = subprocess.run(["tasklist", "/v", "/fo", "csv"], capture_output=True, text=True, timeout=5)
            lines = res.stdout.splitlines()[1:]
            return [line.split(",")[-1].replace('"', '') for line in lines if "N/A" not in line][:20]
        except Exception:
            return []


def minimize_all_windows() -> Dict[str, Any]:
    """Minimizes all windows to show the desktop (Win+D)."""
    import ctypes
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
    return {"success": True, "message": "Minimized all windows."}


def read_clipboard() -> Dict[str, Any]:
    """Reads current text from the Windows clipboard."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return {"success": True, "content": data}
    except Exception as e:
        return {"success": False, "error": f"Failed to read clipboard: {e}"}


def write_clipboard(text: str) -> Dict[str, Any]:
    """Writes text to the Windows clipboard."""
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return {"success": True, "message": "Copied to clipboard."}
    except Exception as e:
        return {"success": False, "error": f"Failed to write to clipboard: {e}"}


def lock_workstation() -> Dict[str, Any]:
    """Locks the Windows workstation instantly."""
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Windows workstation locked."}
    except Exception as e:
        return {"success": False, "error": f"Failed to lock workstation: {e}"}


def open_folder(folder_path: str = "downloads") -> Dict[str, Any]:
    """
    Opens a folder in Windows File Explorer.
    Supports keywords: 'downloads', 'documents', 'desktop', 'pictures', 'videos', or any absolute path.
    """
    user_home = Path.home()
    folder_map = {
        "downloads": user_home / "Downloads",
        "documents": user_home / "Documents",
        "desktop": user_home / "Desktop",
        "pictures": user_home / "Pictures",
        "videos": user_home / "Videos",
        "home": user_home,
    }

    clean_target = folder_path.strip().lower()
    target_path = folder_map.get(clean_target, Path(folder_path))

    if not target_path.exists():
        return {"success": False, "error": f"Folder '{folder_path}' does not exist."}

    try:
        os.startfile(str(target_path))
        return {"success": True, "message": f"Opened folder: {target_path}"}
    except Exception as e:
        return {"success": False, "error": f"Could not open folder: {e}"}
