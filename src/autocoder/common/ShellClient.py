import subprocess
import threading
import os
from typing import Optional,Tuple

class ShellClient:
    def __init__(self, 
                 shell: str = "/bin/bash",
                 timeout: int = 300,
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
        self.process.stdin.write(command.encode() + b"\n")
        self.process.stdin.flush()
        try:
            stdout, stderr = self.process.communicate(timeout=self.timeout)
            stdout = stdout.decode()
            stderr = stderr.decode()
        except subprocess.TimeoutExpired:            
            stdout = "Execution timed out."
            stderr = ""                    
        return stdout, stderr
        
    def close(self):
        """Close the shell process."""
        self.process.terminate()