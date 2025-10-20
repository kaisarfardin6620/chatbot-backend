# Chatbot Assistant Backend

This repository contains the backend implementation for the Chatbot Assistant Integration Challenge. It uses FastAPI for the web server, WebSockets for real-time communication, and LangChain with an OpenAI model for the AI logic.

## Architecture

The architecture is streamlined for the specific task of creating a support ticket:

1.  **FastAPI Server (`main.py`)**: Manages HTTP endpoints for session creation and WebSocket connections for live chat. It handles in-memory session state for each connected client.
2.  **AI Logic (`agent.py`)**: Contains a focused LangChain implementation. A precise system prompt guides an OpenAI LLM through the conversation flow, from greeting to ticket confirmation, without the need for external tools.
3.  **Connection Manager (`main.py`)**: A simple in-memory class to manage active WebSocket connections and their associated conversation states.

**Flow Diagram:**
`Client -> WebSocket -> FastAPI Server -> AI Logic (LangChain) -> OpenAI API -> FastAPI Server -> WebSocket -> Client`

## Setup and Running the Backend

### 1. Prerequisites
- Python 3.9+
- An OpenAI API key

### 2. Installation
Clone the repository and install the required dependencies:
```bash
git clone <your_repo_url>
cd chatbot-backend
pip install -r requirements.txt