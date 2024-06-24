from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.common import ExecuteSteps
from typing import List,Dict,Any,Optional,Union

class Interpreter:
    def __init__(self,cwd:Optional[str]=None):
        self.jupyter_client = JupyterNotebook()
        self.shell_client = ShellClient(working_dir=cwd)

    def close(self):
        self.jupyter_client.close()
        self.shell_client.close()    

    def execute_steps(self, steps: ExecuteSteps) -> str:
        jupyter_client = self.jupyter_client
        shell_client = self.shell_client

        if steps.steps[0].cwd:
            self.shell_client.working_dir = steps.steps[0].cwd        
        try:
            output = ""
            for step in steps.steps:
                if step.lang and step.lang.lower() in ["python"]:
                    output += f"Python Code:\n{step.code}\n"
                    output += "Output:\n"
                    result, error = jupyter_client.add_and_run(step.code)
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
                    stdout, stderr = shell_client.add_and_run(step.code)
                    output += stdout + "\n"
                    if stderr:
                        output += f"Error: {stderr}\n"
                else:
                    output += f"Unknown step type: {step.lang}\n"

                output += "-" * 20 + "\n"
        except Exception as e:
            output += f"Error: {str(e)}\n"        

        return output

