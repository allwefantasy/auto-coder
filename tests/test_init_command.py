import os
import shutil
from autocoder.auto_coder import main
from autocoder.command_args import parse_args

def test_init_command():
    # Create a temporary directory for testing
    test_dir = "temp_test_dir"
    os.makedirs(test_dir, exist_ok=True)

    # Call the init command with the test directory
    args = f"init --dir {test_dir}"
    main(parse_args(args.split())[0])

    # Check if the required directories and files are created
    assert os.path.exists(os.path.join(test_dir, "actions"))
    assert os.path.exists(os.path.join(test_dir, ".auto-coder"))
    assert os.path.exists(os.path.join(test_dir, "actions", "101_current_work.yml"))

    # Clean up the temporary test directory
    shutil.rmtree(test_dir)