## Domain-Specific LLM-Based Agentic Chatbot

A multi-agent LLM-powered chatbot system designed to handle domain-specific user requests through intelligent dialogue, personalization, and external system integration. It supports both text and multimodal inputs, enabling real-time, actionable conversations. 

### 🔧 Features
- #### Multi-Agent Architecture (LangGraph)

  - Modular agents for service application, order history summarization, web search, and multimodal interaction.

  -  Message routing and session tracking via State and Edge in LangGraph.

- #### MCP-based Executable Agent

  - Extracts structured JSON from user utterances (e.g., product type, quantity, date).

  - Sends structured requests via FastAPI to backend server for action execution.

- #### Multimodal Image Search Agent

  - Uses GPT-4o vision capabilities to extract intent keywords from user-uploaded images.

  - Combines extracted interest with user location (via Google Maps API) to recommend relevant services.

<br> 

### 📁 Tech Stack
| Domain           | Tools & Frameworks                                    |
| ---------------- | ----------------------------------------------------- |
| Backend / API    | Python, FastAPI, PostgreSQL, AWS RDS                  |
| Frontend         | JavaScript, React, Chainlit, Tailwind CSS             |
| LLM & Agentic AI | GPT-4o, LangGraph, OpenAI Function Calling, JSON Mode |
| Retrieval & RAG  | PGVector, BGE-M3, ChromaDB                            |
| Infra / DevOps   | Docker, GitLab CI/CD                                  |
| Multimodal       | GPT-4o Vision, Google Maps API                        |
| Embeddings       | Multilingual-GTE, Sentence Transformers               |
<br> 

### 📌 Project Highlights
- 🔍 Enhanced RAG with domain-specific retriever fine-tuning

- 🧠 Persona-aware response generation using soft prompting

- 🧭 Multi-agent orchestration using LangGraph for task-specific flows

- 🖼️ GPT-4o multimodal integration for image-based intent resolution

- 💬 Embedded as a module inside a real-world application
<br>

### 📂 Dataset Sources
- [Korean Proptech Retrieval Dataset](https://huggingface.co/datasets/crjoya/korean-proptech-retrieval)

- [Structured Persona Dataset](https://huggingface.co/datasets/crjoya/structured_personas_dataset)

- [Fine-tuned BGE-M3 Model](https://huggingface.co/crjoya/bge-m3-proptech-retrieval)
