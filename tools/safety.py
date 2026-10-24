"""Safety and security validator for TARS execution commands."""
import json
import re
from pathlib import Path
from typing import Tuple, Optional


class SafetyValidator:
    """Validates commands and actions to prevent unintended system destruction."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "config" / "safety_rules.json"
        
        self.config_path = config_path
        self.blocked_commands = []
        self.confirmation_patterns = []
        self.protected_paths = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Loads safety rules from JSON configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.blocked_commands = [c.lower().strip() for c in data.get("blocked_commands", [])]
                    self.confirmation_patterns = [
                        re.compile(p, re.IGNORECASE) for p in data.get("confirmation_required_patterns", [])
                    ]
                    self.protected_paths = [p.lower() for p in data.get("protected_paths", [])]
            except Exception as e:
                print(f"[Warning] Failed to load safety rules: {e}")

    def evaluate_command(self, command: str) -> Tuple[bool, bool, str]:
        """
        Evaluates a shell/OS command.
        
        Returns:
            (is_allowed: bool, requires_confirmation: bool, reason: str)
        """
        cmd_clean = command.strip().lower()

        # 1. Check outright blocked commands
        for blocked in self.blocked_commands:
            if blocked in cmd_clean:
                return False, False, f"Command contains blocked destructive sequence: '{blocked}'"

        # 2. Check protected system paths
        for path in self.protected_paths:
            if path in cmd_clean and any(destructive in cmd_clean for destructive in ["rm", "del", "remove", "rd"]):
                return False, False, f"Attempted deletion targeting protected system path: '{path}'"

        # 3. Check patterns that require human confirmation
        for pattern in self.confirmation_patterns:
            if pattern.search(command):
                return True, True, f"Command matches sensitive pattern '{pattern.pattern}'. Confirmation required."

        return True, False, "Command is safe to execute."
