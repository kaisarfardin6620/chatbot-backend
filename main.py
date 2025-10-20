import uuid
import time
import random
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List

from agent import get_agent_response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if session_id not in self.session_states:
            self.session_states[session_id] = self.create_initial_state(session_id)
        print(f"Client connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        print(f"Client disconnected: {session_id}")

    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    def get_state(self, session_id: str) -> Dict:
        return self.session_states.get(session_id)

    def update_state(self, session_id: str, new_state: Dict):
        if session_id in self.session_states:
            self.session_states[session_id] = new_state

    def create_initial_state(self, session_id: str) -> Dict:
        welcome_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "text": "Hi! I’m your support assistant. What product can I help you with today?",
            "ts": int(time.time()),
        }
        return {
            "sessionId": session_id,
            "messages": [welcome_message],
            "context": {
                "product": None, "issue": None, "urgency": None,
                "ticketId": None, "state": "greeting"
            },
        }

manager = ConnectionManager()

@app.post("/api/chat/session")
async def create_session():
    session_id = str(uuid.uuid4())
    return {"sessionId": session_id}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    initial_state = manager.get_state(session_id)
    await manager.send_json(session_id, {"type": "history", "data": initial_state})

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message")
            start_time = time.time()

            await manager.send_json(session_id, {"type": "status", "message": "Assistant is thinking..."})

            current_state = manager.get_state(session_id)
            
            chat_history_for_agent = [
                {"role": msg["role"], "content": msg["text"]}
                for msg in current_state["messages"]
            ]

            try:
                ai_reply = get_agent_response(
                    chat_history=chat_history_for_agent,
                    user_input=user_message,
                    context=current_state["context"]
                )
                latency_ms = int((time.time() - start_time) * 1000)

                new_context = current_state["context"].copy()
                
                if "creating a ticket for" in ai_reply.lower() and "submit now?" in ai_reply.lower():
                    new_context["state"] = "confirming"
                
                elif "ticket #" in ai_reply.lower() and "[TICKET_ID]" in ai_reply:
                    ticket_id = f"T-{random.randint(1000, 9999)}"
                    ai_reply = ai_reply.replace("[TICKET_ID]", ticket_id)
                    new_context["state"] = "complete"
                    new_context["ticketId"] = ticket_id

                response_payload = {
                    "reply": ai_reply, "context": new_context, "latencyMs": latency_ms
                }
                
                current_state["context"] = new_context
                current_state["messages"].append({"id": str(uuid.uuid4()), "role": "user", "text": user_message, "ts": int(time.time())})
                current_state["messages"].append({"id": str(uuid.uuid4()), "role": "assistant", "text": ai_reply, "ts": int(time.time())})
                manager.update_state(session_id, current_state)

                await manager.send_json(session_id, {"type": "message", "data": response_payload})

            except Exception as e:
                error_payload = {
                    "error": f"Upstream LLM error: {str(e)}", "retryAfterMs": 1000
                }
                await manager.send_json(session_id, {"type": "error", "data": error_payload})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        print(f"An error occurred with session {session_id}: {e}")
        manager.disconnect(session_id)