# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""
Semantic Translation Service for Multi-Agent Communication

Translates messages and queries between different agent vocabularies
while preserving semantic meaning. Enables agents with different
terminologies to understand each other.
"""

import logging
from typing import Any, Dict, List, Optional
from services.shared_memory import get_shared_memory, MemoryEntry

logger = logging.getLogger("lungo.services.semantic_translator")


class SemanticTranslator:
    """
    Translates between agent vocabularies while preserving meaning.
    
    Handles:
    - Domain-specific terminology mapping
    - Context preservation
    - Query translation
    - Cross-agent vocabulary alignment
    """
    
    # Vocabulary mappings between agents
    VOCABULARY_MAPS: Dict[str, Dict[str, str]] = {
        "supervisor": {
            "order": "order",
            "shipment": "order",
            "transaction": "order",
            "quantity": "quantity",
            "amount": "quantity",
            "price": "price",
            "cost": "price",
        },
        "farm_agent": {
            "order": "order",
            "shipment": "shipment",
            "delivery": "shipment",
            "quantity": "quantity",
            "lbs": "quantity",
            "price": "price",
            "rate": "price",
        },
        "shipper": {
            "order": "shipment",
            "transaction": "shipment",
            "package": "shipment",
            "quantity": "weight",
            "lbs": "weight",
            "price": "cost",
            "rate": "cost",
        },
        "accountant": {
            "order": "transaction",
            "shipment": "transaction",
            "delivery": "transaction",
            "quantity": "units",
            "amount": "units",
            "price": "amount",
            "cost": "amount",
        },
    }
    
    # State mappings (logistics workflow states)
    STATE_SYNONYMS: Dict[str, List[str]] = {
        "RECEIVED_ORDER": ["order received", "order intake", "order acknowledged", "new order"],
        "HANDOVER_TO_SHIPPER": ["handover", "shipment ready", "ready to ship", "prepared"],
        "CUSTOMS_CLEARANCE": ["customs cleared", "customs validated", "documents cleared"],
        "PAYMENT_COMPLETE": ["payment confirmed", "payment verified", "paid", "payment captured"],
        "DELIVERED": ["delivered", "completed", "finalized", "closed"],
    }
    
    def __init__(self):
        self.shared_memory = get_shared_memory()
    
    def translate_query(
        self,
        query: str,
        from_agent: str,
        to_agent: Optional[str] = None,
    ) -> str:
        """
        Translate a query from one agent's vocabulary to another.
        
        Args:
            query: The query string
            from_agent: Source agent ID
            to_agent: Target agent ID (if None, uses canonical form)
            
        Returns:
            Translated query string
        """
        if to_agent is None:
            # Use canonical form (supervisor vocabulary)
            to_agent = "supervisor"
        
        if from_agent == to_agent:
            return query
        
        translated = query
        
        # Get vocabulary maps
        from_vocab = self.VOCABULARY_MAPS.get(from_agent, {})
        to_vocab = self.VOCABULARY_MAPS.get(to_agent, {})
        
        # Reverse lookup: find canonical term, then map to target
        for canonical, synonyms in from_vocab.items():
            for synonym in [canonical] + [s for s in synonyms if isinstance(s, str)]:
                if synonym.lower() in query.lower():
                    # Find target synonym
                    target_synonyms = to_vocab.get(canonical, [canonical])
                    if target_synonyms:
                        target = target_synonyms[0] if isinstance(target_synonyms, list) else target_synonyms
                        translated = translated.replace(synonym, target)
                        break
        
        logger.info(f"Semantic Translation: {from_agent} -> {to_agent}: '{query}' -> '{translated}'")
        return translated
    
    def translate_state(
        self,
        state: str,
        from_agent: str,
        to_agent: Optional[str] = None,
    ) -> str:
        """
        Translate a state value between agents.
        
        Args:
            state: State string (e.g., "RECEIVED_ORDER")
            from_agent: Source agent ID
            to_agent: Target agent ID
            
        Returns:
            Translated state string
        """
        # States are standardized, but we can add agent-specific interpretations
        if to_agent is None:
            return state
        
        # For now, states are canonical across agents
        # But we can add agent-specific state synonyms if needed
        return state
    
    def find_semantic_matches(
        self,
        query: str,
        agent_context: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """
        Find memory entries that semantically match a query.
        
        Args:
            query: Natural language query
            agent_context: Optional agent ID for context-aware matching
            
        Returns:
            List of matching MemoryEntry objects
        """
        # Extract semantic tags from query
        query_lower = query.lower()
        semantic_tags = []
        
        # Map query terms to semantic tags
        if "order" in query_lower or "transaction" in query_lower or "shipment" in query_lower:
            semantic_tags.append("order")
        
        if "state" in query_lower or "status" in query_lower:
            semantic_tags.append("state")
        
        if "inventory" in query_lower or "available" in query_lower or "stock" in query_lower:
            semantic_tags.append("inventory")
        
        if "price" in query_lower or "cost" in query_lower or "amount" in query_lower:
            semantic_tags.append("price")
        
        if "quantity" in query_lower or "amount" in query_lower or "lbs" in query_lower:
            semantic_tags.append("quantity")
        
        # Add logistics-specific tags
        for state, synonyms in self.STATE_SYNONYMS.items():
            if any(syn in query_lower for syn in synonyms):
                semantic_tags.append(state.lower())
                semantic_tags.append("logistics")
        
        if not semantic_tags:
            semantic_tags = ["order", "logistics"]  # Default tags
        
        # Query shared memory
        results = self.shared_memory.query(
            semantic_tags=semantic_tags,
            agent_id=agent_context,
            limit=20,
        )
        
        logger.info(f"Semantic Search: Found {len(results)} matches for query '{query}'")
        return results
    
    def translate_response(
        self,
        response: Any,
        from_agent: str,
        to_agent: str,
    ) -> Any:
        """
        Translate a response from one agent's vocabulary to another.
        
        Args:
            response: Response value (can be string, dict, etc.)
            from_agent: Source agent ID
            to_agent: Target agent ID
            
        Returns:
            Translated response
        """
        if isinstance(response, str):
            return self.translate_query(response, from_agent, to_agent)
        elif isinstance(response, dict):
            # Translate dictionary keys and values
            translated = {}
            for key, value in response.items():
                translated_key = self.translate_query(key, from_agent, to_agent)
                if isinstance(value, str):
                    translated_value = self.translate_query(value, from_agent, to_agent)
                else:
                    translated_value = value
                translated[translated_key] = translated_value
            return translated
        else:
            return response
    
    def get_canonical_term(self, term: str, agent_id: str) -> str:
        """
        Get the canonical term for an agent-specific term.
        
        Args:
            term: Agent-specific term
            agent_id: Agent ID
            
        Returns:
            Canonical term (using supervisor vocabulary)
        """
        vocab = self.VOCABULARY_MAPS.get(agent_id, {})
        # Find reverse mapping
        for canonical, synonyms in vocab.items():
            if term.lower() == canonical.lower():
                return canonical
            if isinstance(synonyms, list) and term.lower() in [s.lower() for s in synonyms]:
                return canonical
        return term


# Global singleton instance (declared after class definition to avoid forward reference)
_semantic_translator_instance: Optional["SemanticTranslator"] = None


def get_semantic_translator() -> SemanticTranslator:
    """Get the global semantic translator instance."""
    global _semantic_translator_instance
    if _semantic_translator_instance is None:
        _semantic_translator_instance = SemanticTranslator()
    return _semantic_translator_instance
