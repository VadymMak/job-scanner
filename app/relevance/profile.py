PROFILE_TEXT = (
    "I build AI-powered integrations and full-stack web applications. "
    "On the AI side I work with LLMs, RAG pipelines, embeddings, vector databases, "
    "MCP servers, chat-bots, OpenAI and Anthropic APIs, LangChain, and prompt engineering. "
    "On the web side I use React, Next.js, Node.js, TypeScript, and occasionally Vue. "
    "For back-end services I reach for Python with FastAPI or Node with Express. "
    "I am comfortable with async Python, SQLAlchemy, PostgreSQL, and REST/GraphQL APIs."
)

# OR-запрос для ts_rank: попадает любая вакансия, упоминающая хотя бы один термин.
# Postgres требует одно слово на токен — составные термины разбиваем на части.
PROFILE_QUERY = (
    "ai | llm | rag | embedding | embeddings | vector | openai | anthropic | "
    "langchain | chatbot | mcp | prompt | nlp | react | nextjs | next | "
    "node | typescript | javascript | python | fastapi | fullstack | "
    "frontend | backend | vue"
)
