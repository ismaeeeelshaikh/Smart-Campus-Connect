from langchain_groq import ChatGroq
from app.config import settings

def test_groq():
    try:
        llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.1
        )
        response = llm.invoke("Hello, how are you?")
        print(f"✅ GROQ API working with {settings.groq_model}! Response: {response.content}")
    except Exception as e:
        print(f"❌ GROQ API error: {e}")

if __name__ == "__main__":
    test_groq()
