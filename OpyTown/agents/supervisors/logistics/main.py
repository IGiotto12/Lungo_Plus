# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi.responses import StreamingResponse
from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from ioa_observe.sdk.tracing import session_start

from agents.supervisors.logistics.graph.graph import LogisticGraph
from agents.supervisors.logistics.graph import shared
from agents.logistics.shipper.card import AGENT_CARD  # assuming similar structure
from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT
from config.logging_config import setup_logging
from pathlib import Path
from services.shared_memory import get_shared_memory
from services.semantic_translator import get_semantic_translator
from typing import Optional, List, Dict, Any

setup_logging()
logger = logging.getLogger("lungo.logistics.supervisor.main")

load_dotenv()

# Initialize the shared agntcy factory with tracing enabled
shared.set_factory(AgntcyFactory("lungo.logistics_supervisor", enable_tracing=True))

app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

logistic_graph = LogisticGraph()

class PromptRequest(BaseModel):
  prompt: str

@app.post("/agent/prompt")
async def handle_prompt(request: PromptRequest):
  try:
    with session_start() as session_id:
      timeout_val = int(os.getenv("LOGISTIC_TIMEOUT", "200"))
      result = await asyncio.wait_for(
        logistic_graph.serve(request.prompt),
        timeout=timeout_val
      )
      logger.info(f"Final result from LangGraph: {result}")
      return {"response": result, "session_id": session_id["executionID"]}
  except asyncio.TimeoutError:
    logger.error("Request timed out after %s seconds", timeout_val)
    raise HTTPException(status_code=504, detail=f"Request timed out after {timeout_val} seconds")
  except ValueError as ve:
    raise HTTPException(status_code=400, detail=str(ve))
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")

@app.get("/health")
async def health_check():
  return {"status": "ok"}

@app.get("/v1/health")
async def connectivity_health():
  """
  Deep liveness: validates transport + client creation.
  """
  try:
    factory = shared.get_factory() if hasattr(shared, "get_factory") else shared.factory  # fallback
    transport = factory.create_transport(
      DEFAULT_MESSAGE_TRANSPORT,
      endpoint=TRANSPORT_SERVER_ENDPOINT,
      name="default/default/liveness_probe",
    )
    _ = await asyncio.wait_for(
      factory.create_client(
        "A2A",
        agent_topic=A2AProtocol.create_agent_topic(AGENT_CARD),
        transport=transport,
      ),
      timeout=30,
    )
    return {"status": "alive"}
  except asyncio.TimeoutError:
    raise HTTPException(status_code=500, detail="Timeout creating A2A client")
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/transport/config")
async def get_config():
  return {
    "transport": DEFAULT_MESSAGE_TRANSPORT.upper()
  }


@app.post("/agent/prompt/stream")
async def handle_stream_prompt(request: PromptRequest):
    """
    Streams real-time order processing events as they occur in the logistics workflow.

    Flow:
    1. Extracts order parameters (farm, quantity, price) from user prompt using LLM
    2. Initiates order with logistics agents (farm, shipper, accountant)
    3. Streams each status update as agents process the order:
       - RECEIVED_ORDER: Supervisor sends order to farm
       - HANDOVER_TO_SHIPPER: Farm hands off to shipper
       - CUSTOMS_CLEARANCE: Shipper clears customs
       - PAYMENT_COMPLETE: Accountant confirms payment
       - DELIVERED: Shipper completes delivery
    4. Sends final formatted summary message

    Args:
        request (PromptRequest): User's order request (e.g., "Order 5000 lbs at $3.52 from Tatooine")

    Returns:
        StreamingResponse: NDJSON stream where each line is:
        {"response": {"order_id": "...", "sender": "...", "state": "...", ...}} for events
        {"response": "Order X from Y for Z units at $W has been successfully delivered."} for summary

    Raises:
        HTTPException: 400 for invalid input, 500 for server-side errors.
    """
    try:
        with session_start() as session_id:  # Start a new tracing session for observability

          async def stream_generator():
              try:
                  async for chunk in logistic_graph.streaming_serve(request.prompt):
                      yield json.dumps({"response": chunk, "session_id": session_id["executionID"]}) + "\n"
              except Exception as e:
                  logger.error(f"Error in stream: {e}")
                  yield json.dumps({"response": f"Error: {str(e)}"}) + "\n"

          return StreamingResponse(
              stream_generator(),
              media_type="application/x-ndjson",
              headers={
                  "Cache-Control": "no-cache",
                  "Connection": "keep-alive",
              }
          )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")

@app.get("/suggested-prompts")
async def get_prompts(pattern: str = "default"):
  """
  Fetch suggested prompts based on the specified pattern.

  Parameters:
      pattern (str): The type of prompts to fetch.
                     Use "default" for all prompts or "streaming" for streaming-specific prompts.

  Returns:
      dict: A dictionary containing lists of prompts for "buyer" and "purchaser".

  Raises:
      HTTPException:
          - 500 if the JSON file is invalid or an unexpected error occurs.
  """
  try:
    prompts_path = Path(__file__).resolve().parent / "suggested_prompts.json"
    raw = prompts_path.read_text(encoding="utf-8")
    data = json.loads(raw)

    return {"logistics": data.get("logistics_prompts", [])}

  except Exception as e:
    logger.error(f"Unexpected error while reading prompts: {str(e)}")
    raise HTTPException(status_code=500, detail="An unexpected error occurred while reading prompts.")


# --- Shared Memory API Endpoints ---

class WriteMemoryRequest(BaseModel):
    key: str
    value: Any
    agent_id: str
    semantic_tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class QueryMemoryRequest(BaseModel):
    semantic_tags: List[str]
    agent_id: Optional[str] = None
    limit: int = 10


@app.post("/shared-memory/write")
async def write_to_shared_memory(request: WriteMemoryRequest):
    """
    Write an entry to shared memory.
    
    Args:
        request: WriteMemoryRequest with key, value, agent_id, and optional tags/metadata
        
    Returns:
        dict: Success message and entry details
    """
    try:
        shared_memory = get_shared_memory()
        entry = shared_memory.write(
            key=request.key,
            value=request.value,
            agent_id=request.agent_id,
            semantic_tags=request.semantic_tags,
            metadata=request.metadata,
        )
        return {
            "status": "success",
            "entry": entry.dict(),
        }
    except Exception as e:
        logger.error(f"Error writing to shared memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write to shared memory: {str(e)}")


@app.get("/shared-memory/read/{key}")
async def read_from_shared_memory(
    key: str,
    agent_id: Optional[str] = None,
    latest_only: bool = True,
):
    """
    Read an entry from shared memory.
    
    Args:
        key: Memory key to read
        agent_id: Optional agent ID filter
        latest_only: If True, return only the latest entry
        
    Returns:
        dict: The value(s) stored at the key
    """
    try:
        shared_memory = get_shared_memory()
        value = shared_memory.read(
            key=key,
            agent_id=agent_id,
            latest_only=latest_only,
        )
        if value is None:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found in shared memory")
        return {
            "key": key,
            "value": value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading from shared memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read from shared memory: {str(e)}")


@app.post("/shared-memory/query")
async def query_shared_memory(request: QueryMemoryRequest):
    """
    Query shared memory by semantic tags.
    
    Args:
        request: QueryMemoryRequest with semantic_tags, optional agent_id, and limit
        
    Returns:
        dict: List of matching memory entries
    """
    try:
        shared_memory = get_shared_memory()
        results = shared_memory.query(
            semantic_tags=request.semantic_tags,
            agent_id=request.agent_id,
            limit=request.limit,
        )
        return {
            "count": len(results),
            "entries": [entry.dict() for entry in results],
        }
    except Exception as e:
        logger.error(f"Error querying shared memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to query shared memory: {str(e)}")


@app.get("/shared-memory/order/{order_id}")
async def get_order_state(order_id: str):
    """
    Get the current state of an order from shared memory.
    
    Args:
        order_id: The order ID
        
    Returns:
        dict: Order state information
    """
    try:
        shared_memory = get_shared_memory()
        state = shared_memory.get_order_state(order_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found in shared memory")
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order state: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get order state: {str(e)}")


@app.get("/shared-memory/orders")
async def get_all_orders():
    """
    Get all order states from shared memory.
    
    Returns:
        dict: List of all order states
    """
    try:
        shared_memory = get_shared_memory()
        orders = shared_memory.get_all_orders()
        return {
            "count": len(orders),
            "orders": orders,
        }
    except Exception as e:
        logger.error(f"Error getting all orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get all orders: {str(e)}")


@app.post("/shared-memory/semantic-search")
async def semantic_search(query: str, agent_context: Optional[str] = None):
    """
    Perform semantic search on shared memory.
    
    Args:
        query: Natural language query
        agent_context: Optional agent ID for context-aware matching
        
    Returns:
        dict: List of matching memory entries
    """
    try:
        translator = get_semantic_translator()
        results = translator.find_semantic_matches(
            query=query,
            agent_context=agent_context,
        )
        return {
            "query": query,
            "count": len(results),
            "entries": [entry.dict() for entry in results],
        }
    except Exception as e:
        logger.error(f"Error performing semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to perform semantic search: {str(e)}")

if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=9090, reload=True)
