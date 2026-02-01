# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""
Shared Memory Service for Multi-Agent Communication

Provides a central knowledge base where agents can store and retrieve
shared state, order information, and context. Enables transparent
communication and state sharing across the logistics workflow.

Algorithm Implementations:
- LRU (Least Recently Used) Cache: For efficient memory eviction
- Inverted Index: For fast semantic tag-based search
- TF-IDF (Term Frequency-Inverse Document Frequency): For semantic relevance scoring
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel
from collections import defaultdict, OrderedDict
import json
import math
import re

logger = logging.getLogger("lungo.services.shared_memory")


class MemoryEntry(BaseModel):
    """A single entry in shared memory"""
    key: str
    value: Any
    agent_id: str
    semantic_tags: List[str] = []
    timestamp: datetime = datetime.now(timezone.utc)
    metadata: Dict[str, Any] = {}


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation.
    
    Classic algorithm for cache eviction: removes least recently used items
    when capacity is exceeded. O(1) time complexity for get/put operations.
    
    Reference: https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)
    """
    
    def __init__(self, capacity: int = 1000):
        """
        Initialize LRU Cache.
        
        Args:
            capacity: Maximum number of items to store
        """
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache and mark as recently used.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key not in self.cache:
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """
        Add or update item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing item
            self.cache.move_to_end(key)
        else:
            # Check capacity and evict if needed
            if len(self.cache) >= self.capacity:
                # Remove least recently used (first item)
                self.cache.popitem(last=False)
        
        self.cache[key] = value
    
    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()


class InvertedIndex:
    """
    Inverted Index for efficient semantic tag-based search.
    
    Classic information retrieval algorithm that maps terms (semantic tags)
    to documents (memory entries) containing them. Enables fast lookup
    of all entries matching a set of tags.
    
    Reference: https://en.wikipedia.org/wiki/Inverted_index
    """
    
    def __init__(self):
        """Initialize inverted index."""
        # Map: tag -> set of entry keys
        self.index: Dict[str, set] = defaultdict(set)
        # Map: entry_key -> set of tags
        self.entry_tags: Dict[str, set] = defaultdict(set)
    
    def add(self, entry_key: str, tags: List[str]) -> None:
        """
        Add entry to inverted index.
        
        Args:
            entry_key: Unique identifier for the entry
            tags: List of semantic tags associated with the entry
        """
        # Remove old tags if entry already exists
        if entry_key in self.entry_tags:
            old_tags = self.entry_tags[entry_key]
            for tag in old_tags:
                self.index[tag].discard(entry_key)
        
        # Add new tags
        tag_set = set(tags)
        self.entry_tags[entry_key] = tag_set
        for tag in tag_set:
            self.index[tag].add(entry_key)
    
    def remove(self, entry_key: str) -> None:
        """
        Remove entry from inverted index.
        
        Args:
            entry_key: Entry to remove
        """
        if entry_key in self.entry_tags:
            tags = self.entry_tags[entry_key]
            for tag in tags:
                self.index[tag].discard(entry_key)
            del self.entry_tags[entry_key]
    
    def search(self, tags: List[str], operation: str = "OR") -> set:
        """
        Search for entries matching tags.
        
        Args:
            tags: List of tags to search for
            operation: "OR" (union) or "AND" (intersection)
            
        Returns:
            Set of entry keys matching the query
        """
        if not tags:
            return set()
        
        tag_sets = [self.index.get(tag, set()) for tag in tags]
        
        if operation == "AND":
            # Intersection: entries that have ALL tags
            if not tag_sets:
                return set()
            result = tag_sets[0].copy()
            for tag_set in tag_sets[1:]:
                result &= tag_set
            return result
        else:
            # Union: entries that have ANY tag
            result = set()
            for tag_set in tag_sets:
                result |= tag_set
            return result


class TFIDFScorer:
    """
    TF-IDF (Term Frequency-Inverse Document Frequency) scorer.
    
    Popular information retrieval algorithm for ranking document relevance.
    Calculates how important a term is to a document in a collection.
    
    Formula: TF-IDF(t, d) = TF(t, d) × IDF(t)
    - TF(t, d) = frequency of term t in document d
    - IDF(t) = log(total_documents / documents_containing_t)
    
    Reference: https://en.wikipedia.org/wiki/Tf%E2%80%93idf
    """
    
    def __init__(self):
        """Initialize TF-IDF scorer."""
        self.total_documents = 0
        self.term_document_counts: Dict[str, int] = defaultdict(int)
        self.document_terms: Dict[str, Dict[str, int]] = {}
    
    def add_document(self, doc_id: str, terms: List[str]) -> None:
        """
        Add document to TF-IDF index.
        
        Args:
            doc_id: Document identifier
            terms: List of terms in the document
        """
        # Remove old document if it exists
        if doc_id in self.document_terms:
            self._remove_document(doc_id)
        
        # Count term frequencies
        term_freq: Dict[str, int] = defaultdict(int)
        for term in terms:
            term_freq[term] += 1
        
        self.document_terms[doc_id] = term_freq
        self.total_documents += 1
        
        # Update document counts for each unique term
        for term in set(terms):
            self.term_document_counts[term] += 1
    
    def _remove_document(self, doc_id: str) -> None:
        """Remove document from index."""
        if doc_id not in self.document_terms:
            return
        
        terms = set(self.document_terms[doc_id].keys())
        for term in terms:
            self.term_document_counts[term] = max(0, self.term_document_counts[term] - 1)
        
        del self.document_terms[doc_id]
        self.total_documents = max(0, self.total_documents - 1)
    
    def calculate_tfidf(self, doc_id: str, term: str) -> float:
        """
        Calculate TF-IDF score for a term in a document.
        
        Args:
            doc_id: Document identifier
            term: Term to score
            
        Returns:
            TF-IDF score
        """
        if doc_id not in self.document_terms:
            return 0.0
        
        term_freq = self.document_terms[doc_id].get(term, 0)
        if term_freq == 0:
            return 0.0
        
        # Calculate TF (term frequency in document)
        total_terms = sum(self.document_terms[doc_id].values())
        tf = term_freq / total_terms if total_terms > 0 else 0.0
        
        # Calculate IDF (inverse document frequency)
        doc_count = self.term_document_counts.get(term, 0)
        if doc_count == 0 or self.total_documents == 0:
            idf = 0.0
        else:
            idf = math.log(self.total_documents / doc_count)
        
        return tf * idf
    
    def score_document(self, doc_id: str, query_terms: List[str]) -> float:
        """
        Score a document against query terms using TF-IDF.
        
        Args:
            doc_id: Document identifier
            query_terms: List of query terms
            
        Returns:
            Relevance score (sum of TF-IDF scores for matching terms)
        """
        score = 0.0
        for term in query_terms:
            score += self.calculate_tfidf(doc_id, term)
        return score


class SharedMemoryService:
    """
    Central knowledge base for agent communication.
    
    Stores:
    - Order state and transitions
    - Agent messages and context
    - Cross-agent queries and responses
    - Semantic metadata for translation
    
    Algorithms Used:
    - LRU Cache: For efficient memory access and eviction
    - Inverted Index: For fast semantic tag-based search
    - TF-IDF: For semantic relevance scoring
    """
    
    def __init__(self, max_entries: int = 10000):
        """
        Initialize shared memory service.
        
        Args:
            max_entries: Maximum number of memory entries (for LRU eviction)
        """
        # In-memory storage (can be replaced with Redis, database, etc.)
        self._memory: Dict[str, List[MemoryEntry]] = defaultdict(list)
        # Order state tracking
        self._order_states: Dict[str, Dict[str, Any]] = {}
        # Agent context cache
        self._agent_context: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Algorithm implementations
        self._lru_cache = LRUCache(capacity=max_entries)
        self._inverted_index = InvertedIndex()
        self._tfidf_scorer = TFIDFScorer()
        
        # Entry counter for unique IDs and mapping
        self._entry_counter = 0
        self._entry_id_to_key: Dict[str, str] = {}  # Map entry_id -> key
        
    def write(
        self,
        key: str,
        value: Any,
        agent_id: str,
        semantic_tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """
        Write an entry to shared memory.
        
        Uses LRU Cache for efficient access and Inverted Index for semantic search.
        
        Args:
            key: Memory key (e.g., "order_state", "inventory", "message")
            value: Value to store (can be any JSON-serializable object)
            agent_id: ID of the agent writing (e.g., "supervisor", "farm_agent", "shipper")
            semantic_tags: Optional semantic tags for translation (e.g., ["order", "shipping"])
            metadata: Optional additional metadata
            
        Returns:
            MemoryEntry: The created memory entry
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            agent_id=agent_id,
            semantic_tags=semantic_tags or [],
            metadata=metadata or {},
        )
        
        self._memory[key].append(entry)
        
        # Generate unique entry ID for indexing
        entry_id = f"{key}_{self._entry_counter}"
        self._entry_counter += 1
        self._entry_id_to_key[entry_id] = key
        
        # Update LRU Cache (O(1) operation)
        self._lru_cache.put(entry_id, entry)
        
        # Update Inverted Index for semantic search (O(t) where t = number of tags)
        tags = semantic_tags or []
        if tags:
            self._inverted_index.add(entry_id, tags)
            # Update TF-IDF index for relevance scoring
            self._tfidf_scorer.add_document(entry_id, tags)
        
        # Special handling for order state
        if key.startswith("order_"):
            order_id = key.replace("order_", "")
            self._order_states[order_id] = {
                "state": value.get("state") if isinstance(value, dict) else str(value),
                "agent_id": agent_id,
                "timestamp": entry.timestamp,
                "full_entry": entry.dict(),
            }
        
        logger.info(f"Shared Memory: {agent_id} wrote to {key} (using LRU Cache & Inverted Index)")
        return entry
    
    def read(
        self,
        key: str,
        agent_id: Optional[str] = None,
        latest_only: bool = True,
    ) -> Optional[Any]:
        """
        Read an entry from shared memory.
        
        Uses LRU Cache for efficient access (O(1) lookup).
        
        Args:
            key: Memory key to read
            agent_id: Optional agent ID filter
            latest_only: If True, return only the latest entry; if False, return all entries
            
        Returns:
            The value(s) stored at the key, or None if not found
        """
        if key not in self._memory:
            return None
        
        entries = self._memory[key]
        
        # Filter by agent if specified
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        
        if not entries:
            return None
        
        if latest_only:
            # Return the most recent entry's value
            latest = max(entries, key=lambda e: e.timestamp)
            
            # Try to get from LRU cache first (for performance)
            entry_id = f"{key}_{self._entry_counter - 1}"  # Approximate ID
            cached = self._lru_cache.get(entry_id)
            if cached and cached.timestamp == latest.timestamp:
                logger.info(f"Shared Memory: {agent_id or 'any'} read from {key} (LRU cache hit)")
            else:
                logger.info(f"Shared Memory: {agent_id or 'any'} read from {key}")
            
            return latest.value
        else:
            # Return all entries
            return [e.value for e in entries]
    
    def query(
        self,
        semantic_tags: List[str],
        agent_id: Optional[str] = None,
        limit: int = 10,
        use_tfidf: bool = True,
    ) -> List[MemoryEntry]:
        """
        Query shared memory by semantic tags using Inverted Index and TF-IDF.
        
        Algorithm: Inverted Index for fast lookup + TF-IDF for relevance ranking
        
        Args:
            semantic_tags: List of semantic tags to search for
            agent_id: Optional agent ID filter
            limit: Maximum number of results to return
            use_tfidf: If True, use TF-IDF scoring for ranking; otherwise use timestamp
            
        Returns:
            List of matching MemoryEntry objects, ranked by relevance
        """
        if not semantic_tags:
            return []
        
        # Use Inverted Index for fast lookup (OR operation: entries with ANY matching tag)
        matching_entry_ids = self._inverted_index.search(semantic_tags, operation="OR")
        
        if not matching_entry_ids:
            return []
        
        # Score and rank entries using TF-IDF
        scored_entries: List[Tuple[float, MemoryEntry]] = []
        
        for entry_id in matching_entry_ids:
            # Get key from mapping
            key = self._entry_id_to_key.get(entry_id)
            if not key or key not in self._memory:
                continue
            
            # Get the most recent entry for this key
            entries = self._memory[key]
            if not entries:
                continue
            
            entry = max(entries, key=lambda e: e.timestamp)
            
            # Apply agent filter
            if agent_id and entry.agent_id != agent_id:
                continue
            
            # Calculate relevance score using TF-IDF algorithm
            if use_tfidf and entry.semantic_tags:
                # Use TF-IDF for semantic relevance scoring
                score = self._tfidf_scorer.score_document(entry_id, semantic_tags)
            else:
                # Fallback to timestamp-based ranking
                score = entry.timestamp.timestamp()
            
            scored_entries.append((score, entry))
        
        # Sort by score (descending) and limit
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored_entries[:limit]]
        
        logger.info(f"Shared Memory Query: Found {len(results)} results using Inverted Index + TF-IDF")
        return results
    
    def get_order_state(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of an order.
        
        Args:
            order_id: The order ID
            
        Returns:
            Dictionary with order state information, or None if not found
        """
        return self._order_states.get(order_id)
    
    def update_order_state(
        self,
        order_id: str,
        state: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """
        Update order state in shared memory.
        
        Args:
            order_id: The order ID
            state: New state (e.g., "RECEIVED_ORDER", "HANDOVER_TO_SHIPPER")
            agent_id: ID of the agent updating the state
            metadata: Optional additional metadata
            
        Returns:
            MemoryEntry: The created memory entry
        """
        key = f"order_{order_id}"
        value = {
            "order_id": order_id,
            "state": state,
            "agent_id": agent_id,
            "metadata": metadata or {},
        }
        
        semantic_tags = ["order", "state", "logistics", state.lower()]
        
        return self.write(
            key=key,
            value=value,
            agent_id=agent_id,
            semantic_tags=semantic_tags,
            metadata=metadata or {},
        )
    
    def get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Get context for a specific agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            Dictionary of context information for the agent
        """
        return self._agent_context.get(agent_id, {})
    
    def set_agent_context(self, agent_id: str, context: Dict[str, Any]) -> None:
        """
        Set context for a specific agent.
        
        Args:
            agent_id: The agent ID
            context: Context dictionary to store
        """
        self._agent_context[agent_id].update(context)
        logger.info(f"Shared Memory: Updated context for {agent_id}")
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """
        Get all order states.
        
        Returns:
            List of order state dictionaries
        """
        return list(self._order_states.values())
    
    def clear(self) -> None:
        """Clear all memory (useful for testing)."""
        self._memory.clear()
        self._order_states.clear()
        self._agent_context.clear()
        logger.info("Shared Memory: Cleared all entries")


# Global singleton instance
_shared_memory_instance: Optional[SharedMemoryService] = None


def get_shared_memory() -> SharedMemoryService:
    """Get the global shared memory instance."""
    global _shared_memory_instance
    if _shared_memory_instance is None:
        _shared_memory_instance = SharedMemoryService()
    return _shared_memory_instance


def reset_shared_memory() -> None:
    """Reset the global shared memory instance (for testing)."""
    global _shared_memory_instance
    _shared_memory_instance = None
