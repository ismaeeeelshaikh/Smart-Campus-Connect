import os
import pickle
import logging
from typing import List, Dict
import shutil

# LangChain imports
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain.schema import Document
from langchain.storage import InMemoryStore
from langchain.retrievers import ParentDocumentRetriever

# Web Search
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        logger.info("Initializing RAG Service with Smart Query Logic...")

        self.embeddings = SentenceTransformerEmbeddings(model_name="BAAI/bge-base-en-v1.5")

        # Temperature 0.3: Keep it low to prevent hallucinating names
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
        )

        # Max results 5 ensures we see the specific faculty page snippet
        self.search_wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)
        self.search_tool = DuckDuckGoSearchRun(api_wrapper=self.search_wrapper)

        self.retriever = None
        self.session_conversations: Dict[int, Dict[int, List[Dict]]] = {}

        self._load_or_create_retriever()
        self._load_conversation_memory()
        logger.info("✅ RAG Service initialized successfully")

    def _load_conversation_memory(self):
        memory_file = "conversation_memory.pkl"
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'rb') as f:
                    self.session_conversations = pickle.load(f)
            except Exception:
                self.session_conversations = {}

    def _save_conversation_memory(self):
        try:
            with open("conversation_memory.pkl", 'wb') as f:
                pickle.dump(self.session_conversations, f)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def _load_or_create_retriever(self):
        chroma_dir = "./chroma_db_final"
        if os.path.exists(chroma_dir):
            shutil.rmtree(chroma_dir) 
        self._create_retriever_and_vectorstore()

    def _create_retriever_and_vectorstore(self):
        data_dir = "college_data"
        if not os.path.exists(data_dir) or not os.listdir(data_dir):
             return

        try:
            loader = DirectoryLoader(
                data_dir,
                glob="**/*.txt",
                loader_cls=lambda file_path: TextLoader(file_path, encoding='utf-8'),
            )
            all_docs = loader.load()

            parent_splitter = RecursiveCharacterTextSplitter(separators=["\n=== "], chunk_size=2000, chunk_overlap=200)
            child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100)

            vectorstore = Chroma(
                collection_name="split_by_section",
                embedding_function=self.embeddings,
                persist_directory="./chroma_db_final"
            )
            store = InMemoryStore()

            self.retriever = ParentDocumentRetriever(
                vectorstore=vectorstore,
                docstore=store,
                child_splitter=child_splitter,
                parent_splitter=parent_splitter,
            )
            self.retriever.add_documents(all_docs, ids=None)

        except Exception as e:
            logger.error(f"❌ Error creating retriever: {e}")

    def _get_session_history(self, user_id: int, session_id: int) -> List[Dict]:
        if user_id not in self.session_conversations:
            return []
        if session_id not in self.session_conversations[user_id]:
            return []
        return self.session_conversations[user_id][session_id]

    def _store_session_conversation(self, user_id: int, session_id: int, question: str, answer: str):
        if user_id not in self.session_conversations: self.session_conversations[user_id] = {}
        if session_id not in self.session_conversations[user_id]: self.session_conversations[user_id][session_id] = []
        
        self.session_conversations[user_id][session_id].append({'question': question, 'answer': answer})
        self._save_conversation_memory()

    # --- NEW: SMART SEARCH LOGIC ---
    def _perform_web_search(self, question):
        try:
            q_lower = question.lower()
            
            # Logic 1: If asking for HOD, force specific Department search
            if "hod" in q_lower or "head of department" in q_lower:
                # Try to guess the department
                dept = ""
                if "civil" in q_lower: dept = "Civil Engineering"
                elif "computer" in q_lower: dept = "Computer Engineering"
                elif "it" in q_lower or "information" in q_lower: dept = "Information Technology"
                elif "mech" in q_lower: dept = "Mechanical Engineering"
                elif "aiml" in q_lower: dept = "AIML"
                elif "ds" in q_lower or "data" in q_lower: dept = "Data Science"
                
                # Search specifically for the title to find the "Faculty" page
                search_query = f'"Head of Department" {dept} faculty list site:apsit.edu.in'
            
            # Logic 2: If asking for Principal
            elif "principal" in q_lower:
                search_query = f'"Principal" name site:apsit.edu.in'

            # Logic 3: General Fallback
            else:
                search_query = f"{question} site:apsit.edu.in"

            logger.info(f"🔎 Executing Smart Search: {search_query}")
            return self.search_tool.run(search_query)

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ""

    def get_response_for_session(self, question: str, user_id: int, session_id: int) -> str:
        
        # 1. Greeting Logic
        history_list = self._get_session_history(user_id, session_id)
        if len(history_list) > 0:
            style_instruction = "Strictly DO NOT greet. Answer directly."
            history_text = "\n".join([f"User: {msg['question']}\nYou: {msg['answer']}" for msg in history_list[-6:]])
        else:
            style_instruction = "Start with a short, friendly greeting."
            history_text = "No previous conversation."

        # 2. Retrieve Documents (Internal DB)
        try:
            db_docs = self.retriever.get_relevant_documents(question)
            db_context = "\n".join([doc.page_content for doc in db_docs]) if db_docs else ""
        except Exception:
            db_context = ""

        # 3. Web Search
        web_context = ""
        if len(question.split()) > 1: 
            web_context = self._perform_web_search(question)
        
        # 4. Construct Prompt
        knowledge_base = f"""
        [SOURCE 1: LIVE WEB SEARCH (HIGHEST PRIORITY)]:
        {web_context}

        [SOURCE 2: INTERNAL DATABASE (SECONDARY)]:
        {db_context}
        """

        final_prompt = f"""You are a smart senior student at APSIT.

        **CRITICAL INSTRUCTIONS:**
        1. **Conflict Rule:** If Source 1 and Source 2 disagree on a person's name/role, **Source 1 (Web) is the TRUTH**.
        2. **HOD Check:** When checking for "HOD" or "Head of Department", look for the exact name listed next to that title in Source 1. Ignore "Assistant Professor" names unless they are explicitly called HOD.
        3. **Correction:** If the user corrects you (e.g., "Mugdha is HOD"), trust the user and double-check Source 1.
        4. **Persona:** {style_instruction} Be helpful and confident.

        **CONTEXT:**
        History: {history_text}
        User Question: {question}

        **INFORMATION:**
        {knowledge_base}

        **ANSWER:**"""

        try:
            response = self.llm.invoke(final_prompt)
            self._store_session_conversation(user_id, session_id, question, response.content)
            return response.content

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: {e}")
            return "I'm hitting a search limit. Give me a second and ask again."

    def clear_session_memory(self, user_id: int, session_id: int):
        if user_id in self.session_conversations and session_id in self.session_conversations[user_id]:
            del self.session_conversations[user_id][session_id]
            self._save_conversation_memory()

rag_service = RAGService()