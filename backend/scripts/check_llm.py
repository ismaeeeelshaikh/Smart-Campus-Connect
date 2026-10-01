"""Check that the configured LLM server answers (Groq now, the college DGX server later).

    python -m scripts.check_llm
"""
from app.config import settings
from app.services.rag import create_chat_model


def main():
    print(f"LLM: {settings.llm_model} at {settings.llm_base_url}")
    try:
        llm = create_chat_model(temperature=0, max_retries=0, timeout=60)
        response = llm.invoke("Reply with one short sentence: what is APSIT in Thane?")
        print(f"OK: the LLM answered: {response.content.strip()}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
