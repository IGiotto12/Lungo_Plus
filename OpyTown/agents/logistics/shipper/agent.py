# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging

from langchain_core.messages import AIMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, END

from ioa_observe.sdk.decorators import agent, graph

from common.logistics_states import (
    LogisticsStatus,
    extract_status,
    build_transition_message,
    ensure_order_id,
)
from services.shared_memory import get_shared_memory
from services.semantic_translator import get_semantic_translator

logger = logging.getLogger("lungo.shipper_agent.agent")

# --- 1. Define Node Names as Constants ---
class NodeStates:
    SHIPPER = "shipper"


# --- 2. Define the Graph State ---
class GraphState(MessagesState):
    """
    Represents the state of our graph, passed between nodes.
    """
    pass


# --- 3. Implement the Shipper Agent Class ---
@agent(name="shipper_agent")
class ShipperAgent:
    def __init__(self):
        """
        Initializes the ShipperAgent with a single node LangGraph workflow.
        Handles two specific inputs:
        - HANDOVER_TO_SHIPPER -> CUSTOMS_CLEARANCE
        - PAYMENT_COMPLETE -> DELIVERED
        """
        self.shared_memory = get_shared_memory()
        self.semantic_translator = get_semantic_translator()
        self.app = self._build_graph()

    # --- Node Definition ---

    def _shipper_node(self, state: GraphState) -> dict:
        messages = state["messages"]
        if isinstance(messages, list) and messages:
            last = messages[-1]
            text = getattr(last, "content", str(last))
        else:
            text = str(messages)
        raw = text.strip()
        status = extract_status(raw)

        order_id = ensure_order_id(raw)

        if status is LogisticsStatus.HANDOVER_TO_SHIPPER:
            next_status = LogisticsStatus.CUSTOMS_CLEARANCE
            
            # Read previous state from shared memory
            prev_state = self.shared_memory.get_order_state(order_id)
            if prev_state:
                logger.info(f"Shipper read order state from shared memory: {prev_state}")
            
            # Write to shared memory
            self.shared_memory.update_order_state(
                order_id=order_id,
                state=next_status.value,
                agent_id="shipper_agent",
                metadata={
                    "sender": "Shipper",
                    "receiver": "Accountant",
                    "details": "Customs docs validated and cleared",
                }
            )
            
            # Store message in shared memory
            self.shared_memory.write(
                key=f"message_{order_id}",
                value={
                    "order_id": order_id,
                    "sender": "Shipper",
                    "receiver": "Accountant",
                    "state": next_status.value,
                    "message": raw,
                },
                agent_id="shipper_agent",
                semantic_tags=["order", "customs", "clearance", "logistics"],
            )
            
            msg = build_transition_message(
                order_id=order_id,
                sender="Shipper",
                receiver="Accountant",
                to_state=next_status.value,
                details="Customs docs validated and cleared",
            )
            return {"messages": [AIMessage(msg)]}

        if status is LogisticsStatus.PAYMENT_COMPLETE:
            next_status = LogisticsStatus.DELIVERED
            
            # Write to shared memory
            self.shared_memory.update_order_state(
                order_id=order_id,
                state=next_status.value,
                agent_id="shipper_agent",
                metadata={
                    "sender": "Shipper",
                    "receiver": "Supervisor",
                    "details": "Final handoff completed",
                }
            )
            
            # Store message in shared memory
            self.shared_memory.write(
                key=f"message_{order_id}",
                value={
                    "order_id": order_id,
                    "sender": "Shipper",
                    "receiver": "Supervisor",
                    "state": next_status.value,
                    "message": raw,
                },
                agent_id="shipper_agent",
                semantic_tags=["order", "delivered", "completed", "logistics"],
            )
            
            msg = build_transition_message(
                order_id=order_id,
                sender="Shipper",
                receiver="Supervisor",
                to_state=next_status.value,
                details="Final handoff completed",
            )
            return {"messages": [AIMessage(msg)]}

        return {"messages": [AIMessage("Shipper remains IDLE. No further action required.")]}

    # --- Graph Building Method ---

    @graph(name="shipper_graph")
    def _build_graph(self):
        """
        Builds and compiles the LangGraph workflow with single node.
        """
        workflow = StateGraph(GraphState)

        # Add single node
        workflow.add_node(NodeStates.SHIPPER, self._shipper_node)

        # Set the entry point
        workflow.set_entry_point(NodeStates.SHIPPER)

        # Add edge to END
        workflow.add_edge(NodeStates.SHIPPER, END)

        return workflow.compile()

    # --- Public Methods for Interaction ---

    async def ainvoke(self, user_message: str) -> str:
        """
        Invokes the graph with a user message.

        Args:
            user_message (str): The current message from the user.

        Returns:
            str: The final response from the shipper agent.
        """
        inputs = {"messages": [user_message]}
        result = await self.app.ainvoke(inputs)

        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("No messages found in the graph response.")

        # Find the last AIMessage with non-empty content
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content.strip():
                logger.debug(f"Valid AIMessage found: {message.content.strip()}")
                return message.content.strip()

        # If no valid AIMessage found, return the last message as a fallback
        return messages[-1].content.strip()