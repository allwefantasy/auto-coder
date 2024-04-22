import tempfile
import shutil
import os
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.common import AutoCoderArgs
from byzerllm.llms.fake_llm import FakeLLM

class TestSimpleRAG:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test files
        with open(os.path.join(self.temp_dir, 'file1.txt'), 'w') as f:
            f.write('This is a test file.')
        with open(os.path.join(self.temp_dir, 'file2.txt'), 'w') as f:  
            f.write('Another test file.')
        
        self.llm = FakeLLM()
        self.args = AutoCoderArgs()
        self.rag = SimpleRAG(self.llm, self.args, self.temp_dir)
        self.rag.build()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
        
    def test_search(self):
        results = self.rag.search('test file')
        assert len(results) > 0
        assert 'test file' in results[0].source_code
        
    def test_stream_search(self):
        response_gen, contexts = self.rag.stream_search('Another test')
        response = ''.join([text for text in response_gen])
        assert 'Another test file' in response
        assert len(contexts) > 0
        
    def test_retrieve(self):
        results = self.rag.retrieve('test file')  
        assert len(results) > 0
        assert 'test file' in results[0].text