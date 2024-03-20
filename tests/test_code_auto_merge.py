import os
import shutil
import unittest
from autocoder.common.code_auto_merge import CodeAutoMerge


class TestCodeAutoMerge(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_merge_code(self):
        merger = CodeAutoMerge(None,None)
        text = """
##File: /tmp/src/server/server.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

##File: /tmp/src/main.py
from server.server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

        merger.merge_code(text)

        with open(os.path.join("/tmp/src/server/server.py"), "r") as f:
            self.assertEqual(f.read().strip(), 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef read_root():\n    return {"message": "Hello, World!"}')

        with open(os.path.join("/tmp/src/main.py"), "r") as f:
            self.assertEqual(f.read().strip(), 'from server.server import app\n\nif __name__ == "__main__":\n    import uvicorn\n    uvicorn.run(app, host="0.0.0.0", port=8000)')


if __name__ == "__main__":
    unittest.main()