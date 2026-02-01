# Shared Memory Algorithms

This document describes the popular algorithms implemented in the Shared Memory service to showcase algorithm design capabilities.

## Algorithms Implemented

### 1. LRU (Least Recently Used) Cache

**Algorithm Type**: Cache Replacement Policy  
**Complexity**: O(1) for get/put operations  
**Reference**: [Wikipedia - LRU Cache](https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU))

**Purpose**: Efficiently manage memory by automatically evicting least recently used entries when capacity is exceeded.

**Implementation**:
- Uses Python's `OrderedDict` for O(1) operations
- Moves accessed items to end (most recently used)
- Evicts from front (least recently used) when capacity reached

**Usage in Shared Memory**:
- Caches frequently accessed memory entries
- Prevents unbounded memory growth
- Provides fast O(1) lookup for recent entries

### 2. Inverted Index

**Algorithm Type**: Information Retrieval Data Structure  
**Complexity**: O(1) lookup per tag, O(t) for t tags  
**Reference**: [Wikipedia - Inverted Index](https://en.wikipedia.org/wiki/Inverted_index)

**Purpose**: Enable fast semantic tag-based search by mapping tags to entries containing them.

**Implementation**:
- Maps: `tag → set of entry_ids`
- Supports AND (intersection) and OR (union) operations
- Enables fast retrieval of all entries matching query tags

**Usage in Shared Memory**:
- Powers semantic tag-based queries
- Enables efficient multi-tag search
- Reduces search time from O(n) to O(t) where t = number of tags

### 3. TF-IDF (Term Frequency-Inverse Document Frequency)

**Algorithm Type**: Information Retrieval Scoring Algorithm  
**Complexity**: O(t) for t terms per document  
**Reference**: [Wikipedia - TF-IDF](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)

**Purpose**: Rank document relevance by calculating how important terms are to documents in a collection.

**Formula**:
```
TF-IDF(t, d) = TF(t, d) × IDF(t)

Where:
- TF(t, d) = frequency of term t in document d / total terms in d
- IDF(t) = log(total_documents / documents_containing_t)
```

**Implementation**:
- Tracks term frequencies per document
- Calculates inverse document frequency
- Scores documents based on query term relevance

**Usage in Shared Memory**:
- Ranks semantic search results by relevance
- Prioritizes entries with more matching semantic tags
- Provides intelligent result ordering beyond simple timestamp sorting

## Algorithm Integration

The three algorithms work together:

1. **LRU Cache**: Provides fast access to frequently used entries
2. **Inverted Index**: Enables fast semantic tag lookup
3. **TF-IDF**: Ranks results by semantic relevance

### Example Query Flow

```
Query: ["order", "logistics", "payment"]

1. Inverted Index: O(1) lookup → finds all entries with these tags
2. TF-IDF Scoring: O(t) per entry → ranks by semantic relevance
3. LRU Cache: O(1) → provides fast access to top results
```

## Performance Characteristics

| Operation | Without Algorithms | With Algorithms | Improvement |
|-----------|-------------------|-----------------|-------------|
| Write | O(1) | O(1) + O(t) | Same (t = tags) |
| Read (by key) | O(1) | O(1) | Same |
| Query (by tags) | O(n) | O(t + k log k) | O(n) → O(t) |
| Memory Eviction | Manual | Automatic (LRU) | Automatic |

Where:
- n = total number of entries
- t = number of query tags
- k = number of matching entries

## Benefits

1. **Scalability**: Algorithms handle large datasets efficiently
2. **Relevance**: TF-IDF provides intelligent ranking
3. **Performance**: Inverted Index enables fast search
4. **Memory Management**: LRU Cache prevents unbounded growth
5. **Industry Standard**: Uses well-known, proven algorithms

## References

- LRU Cache: Used in Redis, Memcached, CPU caches
- Inverted Index: Foundation of search engines (Google, Elasticsearch)
- TF-IDF: Standard in information retrieval, used in search engines and NLP
