import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path

from autocoder.common.mcp_hub import McpHub, McpServer, McpTool, McpResource, McpResourceTemplate

# Helper function for async tests
async def run_test(test_func):
    """Helper to run async test functions"""
    try:
        await test_func()
        print("✅ Test passed")
    except AssertionError as e:
        print(f"❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"❌ Test error: {str(e)}")

# Previous test cases...

async def test_filesystem_operations():
    """Test filesystem operations using MCP"""
    # Create settings file with filesystem server config
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        settings = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/Users/allwefantasy/projects/tests"
                    ]
                }
            }
        }
        json.dump(settings, f)
        settings_path = f.name
    
    try:
        # Initialize hub
        hub = McpHub(settings_path)
        await hub.initialize()
        
        # Create directory using tools
        create_dir_args = {
            "path": "tt",
            "recursive": True
        }
        
        try:
            # Call the create directory tool
            result = await hub.call_tool("filesystem", "create-dir", create_dir_args)
            print(f"Directory creation result: {result}")
            
            # Verify directory exists
            assert os.path.exists("/Users/allwefantasy/projects/tests/tt"), "Directory should be created"
            
        except Exception as e:
            print(f"Error during directory creation: {e}")
            raise
            
    finally:
        # Cleanup
        await hub.shutdown()
        os.unlink(settings_path)

# Run the filesystem test
print("Testing filesystem operations:")
asyncio.run(run_test(test_filesystem_operations))