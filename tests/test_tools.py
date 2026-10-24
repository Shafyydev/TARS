"""Unit tests for TARS execution tools and safety layer."""
import unittest
from tools.safety import SafetyValidator
from tools.terminal_tools import run_powershell
from tools.os_tools import get_system_telemetry
from core.memory import MemoryStore


class TestTARS(unittest.TestCase):

    def setUp(self):
        self.safety = SafetyValidator()
        self.memory = MemoryStore(":memory:")

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

    def test_memory_store(self):
        self.memory.set_user_preference("humor", 85)
        val = self.memory.get_user_preference("humor")
        self.assertEqual(val, 85)

        self.memory.add_message("user", "Hello TARS")
        msgs = self.memory.get_recent_messages(limit=5)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["content"], "Hello TARS")


if __name__ == "__main__":
    unittest.main()
