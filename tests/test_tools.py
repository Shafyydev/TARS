"""Unit tests for TARS execution tools, voice components, and safety layer."""
import unittest
from tools.safety import SafetyValidator
from tools.terminal_tools import run_powershell
from tools.os_tools import get_system_telemetry
from tools.gui_tools import get_screen_dimensions
from core.memory import MemoryStore
from core.voice_speaker import VoiceSpeaker
from core.voice_listener import VoiceListener
from core.brain import TARSAgent


class TestTARS(unittest.TestCase):

    def setUp(self):
        self.safety = SafetyValidator()
        self.memory = MemoryStore(":memory:")
        self.speaker = VoiceSpeaker()
        self.listener = VoiceListener()
        self.agent = TARSAgent()

    def test_safe_command(self):
        is_allowed, req_confirm, reason = self.safety.evaluate_command("Get-Process")
        self.assertTrue(is_allowed)
        self.assertFalse(req_confirm)

    def test_blocked_destructive_command(self):
        is_allowed, req_confirm, reason = self.safety.evaluate_command("rmdir /s /q c:\\windows")
        self.assertFalse(is_allowed)

    def test_confirmation_required_command(self):
        is_allowed, req_confirm, reason = self.safety.evaluate_command("git reset --hard HEAD~1")
        self.assertTrue(is_allowed)
        self.assertTrue(req_confirm)

    def test_powershell_execution(self):
        res = run_powershell("Write-Output 'TARS Online'")
        self.assertTrue(res["success"])
        self.assertIn("TARS Online", res["stdout"])

    def test_telemetry(self):
        telem = get_system_telemetry()
        self.assertIn("cpu_load_percent", telem)
        self.assertIn("ram_usage_percent", telem)
        self.assertGreaterEqual(telem["ram_usage_percent"], 0)

    def test_screen_dimensions(self):
        dims = get_screen_dimensions()
        self.assertIn("width", dims)
        self.assertIn("height", dims)
        self.assertGreater(dims["width"], 0)
        self.assertGreater(dims["height"], 0)

    def test_memory_store(self):
        self.memory.set_user_preference("humor", 85)
        val = self.memory.get_user_preference("humor")
        self.assertEqual(val, 85)

        self.memory.add_message("user", "Hello TARS")
        msgs = self.memory.get_recent_messages(limit=5)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["content"], "Hello TARS")

    def test_voice_speaker_text_cleaning(self):
        raw = "Hello **world**! Check [docs](https://google.com) and `python main.py`"
        clean = self.speaker._clean_text_for_speech(raw)
        self.assertNotIn("**", clean)
        self.assertNotIn("`", clean)
        self.assertNotIn("https://", clean)
        self.assertIn("Hello world!", clean)

    def test_voice_listener_wake_word(self):
        is_act, cmd = self.listener.check_wake_word("TARS open chrome")
        self.assertTrue(is_act)
        self.assertEqual(cmd, "open chrome")

        is_act2, cmd2 = self.listener.check_wake_word("hey tars, minimize windows")
        self.assertTrue(is_act2)
    def test_normalize_voice_command(self):
        from core.voice_listener import normalize_voice_command
        self.assertEqual(normalize_voice_command("close this tap"), "close tab")
        self.assertEqual(normalize_voice_command("new tap"), "new tab")
        self.assertEqual(normalize_voice_command("clothes window"), "close window")
        self.assertEqual(normalize_voice_command("write click"), "right click")
        self.assertEqual(normalize_voice_command("ex"), "exit")

    def test_agent_fast_paths(self):
        # 1. Telemetry
        res = self.agent.run_agent_loop("system status")
        self.assertTrue(res["success"])
        self.assertTrue(len(res["steps"]) > 0)
        self.assertEqual(res["steps"][0]["tool"], "get_system_telemetry")

        # 2. Humor query
        res_humor = self.agent.run_agent_loop("what is your humor setting")
        self.assertTrue(res_humor["success"])
        self.assertIn("Humor", res_humor["response"])

        # 3. Switch window
        res_switch = self.agent.run_agent_loop("switch window")
        self.assertTrue(res_switch["success"])
        self.assertEqual(res_switch["steps"][0]["tool"], "switch_window")

    def test_presence_instant_response(self):
        res = self.agent.run_agent_loop("where are you now")
        self.assertTrue(res["success"])
        self.assertIn("system memory", res["response"])

        res_who = self.agent.run_agent_loop("who are you")
        self.assertTrue(res_who["success"])
        self.assertIn("TARS", res_who["response"])

    def test_github_profile_navigation(self):
        res = self.agent.run_agent_loop("go to my profile github")
        self.assertTrue(res["success"])
        self.assertEqual(res["steps"][0]["tool"], "launch_application")
        self.assertIn("Shafyydev", res["steps"][0]["args"]["app_name"])

    def test_gui_controls_fast_paths(self):
        # Click
        res_click = self.agent.run_agent_loop("click")
        self.assertTrue(res_click["success"])
        self.assertEqual(res_click["steps"][0]["tool"], "click_coordinate")

        # Scroll
        res_scroll = self.agent.run_agent_loop("scroll down")
        self.assertTrue(res_scroll["success"])
        self.assertEqual(res_scroll["steps"][0]["tool"], "scroll_screen")

        # Enter key
        res_enter = self.agent.run_agent_loop("press enter")
        self.assertTrue(res_enter["success"])
        self.assertEqual(res_enter["steps"][0]["tool"], "press_keys")

        # New tab
        res_tab = self.agent.run_agent_loop("new tab")
        self.assertTrue(res_tab["success"])
        self.assertEqual(res_tab["steps"][0]["tool"], "press_keys")

        # Maximize
        res_max = self.agent.run_agent_loop("maximize window")
        self.assertTrue(res_max["success"])
        self.assertEqual(res_max["steps"][0]["tool"], "maximize_active_window")

    def test_windows_system_keys(self):
        res_start = self.agent.run_agent_loop("open start menu")
        self.assertTrue(res_start["success"])
        self.assertEqual(res_start["steps"][0]["tool"], "press_keys")

        res_taskmgr = self.agent.run_agent_loop("open task manager")
        self.assertTrue(res_taskmgr["success"])
        self.assertEqual(res_taskmgr["steps"][0]["tool"], "press_keys")

    def test_file_system_operations(self):
        res_create = self.agent.run_agent_loop("create folder test_unit_tars on desktop")
        self.assertTrue(res_create["success"])
        self.assertEqual(res_create["steps"][0]["tool"], "create_file_or_folder")

        res_list = self.agent.run_agent_loop("list files in desktop")
        self.assertTrue(res_list["success"])
        self.assertEqual(res_list["steps"][0]["tool"], "list_directory")

        res_del = self.agent.run_agent_loop("delete folder test_unit_tars on desktop")
        self.assertTrue(res_del["success"])
        self.assertEqual(res_del["steps"][0]["tool"], "delete_file_or_folder")

    def test_network_and_power(self):
        res_ip = self.agent.run_agent_loop("what is my ip")
        self.assertTrue(res_ip["success"])
        self.assertEqual(res_ip["steps"][0]["tool"], "get_network_info")

        res_abort = self.agent.run_agent_loop("cancel shutdown")
        self.assertTrue(res_abort["success"])
        self.assertEqual(res_abort["steps"][0]["tool"], "system_power")

    def test_resolve_system_target(self):
        from tools.os_tools import resolve_system_target
        from pathlib import Path
        
        # Test Drive resolution
        d_path = resolve_system_target("d drive")
        self.assertIsNotNone(d_path)
        self.assertTrue(str(d_path).upper().startswith("D:"))

        c_path = resolve_system_target("c drive")
        self.assertIsNotNone(c_path)
        self.assertTrue(str(c_path).upper().startswith("C:"))

        # Test Known directory resolution
        codehub_p = resolve_system_target("codehub")
        self.assertIsNotNone(codehub_p)
        self.assertIn("codehub", str(codehub_p).lower())

        codehub_folder_p = resolve_system_target("code hub folder")
        self.assertIsNotNone(codehub_folder_p)
        self.assertIn("codehub", str(codehub_folder_p).lower())

    def test_drive_and_folder_navigation(self):
        # Open D drive
        res_d = self.agent.run_agent_loop("open d drive")
        self.assertTrue(res_d["success"])
        self.assertEqual(res_d["steps"][0]["tool"], "open_folder")
        self.assertIn("D:", res_d["steps"][0]["args"]["folder_path"].upper())

        # Go to D drive
        res_god = self.agent.run_agent_loop("go to d drive")
        self.assertTrue(res_god["success"])
        self.assertEqual(res_god["steps"][0]["tool"], "open_folder")

        # Open code hub folder
        res_ch = self.agent.run_agent_loop("open code hub folder")
        self.assertTrue(res_ch["success"])
        self.assertEqual(res_ch["steps"][0]["tool"], "open_folder")

        # Go to codehub
        res_gch = self.agent.run_agent_loop("go to codehub")
        self.assertTrue(res_gch["success"])
        self.assertEqual(res_gch["steps"][0]["tool"], "open_folder")

    def test_explorer_gui_hotkeys(self):
        # Go up one level
        res_up = self.agent.run_agent_loop("go up")
        self.assertTrue(res_up["success"])
        self.assertEqual(res_up["steps"][0]["tool"], "press_keys")
        self.assertEqual(res_up["steps"][0]["args"]["keys"], ["alt", "up"])

        # Create new folder
        res_nf = self.agent.run_agent_loop("new folder")
        self.assertTrue(res_nf["success"])
        self.assertEqual(res_nf["steps"][0]["tool"], "press_keys")
        self.assertEqual(res_nf["steps"][0]["args"]["keys"], ["ctrl", "shift", "n"])

        # Rename
        res_rn = self.agent.run_agent_loop("rename")
        self.assertTrue(res_rn["success"])
        self.assertEqual(res_rn["steps"][0]["tool"], "press_keys")
        self.assertEqual(res_rn["steps"][0]["args"]["keys"], ["f2"])

        # Dismiss popup / cancel dialog
        res_esc = self.agent.run_agent_loop("dismiss popup")
        self.assertTrue(res_esc["success"])
        self.assertEqual(res_esc["steps"][0]["tool"], "press_keys")
        self.assertEqual(res_esc["steps"][0]["args"]["keys"], ["escape"])

        # Focus address bar
        res_addr = self.agent.run_agent_loop("address bar")
        self.assertTrue(res_addr["success"])
        self.assertEqual(res_addr["steps"][0]["tool"], "press_keys")
        self.assertEqual(res_addr["steps"][0]["args"]["keys"], ["alt", "d"])

    def test_voice_interruption_and_silence(self):
        # 1. Silence & stop talking command
        res_stop = self.agent.run_agent_loop("stop talking")
        self.assertTrue(res_stop["success"])
        self.assertEqual(res_stop["response"], "Standing by.")

        res_quiet = self.agent.run_agent_loop("be quiet")
        self.assertTrue(res_quiet["success"])
        self.assertEqual(res_quiet["response"], "Standing by.")

        # 2. Presence & hear me query
        res_hear = self.agent.run_agent_loop("can you hear me")
        self.assertTrue(res_hear["success"])
        self.assertIn("Loud and clear", res_hear["response"])

        # 3. Speaker stop capability
        self.speaker.stop()
        self.assertFalse(self.speaker.is_speaking)

        # 4. Barge-in monitor creation
        monitor = self.listener.create_barge_in_monitor()
        if monitor:
            self.assertFalse(monitor.is_triggered())
            monitor.stop()


if __name__ == "__main__":
    unittest.main()
