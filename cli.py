import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "dataagent" / ".env")

# after dotenv, so USE_LLM and the key exist before the client is built
import dataagent.tools
from dataagent.registry import registry
from dataagent.llm import MockLLM
from dataagent.llm_openai import OpenAICompatLLM
from dataagent.warehouse import EmbeddedWarehouse
from dataagent.agent import Agent

llm = OpenAICompatLLM() if os.getenv("USE_LLM") else MockLLM()
agent = Agent(llm, registry, EmbeddedWarehouse())

async def main():
    # one loop for the whole prompt. asyncio.run per question closes the loop
    # and the OpenAI client's HTTP pool dies on the next line.
    print("data agent ready. type a question, or 'quit' to exit.")
    while True:
        try:
            message = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if message.strip().lower() in ("quit", "exit"):
            break
        if not message.strip():
            continue
        response = await agent.chat(message)
        print(response.answer)
        print(f"[turns: {response.turns}, tools: {response.tools_used}]")
        if response.sql:
            print(f"[sql: {response.sql}]")
        if response.tables_used:
            print(f"[tables: {response.tables_used}]")

if __name__ == "__main__":
    asyncio.run(main())
