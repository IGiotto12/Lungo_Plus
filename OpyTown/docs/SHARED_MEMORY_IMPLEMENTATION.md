# Shared Memory / Semantic Translation Implementation Plan

## Overview

Add shared memory and semantic translation capabilities to the SLIM order fulfillment conversation workflow. This enables agents to:
- Share context and state transparently
- Translate between different agent vocabularies
- Maintain reliable, observable communication

## Visualization in Agentic UI

The shared memory is visualized in the workflow graph as:
- **Node Type**: Custom node with Database icon
- **Label**: "Shared Memory" / "Semantic Translation Bus"
- **Position**: Centrally located in the logistics group
- **Connections**: Bidirectional edges to all agents (Supervisor, Farm, Shipper, Accountant)
- **Edge Labels**: "Write/Read" to indicate bidirectional access

## Architecture

### Shared Memory Service

**Location**: `services/shared_memory.py`

**Responsibilities**:
- Store agent messages and state in a shared knowledge base
- Provide semantic translation between agent vocabularies
- Maintain conversation context across agents
- Enable querying of shared state

**Key Features**:
- Central knowledge base (can use Redis, in-memory dict, or database)
- Agent-specific views and semantic translation
- Context preservation across agent interactions
- Observable read/write operations

### Semantic Translation Layer

**Location**: `services/semantic_translator.py`

**Responsibilities**:
- Convert messages between different agent vocabularies
- Preserve semantic meaning during translation
- Handle domain-specific terminology (e.g., "order" vs "shipment" vs "transaction")

**Example**:
```
Colombia Farm: "We have 500 lbs available"
→ Stored in shared memory with semantic tags
→ Vietnam Farm queries: "What's Colombia's inventory?"
→ Semantic translator converts query and retrieves: "Colombia has 500 lbs"
```

## Integration Points

### 1. Update Logistics Agents

**Files to Modify**:
- `agents/logistics/farm/agent_executor.py`
- `agents/logistics/shipper/agent_executor.py`
- `agents/logistics/accountant/agent_executor.py`
- `agents/supervisors/logistics/graph/tools.py`

**Changes**:
- Write order state updates to shared memory
- Read shared memory before processing orders
- Use semantic translation for cross-agent queries

### 2. Shared Memory API

**Endpoints** (can be added to logistics supervisor):
- `POST /shared-memory/write` - Write state to shared memory
- `GET /shared-memory/read` - Read state from shared memory
- `POST /shared-memory/translate` - Semantic translation query

**Example Usage**:
```python
# Write to shared memory
await shared_memory.write(
    agent_id="farm_agent",
    key="order_state",
    value={"order_id": "123", "state": "HANDOVER_TO_SHIPPER"},
    semantic_tags=["order", "shipping", "logistics"]
)

# Read with semantic translation
result = await shared_memory.read(
    query="What is the current order status?",
    agent_context="shipper_agent"
)
# Returns translated result in shipper's vocabulary
```

## Workflow Integration

### Current Flow (without shared memory):
```
Supervisor → SLIM Transport → Farm Agent
Farm Agent → SLIM Transport → Shipper Agent
Shipper Agent → SLIM Transport → Accountant Agent
```

### Enhanced Flow (with shared memory):
```
Supervisor → Write to Shared Memory → SLIM Transport → Farm Agent
Farm Agent → Read from Shared Memory → Process → Write to Shared Memory
Shipper Agent → Read from Shared Memory → Process → Write to Shared Memory
Accountant Agent → Read from Shared Memory → Process → Write to Shared Memory
```

## Benefits

1. **Transparency**: All agents can see shared state
2. **Reliability**: State is persisted and queryable
3. **Semantic Interoperability**: Agents with different vocabularies can communicate
4. **Observability**: Shared memory operations are visible in the workflow graph
5. **Debugging**: Easier to trace state changes across agents

## Implementation Steps

1. **Phase 1: Shared Memory Service**
   - Create `services/shared_memory.py`
   - Implement basic read/write operations
   - Add semantic tagging

2. **Phase 2: Semantic Translation**
   - Create `services/semantic_translator.py`
   - Implement vocabulary mapping
   - Add context preservation

3. **Phase 3: Agent Integration**
   - Update logistics agents to use shared memory
   - Add read/write operations at key workflow points
   - Integrate semantic translation

4. **Phase 4: Visualization**
   - ✅ Already added to frontend graph visualization
   - Add real-time updates showing memory operations
   - Highlight active read/write operations

## Example Use Cases

### Use Case 1: Order State Sharing
```
Supervisor creates order → Writes to shared memory
Farm Agent reads order → Processes → Writes "HANDOVER_TO_SHIPPER" state
Shipper Agent reads state → Processes → Writes "CUSTOMS_CLEARANCE" state
Accountant Agent reads state → Processes → Writes "PAYMENT_COMPLETE" state
```

### Use Case 2: Cross-Agent Queries
```
Shipper Agent: "What's the order quantity?"
→ Queries shared memory with semantic translation
→ Returns: "Order 123 has quantity 5000 lbs"
```

### Use Case 3: Context Preservation
```
Agent A: "Order 123 is ready for shipping"
→ Stored in shared memory with context
Agent B: "What orders are ready?"
→ Semantic translator matches "ready for shipping" → Returns order 123
```

## Next Steps

1. Implement the shared memory service backend
2. Add semantic translation layer
3. Integrate with existing logistics agents
4. Test with order fulfillment workflow
5. Monitor and visualize in the agentic UI
