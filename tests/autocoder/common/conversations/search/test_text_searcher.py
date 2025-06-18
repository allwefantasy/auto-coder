"""Tests for text search functionality."""
import pytest
from src.autocoder.common.conversations.search.text_searcher import TextSearcher

class TestTextSearcher:
    def test_text_searcher_creation(self):
        """Test text searcher creation."""
        searcher = TextSearcher()
        assert not searcher.case_sensitive
        assert not searcher.stemming
        assert len(searcher.stop_words) > 0
        
    def test_tokenization(self):
        """Test text tokenization.""" 
        searcher = TextSearcher()
        tokens = searcher._tokenize("Hello world this is a test")
        assert 'hello' in tokens
        assert 'world' in tokens
        assert 'test' in tokens
        assert 'is' not in tokens  # Stop word removed
        
    def test_search_conversations(self):
        """Test conversation search."""
        searcher = TextSearcher()
        conversations = [
            {'name': 'Python Programming', 'description': 'Learn Python'},
            {'name': 'JavaScript Basics', 'description': 'Learn JS'}
        ]
        
        results = searcher.search_conversations("Python", conversations, min_score=0.01)
        assert len(results) == 1
        assert results[0][0]['name'] == 'Python Programming'
        assert results[0][1] > 0
        
    def test_highlight_matches(self):
        """Test text highlighting."""
        searcher = TextSearcher()
        text = "This is a Python test"
        query = "Python"
        highlighted = searcher.highlight_matches(text, query)
        assert "**Python**" in highlighted
        
    def test_search_suggestions(self):
        """Test search suggestions."""
        searcher = TextSearcher()
        conversations = [
            {'name': 'Python Programming', 'description': 'Learn Python'},
            {'name': 'Programming Tutorial', 'description': 'Basic programming'}
        ]
        
        suggestions = searcher.get_search_suggestions("prog", conversations)
        assert len(suggestions) > 0
        assert any("programming" in suggestion.lower() for suggestion in suggestions)
