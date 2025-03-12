from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.common import ExecuteSteps
from typing import List, Dict, Any, Optional, Callable


class Interpreter:
    def __init__(self, cwd: Optional[str] = None):
        self.jupyter_client = JupyterNotebook()
        self.shell_client = ShellClient(working_dir=cwd)

    def close(self):
        self.jupyter_client.close()
        self.shell_client.close()

    def execute_steps(
        self, steps: ExecuteSteps, output_callback: Optional[Callable] = None
    ) -> str:
        jupyter_client = self.jupyter_client
        shell_client = self.shell_client

        if steps.steps[0].cwd:
            self.shell_client.working_dir = steps.steps[0].cwd
        try:
            output = ""
            for step in steps.steps:
                if step.lang and step.lang.lower() in ["python"]:
                    output += f"Python Code:\n{step.code}\n"
                    if output_callback:
                        output_callback("code", step.code)
                    output += "Output:\n"
                    result, error = jupyter_client.add_and_run(step.code)
                    if output_callback:
                        output_callback("result", result)
                        if error:
                            output_callback("error", error)
                    output += result + "\n"
                    if error:
                        output += f"Error: {str(error)}\n"
                elif step.lang and step.lang.lower() in [
                    "shell",
                    "bash",
                    "sh",
                    "zsh",
                    "ksh",
                    "csh",
                    "powershell",
                    "cmd",
                ]:
                    output += f"Shell Command:\n{step.code}\n"
                    output += "Output:\n"
                    if output_callback:
                        output_callback("code", step.code)
                    stdout, stderr = shell_client.add_and_run(step.code)
                    if output_callback:
                        output_callback("result", stdout)
                        if stderr:
                            output_callback("error", stderr)
                    output += stdout + "\n"
                    if stderr:
                        output += f"Error: {stderr}\n"
                        if output_callback:
                            output_callback("error", stderr)
                else:
                    output += f"Unknown step type: {step.lang}\n"

                output += "-" * 20 + "\n"
        except Exception as e:
            output += f"Error: {str(e)}\n"
            if output_callback:
                output_callback("error", str(e))

        return output
