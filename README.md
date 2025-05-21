how to run this

to run the service

```
git clone https://github.com/getzep/graphiti.git
cd graphiti
uv sync
cd mcp_server
OPENAI_BASE_URL=http://localhost:5000 docker compose up
```

now

```
git clone https://github.com/abab-dev/test-graphiti-mcp-server.git
cd test-graphiti-mcp-server
uv run server.py
uv run mcp_sse_test.py
```

insertion works directly with gemini embedder and client
but calls to mcp server does not work
what might be problem
