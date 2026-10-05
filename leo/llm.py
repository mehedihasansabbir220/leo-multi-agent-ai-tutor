import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()


def get_llm() -> LLM:
    return LLM(
        model=f"ollama/{os.getenv('OLLAMA_MODEL', 'llama3.2:3b')}",
        base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
        temperature=0.2,
    )
