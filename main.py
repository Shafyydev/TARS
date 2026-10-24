import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
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


def test_microphone() -> None:
    """Runs an instant microphone and speech-to-text benchmark."""
    console.print("\n[bold yellow]🎙️  Testing Microphone & Speech Recognition...[/bold yellow]")
    listener = VoiceListener()
    if not listener._recognizer or not listener._microphone:
        console.print("[bold red]❌ Microphone failed to initialize. Check Windows audio settings.[/bold red]")
        return

    console.print("[dim cyan]Calibrating ambient acoustics...[/dim cyan]")
    thresh = listener.calibrate(duration=0.5)
    console.print(f"[green]✓ Ambient energy threshold set to: {int(thresh)}[/green]")

    console.print("\n[bold green]Speak something into your microphone now (e.g. 'Hello TARS' or 'open Chrome')...[/bold green]")
    t0 = time.time()
    text, status = listener.listen_once(timeout=8, phrase_time_limit=8)
    elapsed = time.time() - t0

    if text:
        console.print(f"\n[bold green]✓ SUCCESS! Captured in {elapsed:.2f}s:[/bold green] [bold white]\"{text}\"[/bold white]")
        speaker = VoiceSpeaker(fast_voice=True)
        speaker.speak(f"Test successful. Heard {text}.", blocking=True)
    else:
        console.print(f"\n[bold red]❌ No speech transcribed. Status: {status}[/bold red]")
        console.print("[dim yellow]Tips: Check your Windows Default Microphone volume in Settings > Sound.[/dim yellow]")


def run_diagnostics() -> None:
    """Runs a quick hardware and tool self-test."""
    console.print("[bold yellow]Running TARS Core Tool Diagnostics...[/bold yellow]\n")
    
    # 1. PowerShell Test
    ps_res = tools.run_powershell("Write-Output 'PowerShell Subsystem Operational'")
    console.print(f"[{'green' if ps_res['success'] else 'red'}][+] PowerShell Engine: {ps_res['stdout']}[/]")

    # 2. Telemetry Test
    telem = tools.get_system_telemetry()
    console.print(f"[green][+] Hardware Sensors: CPU {telem['cpu_load_percent']}%, RAM {telem['ram_usage_percent']}%, Battery: {telem['battery']}[/green]")

    # 3. Screen Dimensions
    dims = tools.get_screen_dimensions()
    console.print(f"[green][+] Primary Display: {dims['width']}x{dims['height']} pixels[/green]")

    # 4. Running Windows
    wins = tools.get_running_windows()
    console.print(f"[green][+] Window Enumeration: Detected {len(wins)} active window(s)[/green]")

    # 5. Audio Synthesizer Test
    speaker = VoiceSpeaker()
    console.print(f"[green][+] Voice Synthesizer: Configured voice '{speaker.voice_name}' with offline SAPI fallback ready.[/green]")

    console.print("\n[bold green]All core execution engines are ready to take commands.[/bold green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="TARS Autonomous Voice-Driven OS Control Agent")
    parser.add_argument("--text-only", action="store_true", help="Run in silent text-only mode (no audio output)")
    parser.add_argument("--voice", "--voice-only", dest="voice_mode", action="store_true", help="Run in continuous hands-free voice loop")
    parser.add_argument("--neural-voice", action="store_true", help="Use cloud neural Edge-TTS voice (higher fidelity, but slower network latency)")
    parser.add_argument("--fast-voice", action="store_true", default=True, help="Use zero-latency native Windows voice for maximum speed (default)")
    parser.add_argument("--test-mic", action="store_true", help="Test microphone input and speech recognition")
    parser.add_argument("--diagnostics", action="store_true", help="Run hardware and tool diagnostics")
    args = parser.parse_args()

    if args.diagnostics:
        run_diagnostics()
        sys.exit(0)

    if args.test_mic:
        test_microphone()
        sys.exit(0)

    # Initialize TARS Brain & Voice
    agent = TARSAgent()
    use_fast = not args.neural_voice
    speaker = VoiceSpeaker(fast_voice=use_fast) if not args.text_only else None
    listener = VoiceListener() if (args.voice_mode or not args.text_only) else None

    render_hud(agent)

    if listener:
        with console.status("[dim cyan]Calibrating microphone for room acoustics...[/dim cyan]"):
            listener.calibrate(duration=0.4)

    if speaker:
        speaker.speak("TARS operational. All systems online.", blocking=False)

    if args.voice_mode:
        console.print("[bold green]🎙️  CONTINUOUS HANDS-FREE VOICE CONTROL ENGAGED[/bold green]")
        console.print("[white]Speak your command directly anytime. (e.g. [cyan]'open Chrome'[/cyan], [cyan]'volume 50'[/cyan], [cyan]'take a screenshot'[/cyan], [cyan]'status'[/cyan])[/white]")
        console.print("[dim white]Say [bold red]'exit'[/bold red] or [bold red]'disarm'[/bold red] to disarm TARS.[/dim white]\n")
    else:
        console.print("\n[bold white]Modes available:[/bold white]")
        console.print(" • Type your instructions directly.")
        console.print(" • Type [bold cyan]'v'[/bold cyan] or [bold cyan]'voice'[/bold cyan] to speak a single command via microphone.")
        console.print(" • Run with [bold green]python main.py --voice[/bold green] for continuous hands-free voice control.")
        console.print(" • Zero-latency native speech is active by default. (Add [bold green]--neural-voice[/bold green] for cloud Edge-TTS).")
        console.print(" • Type [bold cyan]'exit'[/bold cyan] or [bold cyan]'quit'[/bold cyan] to disarm TARS.\n")

    while True:
        try:
            user_input = None

            if args.voice_mode:
                console.print("\n[bold green]🎙️  Listening... (Speak now)[/bold green]")
                raw_speech, status = listener.listen_once(timeout=8, phrase_time_limit=10) if listener else (None, "no listener")
                
                if status == "timeout":
                    continue
                elif status == "unrecognized":
                    console.print("[dim yellow]⚡ Audio detected, but speech was unclear. Try speaking slightly closer.[/dim yellow]")
                    continue
                elif not raw_speech:
                    time.sleep(0.05)
                    continue

                # Check if wake word prefix was used, or use speech directly
                is_ww, clean_command = listener.check_wake_word(raw_speech)
                
                # If only wake word alone was said ("TARS"), ask user what they want
                if is_ww and not clean_command:
                    console.print(f"[bold cyan]🎙️  You said:[/bold cyan] [bold white]{raw_speech}[/bold white]")
                    if speaker:
                        speaker.speak("Standing by. What is your command?", blocking=True)
                    console.print("[bold yellow]🎙️  Listening for command...[/bold yellow]")
                    follow_speech, _ = listener.listen_once(timeout=6, phrase_time_limit=8)
                    if not follow_speech:
                        continue
                    clean_command = follow_speech

                user_input = clean_command if (is_ww and clean_command) else raw_speech
                console.print(f"[bold cyan]🎙️  You said:[/bold cyan] [bold white]\"{user_input}\"[/bold white]")

                # If using neural cloud voice, speak an immediate acknowledgment while synthesis begins
                if speaker and not speaker.fast_voice:
                    speaker.speak_ack()

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
                        console.print("\n[bold yellow]🎙️  Listening... Speak your command clearly.[/bold yellow]")
                        raw_speech, status = listener.listen_once(timeout=6, phrase_time_limit=8)
                        if not raw_speech:
                            console.print(f"[dim red]No speech detected ({status}).[/dim red]")
                            continue
                        is_ww, clean = listener.check_wake_word(raw_speech)
                        user_input = clean if (is_ww and clean) else raw_speech
                        console.print(f"[bold cyan]🎙️  You said:[/bold cyan] [bold white]\"{user_input}\"[/bold white]")
                    else:
                        console.print("[red]Microphone listener not initialized.[/red]")
                        continue

            # Check shutdown commands
            if user_input.strip().lower() in ["exit", "quit", "disarm", "shutdown", "shut down"]:
                if speaker:
                    speaker.speak("Disarming. Goodbye.", blocking=True)
                console.print("[dim]TARS offline.[/dim]")
                break

            # Status callback
            def on_status(msg: str) -> None:
                console.print(f"[dim yellow]⚡ {msg}[/dim yellow]")

            # Run through Agent ReAct Loop with precise timing
            t_exec_start = time.time()
            with console.status("[bold green]TARS reasoning & executing...[/bold green]", spinner="dots"):
                result = agent.run_agent_loop(user_input, on_status_update=on_status)
            exec_duration = time.time() - t_exec_start

            # Output Spoken / Written Response
            console.print(f"\n[bold green]TARS:[/bold green] {result['response']} [dim green]({exec_duration:.2f}s)[/dim green]\n")

            # Show tool execution details if tools were used
            if result.get("steps"):
                step_table = Table(title="[dim]Tools Executed[/dim]", border_style="dim", box=None)
                step_table.add_column("Tool", style="yellow")
                step_table.add_column("Status", style="green")
                for s in result["steps"]:
                    status = "OK" if s.get("result", {}).get("success", True) else "FAILED"
                    step_table.add_row(s["tool"], status)
                console.print(step_table)

            # Speak response aloud (blocking in voice mode so mic doesn't capture TARS)
            if speaker and result.get("response"):
                speaker.speak(result["response"], blocking=args.voice_mode)

        except KeyboardInterrupt:
            console.print("\n[dim]TARS interrupted. Shutting down.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")


if __name__ == "__main__":
    main()
