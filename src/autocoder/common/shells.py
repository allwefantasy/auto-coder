
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

def execute_shell_command(command: str, encoding: str = None):
    """
    Execute a shell command with cross-platform encoding support.
    
    Args:
        command (str): The shell command to execute
        encoding (str, optional): Override default encoding. Defaults to None.
    """
    console = Console()
    try:
        # Determine encoding based on platform if not specified
        if encoding is None:
            if sys.platform == 'win32':
                encoding = 'gbk'  # Windows default encoding
            else:
                encoding = 'utf-8'  # Linux/macOS encoding

        # Start subprocess
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        # Safe decoding helper
        def safe_decode(byte_stream, encoding):
            try:
                return byte_stream.decode(encoding).strip()
            except UnicodeDecodeError:
                return byte_stream.decode(encoding, errors='replace').strip()

        output = []
        with Live(console=console, refresh_per_second=4) as live:
            while True:
                # Read output streams
                output_bytes = process.stdout.readline()
                error_bytes = process.stderr.readline()

                # Handle standard output
                if output_bytes:
                    output_line = safe_decode(output_bytes, encoding)
                    output.append(output_line)
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="green",
                        )
                    )

                # Handle error output
                if error_bytes:
                    error_line = safe_decode(error_bytes, encoding)
                    output.append(f"ERROR: {error_line}")
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="red",
                        )
                    )

                # Check if process has ended
                if process.poll() is not None:
                    break

        # Get remaining output
        remaining_out, remaining_err = process.communicate()
        if remaining_out:
            output.append(safe_decode(remaining_out, encoding))
        if remaining_err:
            output.append(f"ERROR: {safe_decode(remaining_err, encoding)}")

        # Show final output
        console.print(
            Panel(
                Text("\n".join(output)),
                title="Final Output",
                border_style="blue",
                subtitle=f"Encoding: {encoding} | OS: {sys.platform}"
            )
        )

        if process.returncode != 0:
            console.print(
                f"[bold red]Command failed with code {process.returncode}[/bold red]"
            )

    except FileNotFoundError:
        console.print(
            f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]"
        )
    except Exception as e:
        console.print(
            f"[bold red]Unexpected error:[/bold red] [yellow]{str(e)}[/yellow]"
        )