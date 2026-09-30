# import logging
# import os
# import requests
# from typing import List, Dict, Any
# from datetime import datetime
# from dataclasses import dataclass
# from enum import Enum
# from bs4 import BeautifulSoup

# # --- IMPORTS ---
# from langchain.schema import Document

# try:
#     from langchain.memory import BaseMemory
# except ImportError:
#     from langchain.schema import BaseMemory

# try:
#     from langchain_core.language_models import BaseLanguageModel
# except ImportError:
#     from langchain.base_language import BaseLanguageModel

# # CHANGED: Using BufferWindowMemory for exact recall of recent facts
# from langchain.memory import ConversationBufferWindowMemory 
# from langchain_community.memory.kg import ConversationKGMemory 
# from langchain.memory import VectorStoreRetrieverMemory
# from langchain_community.vectorstores import Chroma

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # =============================================================================
# # 1. HYBRID MEMORY SYSTEM (Fixed for Exact Recall)
# # =============================================================================
# class HybridMemory(BaseMemory):
#     """
#     Combines exact short-term memory (Buffer) with long-term vector storage.
#     """
#     short_term: Any = None
#     vectorstore: Any = None
#     long_term: Any = None
#     kg_memory: Any = None
#     user_preferences: Dict = {}

#     def __init__(self, llm: BaseLanguageModel, embeddings, vectorstore_dir: str = "./memory_vectorstore"):
#         super().__init__()
#         # FIX: Use BufferWindowMemory (k=5) to remember the exact last 5 exchanges.
#         # This solves "What department did I say I was in?"
#         self.short_term = ConversationBufferWindowMemory(
#             memory_key="short_term_history",
#             k=5, 
#             return_messages=False 
#         )
        
#         self.vectorstore = Chroma(
#             embedding_function=embeddings,
#             persist_directory=vectorstore_dir
#         )
        
#         self.long_term = VectorStoreRetrieverMemory(
#             retriever=self.vectorstore.as_retriever(search_kwargs={"k": 2})
#         )
        
#         self.kg_memory = ConversationKGMemory(
#             llm=llm,
#             memory_key="knowledge_graph"
#         )
        
#         self.user_preferences = {}

#     @property
#     def memory_variables(self) -> List[str]:
#         return ["short_term_history", "relevant_past_knowledge", "entity_relationships", "user_preferences"]

#     def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
#         # Save exact conversation to buffer
#         self.short_term.save_context(inputs, outputs)
        
#         # Save to long-term vector DB
#         conversation_text = f"User: {inputs.get('input', '')}\nAI: {outputs.get('response', '')}"
#         self.long_term.save_context(
#             {"input": conversation_text},
#             {"output": datetime.now().isoformat()}
#         )
        
#         # Save entities
#         self.kg_memory.save_context(inputs, outputs)
        
#         # Simple preference extraction
#         user_input = inputs.get("input", "").lower()
#         if "it department" in user_input: self.user_preferences["department"] = "IT"
#         if "civil" in user_input: self.user_preferences["department"] = "Civil"
#         if "comps" in user_input or "computer" in user_input: self.user_preferences["department"] = "Computer"

#     def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
#         user_input = inputs.get("input", "")
        
#         short_context = self.short_term.load_memory_variables(inputs)
#         long_context = self.long_term.load_memory_variables({"input": user_input})
#         kg_context = self.kg_memory.load_memory_variables(inputs)
        
#         return {
#             "short_term_history": short_context.get("short_term_history", ""),
#             "relevant_past_knowledge": long_context.get("input", ""),
#             "entity_relationships": kg_context.get("knowledge_graph", ""),
#             "user_preferences": self.user_preferences
#         }

#     def clear(self):
#         self.short_term.clear()
#         self.long_term.clear()
#         self.kg_memory.clear()
#         self.user_preferences = {}

# # =============================================================================
# # 2. INTELLIGENT WEB CRAWLER (Strict APSIT Scope)
# # =============================================================================
# class IntelligentWebCrawler:
#     def __init__(self, embeddings, max_depth: int = 1, max_pages: int = 5):
#         self.embeddings = embeddings
#         self.max_pages = max_pages
#         self.visited_urls = set()

#     def crawl_for_query(self, start_url: str, query: str) -> List[Document]:
#         relevant_documents = []
        
#         # FIX: We only perform ONE high-quality search via DuckDuckGo logic here
#         # Instead of random crawling, we rely on the Agent's search trigger.
#         # This class simulates fetching the specific page if found.
        
#         # Note: In a real production crawler, we would use Google Search API/Bing API here.
#         # For this logic, we will assume the Agent passes a Google/DDG Search result URL.
#         # Since we don't have a live browser, we'll try to fetch the college homepage directly 
#         # if the query is general, or rely on the LLM's internal knowledge + DB.
        
#         # However, to fix "Dr. Smith", we need actual search.
#         # Since 'requests' can't easily search Google without an API key,
#         # we will fetch the specific faculty page if keywords match.
        
#         url_to_fetch = "https://www.apsit.edu.in"
#         if "civil" in query.lower():
#             url_to_fetch = "https://www.apsit.edu.in/department/civil-engineering/faculty"
#         elif "it" in query.lower() or "information" in query.lower():
#             url_to_fetch = "https://www.apsit.edu.in/department/information-technology/faculty"
#         elif "computer" in query.lower():
#             url_to_fetch = "https://www.apsit.edu.in/department/computer-engineering/faculty"
            
#         content = self._fetch_content(url_to_fetch)
#         if content:
#             doc = self._process_content(content, url_to_fetch)
#             relevant_documents.append(doc)
            
#         return relevant_documents

#     def _fetch_content(self, url):
#         try:
#             # User-Agent is required to not get blocked by college firewall
#             headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
#             response = requests.get(url, headers=headers, timeout=10)
#             if response.status_code == 200:
#                 return response.text
#         except Exception as e:
#             logger.error(f"Crawl Error {url}: {e}")
#         return None

#     def _process_content(self, content, url):
#         soup = BeautifulSoup(content, 'html.parser')
#         for script in soup(["script", "style", "nav", "footer"]): script.decompose()
#         text = soup.get_text(separator=' ', strip=True)
#         # Clean up excessive whitespace
#         text = ' '.join(text.split())
#         return Document(page_content=text[:6000], metadata={"source": url}) # Increased limit to read faculty lists

# # =============================================================================
# # 3. REACT AGENT (Strict Persona)
# # =============================================================================
# class AgentAction(Enum):
#     RETRIEVE = "retrieve"
#     SEARCH = "search"

# class ReActAgent:
#     def __init__(self, llm: BaseLanguageModel, retriever, crawler):
#         self.llm = llm
#         self.retriever = retriever
#         self.crawler = crawler

#     def process_query(self, query: str, memory: HybridMemory) -> str:
#         # 1. Decide Action
#         action = self._determine_action(query)
        
#         # 2. Execute Action
#         context_data = ""
#         if action == AgentAction.RETRIEVE:
#             if self.retriever:
#                 docs = self.retriever.get_relevant_documents(query)
#                 context_data = "\n".join([d.page_content for d in docs])
#             else:
#                 context_data = "No internal documents available."
                
#         elif action == AgentAction.SEARCH:
#             # FIX: Logic to fetch specific department pages
#             docs = self.crawler.crawl_for_query("https://www.apsit.edu.in", query)
#             if docs:
#                 context_data = "\n".join([d.page_content for d in docs])
#             else:
#                 context_data = "Could not access college website live. Using internal knowledge."
        
#         # 3. Generate Answer
#         return self._generate_response(query, context_data, memory)

#     def _determine_action(self, query: str) -> AgentAction:
#         query = query.lower()
#         # Force SEARCH for dynamic/faculty queries to avoid Hallucination
#         if any(x in query for x in ["hod", "head", "faculty", "professor", "teacher", "principal", "latest", "news", "notice"]):
#             return AgentAction.SEARCH
#         return AgentAction.RETRIEVE

#     def _generate_response(self, query, context_data, memory):
#         mem_vars = memory.load_memory_variables({"input": query})
#         history = mem_vars.get("short_term_history", "")
#         preferences = mem_vars.get("user_preferences", {})
        
#         # FIX: STRICT SYSTEM PROMPT
#         prompt = f"""
#         You are the Official AI Assistant for **A.P. Shah Institute of Technology (APSIT)** in Thane, Mumbai.
        
#         **STRICT RULES:**
#         1. You ONLY talk about APSIT (A.P. Shah Institute of Technology). Do NOT mention 'Aditya College' or generic info.
#         2. If the user asks about the HOD or Principal, use the 'CONTEXT FROM ACTION' below. If the context lists specific names (like Dr. Mugdha Agarwadkar for Civil), use them. Do NOT make up names like 'Dr. Smith'.
#         3. MEMORY: The user previously mentioned they are in the '{preferences.get('department', 'Unknown')}' department. Use this if relevant.
#         4. If the context is empty, say "I don't have that specific information right now" rather than guessing.
        
#         CONTEXT FROM LIVE SITE/DB:a
#         {context_data}
        
#         CONVERSATION HISTORY:
#         {history}
        
#         USER QUERY: {query}
        
#         Your Answer:
#         """
#         response = self.llm.invoke(prompt)
#         return response.content

# # =============================================================================
# # 4. PERSONALITY RESPONDER
# # =============================================================================
# @dataclass
# class BotPersonality:
#     traits: List[str]

# class PersonalityAwareResponder:
#     def __init__(self, personality: BotPersonality):
#         self.personality = personality

#     def generate_personality_response(self, base_response: str, query: str) -> str:
#         if "help" in query.lower() or "can you" in query.lower():
#             return f"I'd be happy to help you with that! {base_response}"
#         return base_response