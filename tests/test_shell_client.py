import tempfile
import os
import pytest
from autocoder.common.ShellClient import ShellClient

class TestShellClient:
    
    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        os.rmdir(self.test_dir)
        
    def test_init(self):
        client = ShellClient(working_dir=self.test_dir)
        assert client.shell == "/bin/bash"
        assert client.timeout == 300
        assert client.process is not None

    def test_add_and_run(self):
        client = ShellClient(working_dir=self.test_dir)
        
        # Test a simple command
        output, error = client.add_and_run("echo hello world")
        assert output.strip() == "hello world"
        assert error == ""
        
        # Test a command with error
        with pytest.raises(TimeoutError):
            client.add_and_run("sleep 310")
            
        # Test a non existing command    
        output, error = client.add_and_run("non_existing_cmd")
        assert "not found" in error
        assert output == ""
            
    def test_close(self):
        client = ShellClient(working_dir=self.test_dir) 
        client.close()
        
        # Process should be terminated
        assert client.process.poll() is not None