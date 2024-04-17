import subprocess
import threading
import queue
import os
import time
from typing import Tuple

class ShellClient:
    def __init__(self, working_dir=os.getcwd(), shell="/bin/bash", timeout=300):
        self.shell = shell
        self.timeout = timeout
        self.process = subprocess.Popen([self.shell], stdin=subprocess.PIPE, cwd=working_dir,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self._start_output_threads()

    def _start_output_threads(self):
        def enqueue_output(stream, queue):
            for line in iter(stream.readline, ''):
                queue.put(line)
            stream.close()

        threading.Thread(target=enqueue_output, args=(self.process.stdout, self.output_queue), daemon=True).start()
        threading.Thread(target=enqueue_output, args=(self.process.stderr, self.error_queue), daemon=True).start()

    def add_and_run(self, command: str) -> Tuple[str, str]:
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

        stdout_lines = []
        stderr_lines = []
        start_time = time.time()

        # Process output until command completes or timeout occurs
        while True:
            if self.output_queue.empty() and self.error_queue.empty():
                # Check if the process has completed the command
                self.process.stdin.write("echo '---done---'\n")
                self.process.stdin.flush()
            try:
                line = self.output_queue.get(timeout=0.1)
                if line.strip() == '---done---':
                    break
                stdout_lines.append(line)
            except queue.Empty:
                pass

            try:
                stderr_line = self.error_queue.get_nowait()
                stderr_lines.append(stderr_line)
            except queue.Empty:
                pass

            if (time.time() - start_time) > self.timeout:
                raise TimeoutError(f"Timeout waiting for command [{command}] to complete")

        return "\n".join(stdout_lines), "\n".join(stderr_lines)

    def close(self):
        self.process.terminate()
