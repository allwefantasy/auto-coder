"""
Text search functionality for conversations and messages.

This module provides comprehensive text search capabilities including
full-text search, keyword matching, and relevance-based ranking.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import Counter, defaultdict

from ..models import Conversation, ConversationMessage


class TextSearcher:
    """Text searcher for conversations and messages with relevance ranking."""
    
    def __init__(self, case_sensitive: bool = False, stemming: bool = False):
        """
        Initialize text searcher.
        
        Args:
            case_sensitive: Whether search should be case sensitive
            stemming: Whether to apply basic stemming (simplified)
        """
        self.case_sensitive = case_sensitive
        self.stemming = stemming
        
        # Common English stop words for filtering
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'will', 'with', 'would', 'could', 'should',
            'have', 'had', 'has', 'do', 'does', 'did', 'can', 'may', 'might'
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for searching."""
        if not self.case_sensitive:
            text = text.lower()
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple tokenization - split on word boundaries
        tokens = re.findall(r'\b\w+\b', text)
        
        # Normalize tokens
        tokens = [self._normalize_text(token) for token in tokens]
        
        # Remove stop words if not case sensitive
        if not self.case_sensitive:
            tokens = [token for token in tokens if token not in self.stop_words]
        
        # Apply basic stemming if enabled
        if self.stemming:
            tokens = [self._basic_stem(token) for token in tokens]
        
        return tokens
    
    def _basic_stem(self, word: str) -> str:
        """Apply very basic stemming rules."""
        # Simple English stemming rules
        if len(word) <= 3:
            return word
            
        # Remove common suffixes
        suffixes = ['ing', 'ed', 'er', 'est', 'ly', 's']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        
        return word
    
    def _calculate_tf_idf(
        self, 
        query_terms: List[str], 
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate TF-IDF scores for documents."""
        # Count documents containing each term
        doc_count = defaultdict(int)
        doc_terms = {}
        
        for i, doc in enumerate(documents):
            # Combine searchable text from document
            searchable_text = self._get_searchable_text(doc)
            terms = self._tokenize(searchable_text)
            doc_terms[i] = Counter(terms)
            
            # Count unique terms in this document
            unique_terms = set(terms)
            for term in unique_terms:
                doc_count[term] += 1
        
        # Calculate TF-IDF scores
        total_docs = len(documents)
        tf_idf_scores = {}
        
        for i, doc in enumerate(documents):
            tf_idf_scores[i] = {}
            doc_term_counts = doc_terms[i]
            doc_length = sum(doc_term_counts.values())
            
            for term in query_terms:
                if term in doc_term_counts and doc_length > 0:
                    # Term frequency
                    tf = doc_term_counts[term] / doc_length
                    
                    # Inverse document frequency
                    idf = math.log(total_docs / max(1, doc_count[term]))
                    
                    # TF-IDF score
                    tf_idf_scores[i][term] = tf * idf
                else:
                    tf_idf_scores[i][term] = 0.0
        
        return tf_idf_scores
    
    def _get_searchable_text(self, item: Dict[str, Any]) -> str:
        """Extract searchable text from conversation or message."""
        if isinstance(item, dict):
            # Handle different item types
            text_parts = []
            
            # Add name and description for conversations
            if 'name' in item:
                text_parts.append(item['name'])
            if 'description' in item:
                text_parts.append(item.get('description', ''))
            
            # Add content for messages
            if 'content' in item:
                content = item['content']
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, dict):
                    # Extract text from dict content
                    for value in content.values():
                        if isinstance(value, str):
                            text_parts.append(value)
                elif isinstance(content, list):
                    # Extract text from list content
                    for value in content:
                        if isinstance(value, str):
                            text_parts.append(value)
                        elif isinstance(value, dict):
                            for nested_value in value.values():
                                if isinstance(nested_value, str):
                                    text_parts.append(nested_value)
            
            # Add messages content for conversations
            if 'messages' in item:
                for message in item.get('messages', []):
                    text_parts.append(self._get_searchable_text(message))
            
            return ' '.join(filter(None, text_parts))
        
        return str(item)
    
    def search_conversations(
        self,
        query: str,
        conversations: List[Dict[str, Any]],
        max_results: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search conversations with relevance scoring.
        
        Args:
            query: Search query string
            conversations: List of conversation dictionaries
            max_results: Maximum number of results to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of (conversation, score) tuples sorted by relevance
        """
        if not query.strip() or not conversations:
            return [(conv, 0.0) for conv in conversations[:max_results]]
        
        # Tokenize query
        query_terms = self._tokenize(query)
        if not query_terms:
            return [(conv, 0.0) for conv in conversations[:max_results]]
        
        # Calculate TF-IDF scores
        tf_idf_scores = self._calculate_tf_idf(query_terms, conversations)
        
        # Calculate relevance scores
        results = []
        for i, conversation in enumerate(conversations):
            # Sum TF-IDF scores for all query terms
            total_score = sum(tf_idf_scores[i].values())
            
            # Apply boost for exact phrase matches
            searchable_text = self._get_searchable_text(conversation)
            normalized_text = self._normalize_text(searchable_text)
            normalized_query = self._normalize_text(query)
            
            if normalized_query in normalized_text:
                total_score *= 1.5  # Boost for exact phrase match
            
            # Apply boost for title matches
            if 'name' in conversation:
                title_text = self._normalize_text(conversation['name'])
                if any(term in title_text for term in query_terms):
                    total_score *= 1.2  # Boost for title matches
            
            if total_score >= min_score:
                results.append((conversation, total_score))
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Apply result limit
        if max_results:
            results = results[:max_results]
        
        return results
    
    def search_messages(
        self,
        query: str,
        messages: List[Dict[str, Any]],
        max_results: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search messages with relevance scoring.
        
        Args:
            query: Search query string
            messages: List of message dictionaries
            max_results: Maximum number of results to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of (message, score) tuples sorted by relevance
        """
        if not query.strip() or not messages:
            return [(msg, 0.0) for msg in messages[:max_results]]
        
        # Tokenize query
        query_terms = self._tokenize(query)
        if not query_terms:
            return [(msg, 0.0) for msg in messages[:max_results]]
        
        # Calculate TF-IDF scores
        tf_idf_scores = self._calculate_tf_idf(query_terms, messages)
        
        # Calculate relevance scores
        results = []
        for i, message in enumerate(messages):
            # Sum TF-IDF scores for all query terms
            total_score = sum(tf_idf_scores[i].values())
            
            # Apply boost for exact phrase matches
            searchable_text = self._get_searchable_text(message)
            normalized_text = self._normalize_text(searchable_text)
            normalized_query = self._normalize_text(query)
            
            if normalized_query in normalized_text:
                total_score *= 1.5  # Boost for exact phrase match
            
            # Apply boost for recent messages (if timestamp available)
            if 'timestamp' in message:
                # Simple recency boost - more recent messages get slight boost
                import time
                current_time = time.time()
                message_time = message['timestamp']
                age_hours = (current_time - message_time) / 3600
                
                # Boost decreases with age, but not too dramatically
                recency_boost = max(1.0, 1.1 - (age_hours / (24 * 30)))  # Diminishes over a month
                total_score *= recency_boost
            
            if total_score >= min_score:
                results.append((message, total_score))
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Apply result limit
        if max_results:
            results = results[:max_results]
        
        return results
    
    def highlight_matches(
        self,
        text: str,
        query: str,
        highlight_format: str = "**{}**"
    ) -> str:
        """
        Highlight query matches in text.
        
        Args:
            text: Text to highlight matches in
            query: Search query
            highlight_format: Format string for highlighting (e.g., "**{}**" for bold)
            
        Returns:
            Text with highlighted matches
        """
        if not query.strip():
            return text
        
        query_terms = self._tokenize(query)
        if not query_terms:
            return text
        
        # Create regex pattern for all query terms
        escaped_terms = [re.escape(term) for term in query_terms]
        pattern = r'\b(' + '|'.join(escaped_terms) + r')\b'
        
        # Apply highlighting
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        def highlight_replacer(match):
            return highlight_format.format(match.group(1))
        
        return re.sub(pattern, highlight_replacer, text, flags=flags)
    
    def get_search_suggestions(
        self,
        partial_query: str,
        conversations: List[Dict[str, Any]],
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            conversations: List of conversations to analyze
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        if len(partial_query) < 2:
            return []
        
        # Extract all terms from conversations
        all_terms = set()
        for conversation in conversations:
            searchable_text = self._get_searchable_text(conversation)
            terms = self._tokenize(searchable_text)
            all_terms.update(terms)
        
        # Find matching terms
        partial_lower = partial_query.lower()
        suggestions = []
        
        for term in all_terms:
            if term.lower().startswith(partial_lower) and term.lower() != partial_lower:
                suggestions.append(term)
        
        # Sort by length (shorter terms first) and alphabetically
        suggestions.sort(key=lambda x: (len(x), x))
        
        return suggestions[:max_suggestions] 