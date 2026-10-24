"""TARS — Autonomous Voice-Driven OS Control Agent Entrypoint."""
import sys
import time
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

from core.brain import TARSAgent
from core.voice_speaker import VoiceSpeaker
from core.voice_listener import VoiceListener
import tools

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True)

TARS_BANNER = """
 ████████╗ █████╗ ██████╗ ███████╗
 ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝
    ██║   ███████║██████╔╝███████╗
    ██║   ██╔══██║██╔══██╗╚════██║
    ██║   ██║  ██║██║  ██║███████║
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
    Tactical Autonomous Robotic System
"""


def render_hud(agent: TARSAgent) -> None:
    """Renders the futuristic status dashboard."""
    console.print(Panel(Text(TARS_BANNER, style="bold cyan"), border_style="cyan", expand=False))
    
    # System Telemetry Table
    telemetry = tools.get_system_telemetry()
    p = agent.settings.get("personality", {})

    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")

    info_table = Table(show_header=False, border_style="dim", box=None)
    info_table.add_column(style="cyan")
    info_table.add_column(style="white")

    info_table.add_row("Status", "[bold green]ONLINE & ARMED[/bold green]")
    info_table.add_row("Honesty Matrix", f"{int(p.get('honesty', 0.90) * 100)}%")
    info_table.add_row("Humor Matrix", f"{int(p.get('humor', 0.75) * 100)}%")
    info_table.add_row("Sarcasm Matrix", f"{int(p.get('sarcasm', 0.60) * 100)}%")
    info_table.add_row("CPU Load", f"{telemetry.get('cpu_load_percent')}%")
    info_table.add_row("RAM Used", f"{telemetry.get('ram_used_gb')} / {telemetry.get('ram_total_gb')} GB ({telemetry.get('ram_usage_percent')}%)")
    info_table.add_row("Battery", str(telemetry.get('battery')))

    console.print(Panel(info_table, title="[bold cyan]SYSTEM TELEMETRY & MATRICES[/bold cyan]", border_style="cyan"))


def run_diagnostics() -> None:
    """Runs a quick hardware and tool self-test."""
    console.print("[bold yellow]Running TARS Core Tool Diagnostics...[/bold yellow]\n")
    
    # 1. PowerShell Test
    ps_res = tools.run_powershell("Write-Output 'PowerShell Subsystem Operational'")
    console.print(f"[{'green' if ps_res['success'] else 'red'}][+] PowerShell Engine: {ps_res['stdout']}[/]")

    # 2. Telemetry Test
    telem = tools.get_system_telemetry()
    console.print(f"[green][+] Hardware Sensors: CPU {telem['cpu_load_percent']}%, RAM {telem['ram_usage_percent']}%[/green]")

    # 3. Screen Dimensions
    dims = tools.get_screen_dimensions()
    console.print(f"[green][+] Primary Display: {dims['width']}x{dims['height']} pixels[/green]")

    # 4. Running Windows
    wins = tools.get_running_windows()
    console.print(f"[green][+] Window Enumeration: Detected {len(wins)} active window(s)[/green]")

    console.print("\n[bold green]All core execution engines are ready to take commands.[/bold green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="TARS Autonomous OS Control Agent")
    parser.add_argument("--text-only", action="store_true", help="Run without voice output")
    parser.add_argument("--voice-only", action="store_true", help="Run in continuous voice listening loop")
    parser.add_argument("--diagnostics", action="store_true", help="Run hardware and tool diagnostics")
    args = parser.parse_args()

    if args.diagnostics:
        run_diagnostics()
        sys.exit(0)

    # Initialize TARS Brain & Voice
    agent = TARSAgent()
    speaker = VoiceSpeaker() if not args.text_only else None
    listener = VoiceListener() if (args.voice_only or not args.text_only) else None

    render_hud(agent)

    if speaker:
        speaker.speak("TARS operational. All systems online.", blocking=False)

    console.print("\n[bold white]Modes available:[/bold white]")
    console.print(" • Type your instructions directly.")
    console.print(" • Type [bold cyan]'v'[/bold cyan] or [bold cyan]'voice'[/bold cyan] to speak via microphone.")
    console.print(" • Type [bold cyan]'exit'[/bold cyan] or [bold cyan]'quit'[/bold cyan] to disarm TARS.\n")

    while True:
        try:
            if args.voice_only:
                console.print("\n[bold yellow]🎙️  Listening for command... (speak now)[/bold yellow]")
                user_input = listener.listen_once(timeout=8, phrase_time_limit=12) if listener else None
                if not user_input:
                    time.sleep(0.5)
                    continue
                console.print(f"[bold cyan]You (Voice):[/bold cyan] {user_input}")
            else:
                user_input = Prompt.ask("[bold cyan]TARS >[/bold cyan]")
                if not user_input or not user_input.strip():
                    continue

                if user_input.strip().lower() in ["exit", "quit", "q"]:
                    if speaker:
                        speaker.speak("Disarming. Goodbye.", blocking=True)
                    console.print("[dim]TARS offline.[/dim]")
                    break

                if user_input.strip().lower() in ["v", "voice"]:
                    if listener:
                        console.print("[bold yellow]🎙️  Listening... Speak your command clearly.[/bold yellow]")
                        user_input = listener.listen_once(timeout=6, phrase_time_limit=10)
                        if not user_input:
                            console.print("[dim red]No speech detected.[/dim red]")
                            continue
                        console.print(f"[bold cyan]You (Voice):[/bold cyan] {user_input}")
                    else:
                        console.print("[red]Microphone listener not initialized.[/red]")
                        continue

            # Status callback
            def on_status(msg: str) -> None:
                console.print(f"[dim yellow]⚡ {msg}[/dim yellow]")

            # Run through Agent ReAct Loop
            with console.status("[bold green]TARS reasoning & executing...[/bold green]", spinner="dots"):
                result = agent.run_agent_loop(user_input, on_status_update=on_status)

            # Output Spoken / Written Response
            console.print(f"\n[bold green]TARS:[/bold green] {result['response']}\n")

            # Show tool execution details if tools were used
            if result.get("steps"):
                step_table = Table(title="[dim]Tools Executed[/dim]", border_style="dim", box=None)
                step_table.add_column("Tool", style="yellow")
                step_table.add_column("Status", style="green")
                for s in result["steps"]:
                    status = "OK" if s.get("result", {}).get("success", True) else "FAILED"
                    step_table.add_row(s["tool"], status)
                console.print(step_table)

            # Speak response aloud
            if speaker and result.get("response"):
                speaker.speak(result["response"], blocking=False)

        except KeyboardInterrupt:
            console.print("\n[dim]TARS interrupted. Shutting down.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")


if __name__ == "__main__":
    main()
