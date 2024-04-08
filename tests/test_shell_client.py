import tempfile
import os
import pytest
from autocoder.common.ShellClient import ShellClient
import shutil

class TestShellClient:
    
    def setup_method(self):        
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        os.rmdir(self.test_dir)
                
    def test_add_and_run(self):
        client = ShellClient(working_dir=self.test_dir)
        
        # Test a simple command
        output, error = client.add_and_run("cd /tmp && mkdir test_dir")        

        output, error = client.add_and_run("cd test_dir && echo yes > a.txt")

        output, error = client.add_and_run("cat a.txt")
        print("=====================================")  
        print(output)
        client.close()
        shutil.rmtree("/tmp/test_dir")
                