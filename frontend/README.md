# BenefitWise demo UI

This frontend is a light customization of LangChain's open-source Agent Chat
UI. It preserves the standard single-column conversation and native LangGraph
tool-call/result rendering, then adds a fictional employee demo sign-in, a
compact profile avatar, and a collapsible activity log of observable graph
events. The activity log never requests or displays private model reasoning.

References: [official Agent Chat UI documentation](https://docs.langchain.com/oss/python/langchain/ui)
and [langchain-ai/agent-chat-ui](https://github.com/langchain-ai/agent-chat-ui).
The retained and adapted source remains subject to the included
[`LICENSE.agent-chat-ui`](LICENSE.agent-chat-ui) MIT notice.

The sign-in is deliberately not production authentication. It selects one of
three fictional SQLite-backed profiles and supplies that employee ID to the
LangGraph server, where trusted context is resolved deterministically.

## Run locally

Start the Python LangGraph server from the repository root:

```powershell
.\.venv\Scripts\langgraph.exe dev
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The UI defaults to the local graph URL
`http://127.0.0.1:2024` and graph ID `benefitwise`; override them through the
documented `NEXT_PUBLIC_*` variables only when needed. No OpenAI or LangSmith
secret is accepted by the browser application.
