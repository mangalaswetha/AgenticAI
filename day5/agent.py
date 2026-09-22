"""
LangChain agent powered by Google Gemini.

The LLM decides which tools to call and in what order.
We do NOT hard-code a fixed tool sequence.
"""

from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from tools import ALL_TOOLS

SYSTEM_PROMPT = """You are a helpful academic assistant for student records.

You have tools to:
- look up student name and department
- look up subject marks
- calculate totals and averages
- read university passing rules

Rules:
- Always use tools to get facts from the database. Do not invent marks or names.
- Student IDs look like 22CS045.
- For total/average: first get marks, then use the calculator tool.
- For pass eligibility: get marks, get passing rules, use calculator if needed,
  then decide if every subject is >= 35 and overall average is >= 40.
- Explain your final answer clearly in plain language.
"""


def build_agent(model_name: str | None = None):
    """Create a ReAct-style tool-calling agent with Gemini."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set GOOGLE_API_KEY (or GEMINI_API_KEY) in your environment or .env file."
        )

    model = ChatGoogleGenerativeAI(
        model=model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=api_key,
        temperature=0,
    )

    agent = create_react_agent(
        model,
        ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
    )
    return agent


def ask(agent, question: str) -> str:
    """Run one user question through the agent and return the final text answer."""
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 20},
    )
    messages = result.get("messages", [])
    if not messages:
        return "No response from agent."
    last = messages[-1]
    content = getattr(last, "content", None) or str(last)
    if isinstance(content, list):
        # Gemini sometimes returns list content blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)
