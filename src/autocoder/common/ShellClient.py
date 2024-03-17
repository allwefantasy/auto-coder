import subprocess
import threading
import queue
from typing import Optional, Tuple
import os
import time



class ShellClient:
    def __init__(self, working_dir=os.getcwd(), shell="/bin/bash", timeout=300):
        self.shell = shell
        self.timeout = timeout
        self.process = subprocess.Popen([self.shell], stdin=subprocess.PIPE, cwd=working_dir,
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self._start_output_thread()

    def _start_output_thread(self):
        def enqueue_output(out, queue):
            for line in iter(out.readline, ''):
                queue.put(line)
            out.close()
        
        threading.Thread(target=enqueue_output, args=(self.process.stdout, self.output_queue)).start()
        threading.Thread(target=enqueue_output, args=(self.process.stderr, self.error_queue)).start()

    def add_and_run(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

        stdout_lines = []
        stderr_lines = []

        # Basic approach to wait for command to complete
        time.sleep(0.5)  # Adjust as needed for the command to start executing
        start_time = time.time()
        while not self.output_queue.empty():
            if (time.time() - start_time) > self.timeout:                
                raise TimeoutError(f"Timeout waiting for command [{command}] to complete")
            stdout_lines.append(self.output_queue.get())

        while not self.error_queue.empty():
            if (time.time() - start_time) > self.timeout:                
                raise TimeoutError(f"Timeout waiting for command [{command}] to complete")                
            stderr_lines.append(self.error_queue.get())

        return "\n".join(stdout_lines), "\n".join(stderr_lines)

    def close(self):
        self.process.terminate()
