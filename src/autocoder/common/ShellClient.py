import subprocess
import threading
import os
from typing import Optional,Tuple

class ShellClient:
    def __init__(self, 
                 shell: str = "/bin/bash",
                 timeout: int = 60,
                 working_dir: Optional[str] = None,
                 env: Optional[dict] = None):
        self.shell = shell
        self.timeout = timeout
        self.working_dir = working_dir
        self.env = env or os.environ.copy()
        self.process = subprocess.Popen(self.shell, 
                                        stdin=subprocess.PIPE, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, 
                                        shell=True,
                                        cwd=self.working_dir,
                                        env=self.env)

    def add_and_run(self, command: str) -> Tuple[str, str]:
        # This inner function will be executed in a separate thread
        def run_command_in_thread():
            nonlocal stdout, stderr

            self.process.stdin.write(command.encode() + b"\n")
            self.process.stdin.flush()

            stdout, stderr = self.process.communicate(timeout=self.timeout)
            stdout = stdout.decode()
            stderr = stderr.decode()

        stdout = ""
        stderr = ""

        # Start the thread to run the command
        thread = threading.Thread(target=run_command_in_thread)
        thread.start()

        # Wait for the specified timeout for the thread to finish
        thread.join(timeout=self.timeout)

        # If the thread is still alive after the timeout, it's a timeout
        if thread.is_alive():
            self.process.terminate()
            stdout = "Execution timed out."
            stderr = ""

        return stdout, stderr
        
    def close(self):
        """Close the shell process."""
        self.process.terminate()