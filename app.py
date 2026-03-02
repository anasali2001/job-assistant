# import os
# import json
# import uuid
# import datetime
# import streamlit as st
# from dotenv import load_dotenv
# import chromadb
# import chromadb.utils.embedding_functions as embedding_functions
# from openai import OpenAI

# # ==========================================
# # 1. SETUP & ENVIRONMENT
# # ==========================================
# # Load environment variables from .env file
# load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# # Hugging Face uses /data for persistent storage. If it doesn't exist, use local folder.
# DB_PATH = "/data/chroma_db" if os.path.exists("/data") else "./local_chroma_db"

# # OpenRouter Kimi Model (Moonshot)
# LLM_MODEL = "moonshotai/moonshot-v1-8k"

# st.set_page_config(page_title="UBL Second Brain", page_icon="🧠", layout="centered")

# # ==========================================
# # 2. INITIALIZE SERVICES
# # ==========================================
# @st.cache_resource
# def init_services():
#     if not OPENAI_API_KEY or not OPENROUTER_API_KEY:
#         return None, None

#     # A. OpenRouter Client (Using OpenAI's SDK but pointing to OpenRouter)
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=OPENROUTER_API_KEY,
#     )

#     # B. OpenAI Embeddings Function
#     # openai_ef = embedding_functions.OpenAIEmbeddingFunction(
#     #     api_key=OPENAI_API_KEY,
#     #     model_name="text-embedding-3-small"
#     # )
#     openai_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
#     model_name="all-MiniLM-L6-v2")

#     # C. ChromaDB Client
#     db_client = chromadb.PersistentClient(path=DB_PATH)
#     collection = db_client.get_or_create_collection(
#         name="ubl_analyst_logs",
#         embedding_function=openai_ef
#     )

#     return llm_client, collection

# llm_client, db_collection = init_services()

# # ==========================================
# # 3. CORE FUNCTIONS
# # ==========================================
# def extract_metadata(text):
#     """Uses Kimi (via OpenRouter) to extract JSON metadata from the log."""
#     system_prompt = """
#     You are a JSON extractor. Read the log and extract metadata. 
#     Return ONLY a valid JSON object. No markdown, no explanations.
#     Keys required:
#     - "task_type": (e.g., "task", "learning", "meeting", "issue", "solution")
#     - "tags": [list of relevant tags like "SQL", "Power BI", "Python", "Churn"]
#     - "project": (Name of project if mentioned, otherwise "General")
#     """
#     try:
#         response = llm_client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": f"Log: {text}"}
#             ]
#         )
        
#         raw_output = response.choices[0].message.content
#         cleaned = raw_output.replace('```json', '').replace('```', '').strip()
#         metadata = json.loads(cleaned)
        
#         # ChromaDB requires lists to be converted to strings
#         if isinstance(metadata.get('tags'), list):
#             metadata['tags'] = ", ".join(metadata['tags'])
            
#         return metadata
#     except Exception as e:
#         return {"task_type": "log", "tags": "general", "project": "General"}

# def log_entry(text):
#     """Saves log to ChromaDB with OpenAI Embeddings."""
#     metadata = extract_metadata(text)
#     metadata['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     doc_id = str(uuid.uuid4())
    
#     # Chroma handles calling the OpenAI Embedding API automatically here
#     db_collection.add(
#         ids=[doc_id],
#         documents=[text],
#         metadatas=[metadata]
#     )
#     return metadata

# def query_brain(question):
#     """Retrieves context from ChromaDB and generates an answer using Kimi."""
#     # 1. Retrieve top 5 matches
#     results = db_collection.query(
#         query_texts=[question],
#         n_results=5
#     )
    
#     retrieved_docs = results['documents'][0]
#     retrieved_metadata = results['metadatas'][0]
    
#     if not retrieved_docs:
#         return "🤖 I couldn't find any relevant memories in your database."
        
#     # 2. Format context
#     context_str = ""
#     for doc, meta in zip(retrieved_docs, retrieved_metadata):
#         context_str += f"Log [{meta.get('date', 'Unknown')}] (Project: {meta.get('project', 'None')}): {doc}\n"
        
#     # 3. Ask Kimi via OpenRouter
#     system_prompt = "You are a highly intelligent 'Second Brain' and Personal Assistant for a Data Analyst working at UBL. Answer questions based STRICTLY on the provided past work logs. Be concise, professional, and format SQL/Python code in markdown blocks."
    
#     user_prompt = f"Here are my past work logs:\n{context_str}\n\nMy Question: {question}"
    
#     response = llm_client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ]
#     )
    
#     return response.choices[0].message.content

# # ==========================================
# # 4. STREAMLIT USER INTERFACE
# # ==========================================
# st.title("🧠 UBL Data Analyst Second Brain")

# if not OPENAI_API_KEY or not OPENROUTER_API_KEY:
#     st.error("⚠️ API Keys are missing. Please add them to your .env file.")
#     st.stop()

# # Initialize Chat History
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # Display Chat History
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # User Input
# if prompt := st.chat_input("Type '/log <your update>' OR ask a question..."):
    
#     # Display user message
#     st.chat_message("user").markdown(prompt)
#     st.session_state.messages.append({"role": "user", "content": prompt})
    
#     # Process Command
#     if prompt.lower().startswith("/log "):
#         log_text = prompt[5:].strip()
#         with st.spinner("Analyzing and saving to memory..."):
#             meta = log_entry(log_text)
#             reply = f"✅ **Saved successfully!**\n*Project:* `{meta.get('project')}` | *Tags:* `{meta.get('tags')}`"
            
#         st.chat_message("assistant").markdown(reply)
#         st.session_state.messages.append({"role": "assistant", "content": reply})
        
#     else:
#         # Treat as a Query
#         with st.spinner("Searching second brain..."):
#             answer = query_brain(prompt)
            
#         st.chat_message("assistant").markdown(answer)
#         st.session_state.messages.append({"role": "assistant", "content": answer})





# import os
# import json
# import uuid
# import datetime
# import streamlit as st
# from dotenv import load_dotenv
# import chromadb
# import chromadb.utils.embedding_functions as embedding_functions
# from openai import OpenAI

# # ==========================================
# # 1. SETUP & ENVIRONMENT
# # ==========================================
# load_dotenv()  # Load .env file

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# if not OPENROUTER_API_KEY:
#     st.error("⚠️ OPENROUTER_API_KEY is missing in .env or environment variables.")
#     st.stop()

# # Storage path
# DB_PATH = "/data/chroma_db" if os.path.exists("/data") else "./local_chroma_db"

# # OpenRouter LLM Model
# LLM_MODEL = "moonshotai/kimi-k2"

# st.set_page_config(page_title="UBL Second Brain", page_icon="🧠", layout="centered")

# # ==========================================
# # 2. INITIALIZE SERVICES
# # ==========================================
# # @st.cache_resource
# # def init_services():
# #     # OpenRouter LLM client
# #     llm_client = OpenAI(
# #         base_url="https://openrouter.ai/api/v1",
# #         api_key=OPENROUTER_API_KEY
# #     )

# #     # SentenceTransformer embeddings (local, no API key)
# #     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
# #         model_name="all-MiniLM-L6-v2"
# #     )

# #     # ChromaDB client
# #     db_client = chromadb.PersistentClient(path=DB_PATH)

# #     # Create collection if it doesn't exist
# #     collection = db_client.get_or_create_collection(
# #         name="ubl_analyst_logs",
# #         embedding_function=embedding_fn
# #     )

# #     return llm_client, collection


# # ==========================================
# # 2. INITIALIZE SERVICES
# # ==========================================
# @st.cache_resource(show_spinner=False)
# def init_services():
#     # 1. DEBUG: Verify Key Loading (Look at your terminal when running)
#     if not OPENROUTER_API_KEY:
#         raise ValueError("API Key is None. Check .env file.")
    
#     print(f"--- DEBUG: Loading OpenRouter Key: {OPENROUTER_API_KEY[:6]}... ---")

#     # 2. Initialize Client with REQUIRED OpenRouter headers
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=OPENROUTER_API_KEY,
#         default_headers={
#             "HTTP-Referer": "http://localhost:8501", # Required by OpenRouter
#             "X-Title": "UBL Second Brain",           # Required by OpenRouter
#         }
#     )

#     # 3. SentenceTransformer embeddings (local)
#     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name="all-MiniLM-L6-v2"
#     )

#     # 4. ChromaDB client
#     try:
#         db_client = chromadb.PersistentClient(path=DB_PATH)
#         collection = db_client.get_or_create_collection(
#             name="ubl_analyst_logs",
#             embedding_function=embedding_fn
#         )
#     except Exception as e:
#         print(f"ChromaDB Error: {e}")
#         st.error("Error connecting to Database. Check permissions.")
#         st.stop()

#     return llm_client, collection

# llm_client, db_collection = init_services()

# # ==========================================
# # 3. CORE FUNCTIONS
# # ==========================================
# def extract_metadata(text):
#     """Extract JSON metadata from log using Kimi (OpenRouter)."""
#     system_prompt = """
#     You are a JSON extractor. Read the log and extract metadata. 
#     Return ONLY a valid JSON object. No markdown, no explanations.
#     Keys required:
#     - "task_type": (e.g., "task", "learning", "meeting", "issue", "solution")
#     - "tags": [list of relevant tags like "SQL", "Power BI", "Python", "Churn"]
#     - "project": (Name of project if mentioned, otherwise "General")
#     """
#     try:
#         response = llm_client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": f"Log: {text}"}
#             ],
#             max_tokens=500
#         )
#         raw_output = response.choices[0].message.content
#         cleaned = raw_output.replace("```json", "").replace("```", "").strip()
#         metadata = json.loads(cleaned)
#         # Ensure tags are string
#         if isinstance(metadata.get("tags"), list):
#             metadata["tags"] = ", ".join(metadata["tags"])
#         return metadata
#     except Exception:
#         return {"task_type": "log", "tags": "general", "project": "General"}

# def log_entry(text):
#     """Save log to ChromaDB with embeddings."""
#     metadata = extract_metadata(text)
#     metadata["date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     doc_id = str(uuid.uuid4())
#     db_collection.add(
#         ids=[doc_id],
#         documents=[text],
#         metadatas=[metadata]
#     )
#     return metadata

# def query_brain(question):
#     """Retrieve top memories from ChromaDB and answer using OpenRouter."""
#     results = db_collection.query(query_texts=[question], n_results=5)
#     retrieved_docs = results["documents"][0]
#     retrieved_metadata = results["metadatas"][0]

#     if not retrieved_docs:
#         return "🤖 I couldn't find any relevant memories in your database."

#     context_str = ""
#     for doc, meta in zip(retrieved_docs, retrieved_metadata):
#         context_str += f"Log [{meta.get('date','Unknown')}] (Project: {meta.get('project','None')}): {doc}\n"

#     system_prompt = "You are a highly intelligent 'Second Brain' and Personal Assistant for a Data Analyst at UBL. Answer based STRICTLY on the provided past work logs. Be concise and format SQL/Python in markdown."

#     user_prompt = f"Here are my past work logs:\n{context_str}\n\nMy Question: {question}"

#     response = llm_client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         max_tokens=1000
#     )

#     return response.choices[0].message.content

# # ==========================================
# # 4. STREAMLIT INTERFACE
# # ==========================================
# st.title("🧠 UBL Data Analyst Second Brain")

# # Chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # User input
# if prompt := st.chat_input("Type '/log <your update>' OR ask a question..."):
#     st.chat_message("user").markdown(prompt)
#     st.session_state.messages.append({"role": "user", "content": prompt})

#     if prompt.lower().startswith("/log "):
#         log_text = prompt[5:].strip()
#         with st.spinner("Saving to memory..."):
#             meta = log_entry(log_text)
#             reply = f"✅ **Saved successfully!**\n*Project:* `{meta.get('project')}` | *Tags:* `{meta.get('tags')}`"
#         st.chat_message("assistant").markdown(reply)
#         st.session_state.messages.append({"role": "assistant", "content": reply})
#     else:
#         with st.spinner("Searching second brain..."):
#             answer = query_brain(prompt)
#         st.chat_message("assistant").markdown(answer)
#         st.session_state.messages.append({"role": "assistant", "content": answer})

# # ==========================================
# # 5. Optional: View Memory in Streamlit
# # ==========================================
# with st.expander("📂 View All Memories"):
#     data = db_collection.get()
#     for doc, meta in zip(data["documents"], data["metadatas"]):
#         st.write("Document:", doc)
#         st.write("Metadata:", meta)
#         st.write("---")
#     st.write("Total records:", db_collection.count())





















# import os
# import json
# import uuid
# import datetime
# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from dotenv import load_dotenv
# import chromadb
# import chromadb.utils.embedding_functions as embedding_functions
# from openai import OpenAI

# # ==========================================
# # 1. SETUP & CONFIGURATION
# # ==========================================
# st.set_page_config(page_title="UBL Analyst Brain", page_icon="🧠", layout="wide")

# load_dotenv()
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# if not OPENROUTER_API_KEY:
#     st.error("⚠️ OPENROUTER_API_KEY is missing in .env")
#     st.stop()

# # USE A HIGH-QUALITY FREE MODEL (Gemini Flash 2.0 is fast & smart)
# # If this fails, try "deepseek/deepseek-r1:free" or "meta-llama/llama-3-8b-instruct:free"
# # LLM_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
# LLM_MODEL = "moonshotai/kimi-k2"


# DB_PATH = "/data/chroma_db" if os.path.exists("/data") else "./local_chroma_db"

# # ==========================================
# # 2. INITIALIZE SERVICES (Cached)
# # ==========================================
# @st.cache_resource(show_spinner=False)
# def init_services():
#     # 1. API Client
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=OPENROUTER_API_KEY,
#         default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "UBL Second Brain"}
#     )

#     # 2. Embeddings
#     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name="all-MiniLM-L6-v2"
#     )

#     # 3. Database
#     try:
#         db_client = chromadb.PersistentClient(path=DB_PATH)
#         collection = db_client.get_or_create_collection(name="ubl_analyst_logs", embedding_function=embedding_fn)
#     except Exception as e:
#         st.error(f"Database Error: {e}")
#         st.stop()

#     return llm_client, collection

# llm_client, db_collection = init_services()

# # ==========================================
# # 3. INTELLIGENCE FUNCTIONS
# # ==========================================
# def extract_metadata(text):
#     """Smartly categorizes your log."""
#     system_prompt = """
#     You are a Data Analyst's Assistant. Analyze the log.
#     Return ONLY valid JSON.
#     Fields:
#     - "project": Extract project name (e.g., "Churn", "Migration", "Dashboard"). Default to "General".
#     - "tags": List of tech keywords (e.g., ["SQL", "PowerBI", "Python"]).
#     - "mood": "Neutral", "Positive", "Frustrated" (based on tone).
#     """
#     try:
#         response = llm_client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": text}
#             ],
#             max_tokens=300,
#             temperature=0.1 # Low temp for consistent JSON
#         )
#         raw = response.choices[0].message.content
#         clean_json = raw.replace("```json", "").replace("```", "").strip()
#         meta = json.loads(clean_json)
        
#         # Validation
#         if isinstance(meta.get("tags"), list):
#             meta["tags"] = ", ".join(meta["tags"]) # Chroma needs string
#         return meta
#     except:
#         return {"project": "General", "tags": "General", "mood": "Neutral"}

# def save_memory(text):
#     meta = extract_metadata(text)
#     # Add timestamp for sorting
#     now = datetime.datetime.now()
#     meta["date"] = now.strftime("%Y-%m-%d %H:%M:%S")
#     meta["timestamp"] = now.timestamp() 
    
#     doc_id = str(uuid.uuid4())
#     db_collection.add(ids=[doc_id], documents=[text], metadatas=[meta])
#     return meta

# def ask_brain(query, project_filter=None):
#     # 1. Context Aware Date
#     today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    
#     # 2. Filtered Search
#     where_clause = {"project": project_filter} if project_filter and project_filter != "All" else None
    
#     results = db_collection.query(
#         query_texts=[query], 
#         n_results=7, # Retrieve more context
#         where=where_clause
#     )

#     docs = results["documents"][0]
#     metas = results["metadatas"][0]

#     if not docs:
#         return "📭 No memories found matching that query."

#     # 3. Construct Context
#     context_text = ""
#     for d, m in zip(docs, metas):
#         context_text += f"- [{m.get('date')}] (Proj: {m.get('project')}) {d}\n"

#     # 4. Premium System Prompt
#     system_prompt = f"""
#     You are an expert Data Analyst Chief of Staff. 
#     TODAY IS: {today}.
    
#     Rules:
#     1. Answer strictly based on the provided logs.
#     2. If the user asks "What did I do today?", summarize the logs with today's date.
#     3. Format code blocks (SQL/Python) clearly.
#     4. Be professional but concise.
#     """

#     response = llm_client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"LOGS:\n{context_text}\n\nUSER QUESTION: {query}"}
#         ],
#         max_tokens=1500
#     )
#     return response.choices[0].message.content

# # ==========================================
# # 4. UI: SIDEBAR & NAVIGATION
# # ==========================================
# st.sidebar.title("🧠 Second Brain")
# st.sidebar.markdown("---")

# # Global Filter (Affects Chat & Analytics)
# all_data = db_collection.get()
# if all_data['ids']:
#     df_all = pd.DataFrame(all_data['metadatas'])
#     df_all['document'] = all_data['documents']
#     df_all['id'] = all_data['ids']
#     unique_projects = ["All"] + list(df_all['project'].unique())
# else:
#     unique_projects = ["All"]
#     df_all = pd.DataFrame()

# selected_project = st.sidebar.selectbox("📂 Filter Context by Project", unique_projects)

# st.sidebar.markdown("---")
# st.sidebar.caption(f"Using Model: `{LLM_MODEL}`")

# # ==========================================
# # 5. MAIN INTERFACE (TABS)
# # ==========================================
# tab1, tab2, tab3 = st.tabs(["💬 Chat & Log", "📊 Dashboard", "🗂️ Memory Bank"])

# # --- TAB 1: CHAT ---
# with tab1:
#     st.header("Daily Operations")
    
#     # Chat History
#     if "messages" not in st.session_state:
#         st.session_state.messages = [{"role": "assistant", "content": "Ready. Type `/log` to save memory or ask me anything."}]

#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     # Input Area
#     if prompt := st.chat_input("Type '/log <text>' OR ask a question..."):
#         # User Message
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         st.chat_message("user").markdown(prompt)

#         # Logic
#         if prompt.lower().startswith("/log "):
#             log_content = prompt[5:].strip()
#             with st.spinner("🧠 Encoding memory..."):
#                 meta = save_memory(log_content)
#                 response = f"✅ **Logged** to `{meta['project']}`\nTags: `{meta['tags']}`"
#                 st.rerun() # Refresh to update filters immediately
#         else:
#             with st.spinner("🔎 Searching neural network..."):
#                 response = ask_brain(prompt, selected_project)
        
#         # Assistant Response
#         st.session_state.messages.append({"role": "assistant", "content": response})
#         st.chat_message("assistant").markdown(response)

# # --- TAB 2: DASHBOARD ---
# with tab2:
#     st.header("Analytics Dashboard")
#     if not df_all.empty:
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.metric("Total Memories", len(df_all))
#         with col2:
#             st.metric("Active Projects", df_all['project'].nunique())
#         with col3:
#             st.metric("Latest Entry", df_all['date'].max().split()[0])

#         # Charts
#         c1, c2 = st.columns(2)
#         with c1:
#             st.subheader("Logs per Project")
#             proj_counts = df_all['project'].value_counts().reset_index()
#             fig_proj = px.bar(proj_counts, x='project', y='count', color='project')
#             st.plotly_chart(fig_proj, use_container_width=True)
        
#         with c2:
#             st.subheader("Activity Timeline")
#             # Convert date to datetime object for grouping
#             df_all['day'] = pd.to_datetime(df_all['date']).dt.date
#             timeline = df_all.groupby('day').size().reset_index(name='logs')
#             fig_time = px.line(timeline, x='day', y='logs', markers=True)
#             st.plotly_chart(fig_time, use_container_width=True)
#     else:
#         st.info("Start logging data to see analytics.")

# # --- TAB 3: MEMORY BANK ---
# with tab3:
#     st.header("🗂️ Database Management")
    
#     if not df_all.empty:
#         # Search Box
#         search_term = st.text_input("🔍 Search logs manually", "")
        
#         # Filter Logic
#         display_df = df_all
#         if selected_project != "All":
#             display_df = display_df[display_df['project'] == selected_project]
#         if search_term:
#             display_df = display_df[display_df['document'].str.contains(search_term, case=False)]

#         # Display Dataframe
#         st.dataframe(
#             display_df[['date', 'project', 'document', 'tags']], 
#             use_container_width=True,
#             hide_index=True
#         )

#         # Delete Functionality
#         st.subheader("🗑️ Delete a Memory")
#         col_del, col_btn = st.columns([3, 1])
#         with col_del:
#             del_id = st.selectbox("Select Log to Delete", display_df['document'].tolist(), format_func=lambda x: x[:80]+"...")
#         with col_btn:
#             if st.button("Delete Selected"):
#                 # Find ID associated with text
#                 id_to_delete = display_df[display_df['document'] == del_id]['id'].values[0]
#                 db_collection.delete(ids=[id_to_delete])
#                 st.success("Deleted!")
#                 st.rerun()
#     else:
#         st.write("Database is empty.")















# import os
# import json
# import uuid
# import datetime
# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from dotenv import load_dotenv
# import chromadb
# import chromadb.utils.embedding_functions as embedding_functions
# from openai import OpenAI

# # ==========================================
# # 1. SETUP & CONFIGURATION
# # ==========================================
# st.set_page_config(page_title="UBL Analyst Brain", page_icon="🧠", layout="wide")

# load_dotenv()
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# if not OPENROUTER_API_KEY:
#     st.error("⚠️ OPENROUTER_API_KEY is missing in .env")
#     st.stop()

# # Using Gemini Flash 2.0 (Fast, Smart, Free)
# LLM_MODEL = "moonshotai/kimi-k2"

# DB_PATH = "/data/chroma_db" if os.path.exists("/data") else "./local_chroma_db"

# # ==========================================
# # 2. INITIALIZE SERVICES
# # ==========================================
# @st.cache_resource(show_spinner=False)
# def init_services():
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=OPENROUTER_API_KEY,
#         default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "UBL Second Brain"}
#     )

#     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name="all-MiniLM-L6-v2"
#     )

#     try:
#         db_client = chromadb.PersistentClient(path=DB_PATH)
#         collection = db_client.get_or_create_collection(name="ubl_analyst_logs", embedding_function=embedding_fn)
#     except Exception as e:
#         st.error(f"Database Error: {e}")
#         st.stop()

#     return llm_client, collection

# llm_client, db_collection = init_services()

# # ==========================================
# # 3. INTELLIGENCE FUNCTIONS
# # ==========================================
# def extract_metadata(text):
#     """Smartly categorizes your log."""
#     system_prompt = """
#     You are a Data Analyst's Assistant. Analyze the log. Return ONLY valid JSON.
#     Fields:
#     - "project": Extract project name (e.g., "Churn", "Migration", "Dashboard"). Default to "General".
#     - "tags": List of tech keywords.
#     """
#     try:
#         response = llm_client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
#             max_tokens=300,
#             temperature=0.1
#         )
#         raw = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
#         meta = json.loads(raw)
#         if isinstance(meta.get("tags"), list): meta["tags"] = ", ".join(meta["tags"])
#         return meta
#     except:
#         return {"project": "General", "tags": "General"}

# def save_memory(text):
#     meta = extract_metadata(text)
#     now = datetime.datetime.now()
#     meta["date"] = now.strftime("%Y-%m-%d %H:%M:%S")
#     doc_id = str(uuid.uuid4())
#     db_collection.add(ids=[doc_id], documents=[text], metadatas=[meta])
#     return meta

# def process_chat(query, project_filter=None):
#     """Handles Chat AND Deletion logic."""
#     today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    
#     # 1. Retrieve Context with IDs
#     where_clause = {"project": project_filter} if project_filter and project_filter != "All" else None
#     results = db_collection.query(query_texts=[query], n_results=5, where=where_clause)

#     docs = results["documents"][0]
#     metas = results["metadatas"][0]
#     ids = results["ids"][0]

#     if not docs:
#         return "📭 No relevant memories found."

#     # 2. Build Context containing IDs (Invisible to user, visible to Bot)
#     context_text = ""
#     for i, (d, m, doc_id) in enumerate(zip(docs, metas, ids)):
#         context_text += f"Record_ID: {doc_id} | Date: {m.get('date')} | Log: {d}\n"

#     # 3. System Prompt with 'Tools'
#     system_prompt = f"""
#     You are a Data Analyst's Second Brain. Today is {today}.
    
#     Capabilities:
#     1. Answer questions based on the logs.
#     2. DELETE logs if the user explicitly asks.
    
#     CRITICAL INSTRUCTION FOR DELETION:
#     If the user asks to delete a specific log/record found in the context:
#     - Identify the 'Record_ID' from the context.
#     - Reply ONLY with this exact string: `DELETE_REQUEST: <Record_ID>`
#     - Do not say anything else. Just that string.
    
#     Otherwise, answer the question normally.
#     """

#     response = llm_client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"CONTEXT LOGS:\n{context_text}\n\nUSER QUESTION: {query}"}
#         ],
#         max_tokens=500
#     )
    
#     bot_reply = response.choices[0].message.content.strip()

#     # 4. Check for Deletion Signal
#     if bot_reply.startswith("DELETE_REQUEST:"):
#         id_to_delete = bot_reply.split(":")[1].strip()
#         try:
#             db_collection.delete(ids=[id_to_delete])
#             return "🗑️ **Deleted Successfully.** I have removed that memory from the database."
#         except Exception as e:
#             return f"⚠️ Error deleting: {e}"
            
#     return bot_reply

# # ==========================================
# # 4. UI: SIDEBAR & NAVIGATION
# # ==========================================
# st.sidebar.title("🧠 Second Brain")
# st.sidebar.markdown("---")

# # Refresh Data for filters
# all_data = db_collection.get()
# if all_data['ids']:
#     df_all = pd.DataFrame(all_data['metadatas'])
#     df_all['document'] = all_data['documents']
#     df_all['id'] = all_data['ids']
#     unique_projects = ["All"] + list(df_all['project'].unique())
# else:
#     unique_projects = ["All"]
#     df_all = pd.DataFrame()

# selected_project = st.sidebar.selectbox("📂 Filter Project", unique_projects)
# st.sidebar.caption("Commands: `/log <text>`")

# # ==========================================
# # 5. MAIN INTERFACE
# # ==========================================
# tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "🗂️ Memory Bank"])

# # --- TAB 1: CHAT ---
# with tab1:
#     if "messages" not in st.session_state:
#         st.session_state.messages = [{"role": "assistant", "content": "Hi. How may I help you, Anas?"}]

#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     if prompt := st.chat_input("Type '/log <text>' OR ask a question..."):
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         st.chat_message("user").markdown(prompt)

#         if prompt.lower().startswith("/log "):
#             log_content = prompt[5:].strip()
#             with st.spinner("Saving..."):
#                 meta = save_memory(log_content)
#                 reply = f"✅ **Logged** to `{meta['project']}`"
#                 # Rerun to update dashboard immediately
#                 st.session_state.messages.append({"role": "assistant", "content": reply})
#                 st.rerun() 
#         else:
#             with st.spinner("Processing..."):
#                 reply = process_chat(prompt, selected_project)
                
#         st.session_state.messages.append({"role": "assistant", "content": reply})
#         st.chat_message("assistant").markdown(reply)

# # --- TAB 2: DASHBOARD ---
# with tab2:
#     if not df_all.empty:
#         col1, col2 = st.columns(2)
#         with col1:
#             st.metric("Total Memories", len(df_all))
#             proj_counts = df_all['project'].value_counts().reset_index()
#             fig = px.pie(proj_counts, values='count', names='project', title="Project Distribution")
#             st.plotly_chart(fig, use_container_width=True)
#         with col2:
#              # Timeline
#             df_all['day'] = pd.to_datetime(df_all['date']).dt.date
#             timeline = df_all.groupby('day').size().reset_index(name='count')
#             fig_line = px.line(timeline, x='day', y='count', title="Activity Timeline")
#             st.plotly_chart(fig_line, use_container_width=True)
#     else:
#         st.info("No data yet.")

# # --- TAB 3: DATA ---
# with tab3:
#     if not df_all.empty:
#         st.dataframe(df_all[['date', 'project', 'document', 'tags']], use_container_width=True)
#     else:
#         st.write("Empty.")

















# #final boss
# import os
# import json
# import uuid
# import datetime
# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from dotenv import load_dotenv
# import chromadb
# import chromadb.utils.embedding_functions as embedding_functions
# from openai import OpenAI

# # ==========================================
# # 1. PAGE CONFIG & SETUP
# # ==========================================
# st.set_page_config(
#     page_title="UBL Analyst Brain", 
#     page_icon="🧠", 
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS to stabilize the chat interface and make it look premium
# # st.markdown("""
# # <style>
# #     .stChatInput {position: fixed; bottom: 0; padding-bottom: 1rem; z-index: 1000;}
# #     .block-container {padding-bottom: 6rem;} 
# #     h1 {font-family: 'Helvetica', sans-serif;}
# # </style>
# # """, unsafe_allow_html=True)

# st.markdown("""
# <style>
#     /* 1. Force the Chat Input to be WIDE and Centered */
#     .stChatInput {
#         max-width: 95% !important; /* Occupy 95% of available width */
#         width: 100% !important;
#         margin-left: auto;
#         margin-right: auto;
#         padding-bottom: 20px;
#     }

#     /* 2. Remove default narrow constraints of the main block */
#     .block-container {
#         max-width: 100% !important;
#         padding-left: 2rem !important;
#         padding-right: 2rem !important;
#         padding-top: 2rem !important;
#         padding-bottom: 5rem !important;
#     }

#     /* 3. Style the Headers */
#     h1, h2, h3 {
#         font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
#         font-weight: 600;
#     }
# </style>
# """, unsafe_allow_html=True)

# load_dotenv()
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# if not OPENROUTER_API_KEY:
#     st.error("⚠️ OPENROUTER_API_KEY is missing in .env")
#     st.stop()

# # NOTE: Using Gemini Flash 2.0 (Free & Fast) to avoid 402 Payment Errors
# # LLM_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
# LLM_MODEL = "moonshotai/kimi-k2"


# DB_PATH = "/data/chroma_db" if os.path.exists("/data") else "./local_chroma_db"

# # ==========================================
# # 2. BACKEND SERVICES
# # ==========================================
# @st.cache_resource(show_spinner=False)
# def init_services():
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=OPENROUTER_API_KEY,
#         default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "UBL Second Brain"}
#     )
    
#     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name="all-MiniLM-L6-v2"
#     )

#     try:
#         db_client = chromadb.PersistentClient(path=DB_PATH)
#         collection = db_client.get_or_create_collection(name="ubl_analyst_logs", embedding_function=embedding_fn)
#     except Exception as e:
#         st.error(f"Database Error: {e}")
#         st.stop()

#     return llm_client, collection

# llm_client, db_collection = init_services()

# # ==========================================
# # 3. LOGIC & INTELLIGENCE
# # ==========================================
# def extract_metadata(text):
#     system_prompt = """
#     You are a Data Analyst's Assistant. Return ONLY valid JSON.
#     Fields:
#     - "project": Extract project name (e.g., "Churn", "Migration"). Default "General".
#     - "tags": List of tech keywords.
#     """
#     try:
#         response = llm_client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
#             max_tokens=200, temperature=0.1
#         )
#         raw = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
#         meta = json.loads(raw)
#         if isinstance(meta.get("tags"), list): meta["tags"] = ", ".join(meta["tags"])
#         return meta
#     except:
#         return {"project": "General", "tags": "General"}

# def save_memory(text):
#     meta = extract_metadata(text)
#     now = datetime.datetime.now()
#     meta["date"] = now.strftime("%Y-%m-%d %H:%M:%S")
#     doc_id = str(uuid.uuid4())
#     db_collection.add(ids=[doc_id], documents=[text], metadatas=[meta])
#     return meta

# def analyze_intent(query, project_filter=None):
#     """
#     Determines if the user wants to answer a question OR delete a log.
#     If delete, it locates the ID but DOES NOT delete it yet.
#     """
#     # 1. Search Context
#     where_clause = {"project": project_filter} if project_filter and project_filter != "All" else None
#     results = db_collection.query(query_texts=[query], n_results=5, where=where_clause)
    
#     docs = results["documents"][0]
#     metas = results["metadatas"][0]
#     ids = results["ids"][0]
    
#     if not docs:
#         return {"type": "message", "content": "📭 I couldn't find any relevant logs."}

#     # 2. Build Context for LLM
#     context_str = ""
#     for i, (d, m, doc_id) in enumerate(zip(docs, metas, ids)):
#         context_str += f"ID: {doc_id} | Date: {m.get('date')} | Text: {d}\n"

#     # 3. Ask LLM what to do
#     system_prompt = f"""
#     You are a helpful assistant. Today is {datetime.datetime.now().strftime("%A, %B %d, %Y")}.
    
#     Rules:
#     1. If the user wants to DELETE a specific log found in the context:
#        - Return EXACTLY: `CONFIRM_DELETE: <ID> | <Short Text Summary>`
#     2. Otherwise, answer the user's question helpfuly based on the logs.
#     """

#     response = llm_client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"CONTEXT:\n{context_str}\n\nUSER PROMPT: {query}"}
#         ],
#         max_tokens=500
#     )
    
#     content = response.choices[0].message.content.strip()
    
#     if content.startswith("CONFIRM_DELETE:"):
#         try:
#             parts = content.split(":", 1)[1].split("|")
#             log_id = parts[0].strip()
#             log_summary = parts[1].strip() if len(parts) > 1 else "this log"
#             return {"type": "confirm_delete", "id": log_id, "summary": log_summary}
#         except:
#             return {"type": "message", "content": "❌ Error parsing deletion request."}
            
#     return {"type": "message", "content": content}

# # ==========================================
# # 4. UI COMPONENTS
# # ==========================================

# # Initialize Session State
# if "messages" not in st.session_state:
#     st.session_state.messages = [{"role": "assistant", "content": "👋 Hi Anas. I'm ready."}]
# if "pending_delete" not in st.session_state:
#     st.session_state.pending_delete = None

# # --- SIDEBAR ---
# with st.sidebar:
#     st.header("🧠 Second Brain")
#     st.divider()
    
#     # Load Data for Stats
#     all_data = db_collection.get()
#     if all_data['ids']:
#         df_all = pd.DataFrame(all_data['metadatas'])
#         df_all['document'] = all_data['documents']
#         unique_projects = ["All"] + list(df_all['project'].unique())
#     else:
#         unique_projects = ["All"]
#         df_all = pd.DataFrame()

#     selected_project = st.selectbox("📂 Project Filter", unique_projects)
    
#     st.divider()
#     st.info("💡 Tip: Type `/log <text>` to save. Ask 'Delete that log' to remove.")

# # --- MAIN TABS ---
# tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "🗂️ Memory Bank"])

# with tab1:
#     # 1. Render Chat History
#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     # 2. Render Confirmation Box (Only if pending delete)
#     if st.session_state.pending_delete:
#         with st.chat_message("assistant"):
#             st.warning(f"⚠️ **Are you sure?**\n\nDeleting: *{st.session_state.pending_delete['summary']}*")
#             col_y, col_n = st.columns([1,4])
            
#             if col_y.button("✅ Yes, Delete"):
#                 db_collection.delete(ids=[st.session_state.pending_delete['id']])
#                 st.session_state.messages.append({"role": "assistant", "content": "🗑️ **Deleted.**"})
#                 st.session_state.pending_delete = None
#                 st.rerun()
                
#             if col_n.button("❌ Cancel"):
#                 st.session_state.messages.append({"role": "assistant", "content": "Cancelled."})
#                 st.session_state.pending_delete = None
#                 st.rerun()

#     # 3. Chat Input (Sticky at bottom)
#     if prompt := st.chat_input(f"Type here... /log <content> for logging"):
#         # Reset any pending actions if user types new thing
#         st.session_state.pending_delete = None 
        
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         st.chat_message("user").markdown(prompt)

#         # Logic
#         if prompt.lower().startswith("/log "):
#             log_text = prompt[5:].strip()
#             with st.spinner("Writing to memory..."):
#                 meta = save_memory(log_text)
#                 reply = f"✅ Saved to **{meta['project']}**"
#                 st.session_state.messages.append({"role": "assistant", "content": reply})
#                 st.rerun()
#         else:
#             with st.spinner("Thinking..."):
#                 result = analyze_intent(prompt, selected_project)
                
#                 if result["type"] == "message":
#                     st.session_state.messages.append({"role": "assistant", "content": result["content"]})
#                     st.rerun()
#                 elif result["type"] == "confirm_delete":
#                     st.session_state.pending_delete = result
#                     st.rerun()

# with tab2:
#     if not df_all.empty:
#         c1, c2 = st.columns(2)
#         with c1:
#             fig = px.pie(df_all, names='project', title="Project Distribution", hole=0.3)
#             st.plotly_chart(fig, use_container_width=True)
#         with c2:
#             df_all['day'] = pd.to_datetime(df_all['date']).dt.date
#             timeline = df_all.groupby('day').size().reset_index(name='count')
#             fig2 = px.bar(timeline, x='day', y='count', title="Daily Logs")
#             st.plotly_chart(fig2, use_container_width=True)
#     else:
#         st.info("No data available for dashboard.")

# with tab3:
#     if not df_all.empty:
#         st.markdown("### Database Records")
#         st.dataframe(df_all[['date', 'project', 'document', 'tags']], use_container_width=True)
#     else:
#         st.write("Database is empty.")













#Pinecone
import os
import json
import uuid
import datetime
import time
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
load_dotenv()

# ==========================================
# 1. PAGE CONFIG & PREMIUM CSS
# ==========================================
st.set_page_config(
    page_title="UBL Analyst Brain", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed" # Collapsed until logged in
)

st.markdown("""
<style>
    .stChatInput {max-width: 95% !important; width: 100% !important; margin: 0 auto; padding-bottom: 20px;}
    .block-container {max-width: 100%; padding: 2rem 2rem 5rem 2rem;}
    h1, h2, h3 {font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SECURITY & AUTHENTICATION
# ==========================================
# This acts as a Gatekeeper. No code runs below this until password is correct.
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    # 1. Get password from environment
    env_pass = os.getenv("APP_PASSWORD")
    
    # 2. Get what you typed
    input_pass = st.session_state.password_input

    # 3. DEBUG PRINT (Look at your terminal!)
    print(f"--- DEBUG LOG ---")
    print(f"1. Password in .env file: '{env_pass}'") 
    print(f"2. Password you typed:    '{input_pass}'")
    print(f"-----------------")

    # 4. robust check (removes hidden spaces)
    if env_pass and input_pass.strip() == env_pass.strip():
        st.session_state.authenticated = True
    else:
        st.error("⛔ Incorrect Password")

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🧠 UBL Brain Login</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.text_input("Enter Access Code", type="password", key="password_input", on_change=check_password)
    st.stop()  # STOPS APP EXECUTION HERE IF NOT LOGGED IN

# ==========================================
# 3. SETUP CLOUD SERVICES
# ==========================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not OPENROUTER_API_KEY or not PINECONE_API_KEY:
    st.error("⚠️ API Keys missing. Check .env or Streamlit Secrets.")
    st.stop()

# LLM_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
LLM_MODEL = "moonshotai/kimi-k2"
INDEX_NAME = "ubl-brain"

@st.cache_resource(show_spinner=False)
def init_services():
    # 1. LLM
    llm = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={"HTTP-Referer": "https://ubl-brain.streamlit.app", "X-Title": "UBL Brain"}
    )
    
    # 2. Embeddings (Runs in memory)
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Pinecone (Cloud Database)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)

    return llm, embedder, index

llm_client, embedder, index = init_services()

# ==========================================
# 4. INTELLIGENCE FUNCTIONS
# ==========================================
def extract_metadata(text):
    system_prompt = """
    Extract metadata. Return ONLY valid JSON.
    Fields: "project" (default 'General'), "tags" (list of strings).
    """
    try:
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            max_tokens=200, temperature=0.1
        )
        raw = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        meta = json.loads(raw)
        if isinstance(meta.get("tags"), list): meta["tags"] = ", ".join(meta["tags"])
        return meta
    except:
        return {"project": "General", "tags": "General"}

def save_memory(text):
    meta = extract_metadata(text)
    now = datetime.datetime.now()
    meta["date"] = now.strftime("%Y-%m-%d %H:%M:%S")
    # Store the actual text in metadata too, so we can read it back
    meta["text"] = text 
    
    doc_id = str(uuid.uuid4())
    vector = embedder.encode(text).tolist()
    
    # Upload to Cloud
    index.upsert(vectors=[(doc_id, vector, meta)])
    return meta

def analyze_intent(query, project_filter=None):
    # 1. Convert query to vector
    query_vec = embedder.encode(query).tolist()
    
    # 2. Filter logic (Pinecone Syntax)
    filter_dict = {"project": {"$eq": project_filter}} if project_filter and project_filter != "All" else None

    # 3. Search Cloud
    results = index.query(
        vector=query_vec,
        top_k=5,
        include_metadata=True,
        filter=filter_dict
    )

    matches = results['matches']
    if not matches:
        return {"type": "message", "content": "📭 No memories found."}

    # 4. Build Context
    context_str = ""
    for m in matches:
        meta = m['metadata']
        context_str += f"ID: {m['id']} | Date: {meta.get('date')} | Text: {meta.get('text')}\n"

    # 5. Ask LLM
    system_prompt = f"""
    You are a Second Brain. Today: {datetime.datetime.now().strftime("%A, %B %d, %Y")}.
    
    Rules:
    1. If user wants to DELETE a log in context, return: `CONFIRM_DELETE: <ID> | <Summary>`
    2. Else, answer helpfuly based on context.
    """

    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXT:\n{context_str}\n\nUSER PROMPT: {query}"}
        ],
        max_tokens=500
    )
    
    content = response.choices[0].message.content.strip()
    
    if content.startswith("CONFIRM_DELETE:"):
        try:
            parts = content.split(":", 1)[1].split("|")
            return {"type": "confirm_delete", "id": parts[0].strip(), "summary": parts[1].strip()}
        except:
            return {"type": "message", "content": "❌ Error parsing deletion."}
            
    return {"type": "message", "content": content}

# ==========================================
# 5. UI COMPONENTS
# ==========================================

# Sidebar (Only visible after login)
with st.sidebar:
    st.title("🧠 UBL Brain")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.divider()
    
    # Fetch random/recent data for dashboard (Pinecone limitation: can't fetch all easily)
    # We query with a dummy vector to get recent items
    dummy_vec = [0.1] * 384
    try:
        stats = index.query(vector=dummy_vec, top_k=50, include_metadata=True)
        data_points = [m['metadata'] for m in stats['matches']]
        if data_points:
            df_all = pd.DataFrame(data_points)
            unique_projects = ["All"] + list(df_all['project'].unique())
        else:
            unique_projects = ["All"]
            df_all = pd.DataFrame()
    except:
        unique_projects = ["All"]
        df_all = pd.DataFrame()

    selected_project = st.selectbox("📂 Filter Context", unique_projects)

# Main UI
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 Access Granted. System Online."}]
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "🗂️ Recent Logs"])

with tab1:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_delete:
        with st.chat_message("assistant"):
            st.warning(f"⚠️ Delete: *{st.session_state.pending_delete['summary']}*?")
            c1, c2 = st.columns([1,5])
            if c1.button("Yes"):
                index.delete(ids=[st.session_state.pending_delete['id']])
                st.session_state.messages.append({"role": "assistant", "content": "🗑️ Deleted."})
                st.session_state.pending_delete = None
                st.rerun()
            if c2.button("No"):
                st.session_state.pending_delete = None
                st.rerun()

    if prompt := st.chat_input("Type '/log <your update>' OR ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        if prompt.lower().startswith("/log "):
            with st.spinner("Encrypting to Cloud..."):
                meta = save_memory(prompt[5:].strip())
                st.session_state.messages.append({"role": "assistant", "content": f"✅ Saved to {meta['project']}"})
                st.rerun()
        else:
            with st.spinner("Querying Database..."):
                res = analyze_intent(prompt, selected_project)
                if res["type"] == "message":
                    st.session_state.messages.append({"role": "assistant", "content": res["content"]})
                    st.rerun()
                elif res["type"] == "confirm_delete":
                    st.session_state.pending_delete = res
                    st.rerun()

with tab2:
    if not df_all.empty:
        fig = px.pie(df_all, names='project', title="Project Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log data to see analytics.")

with tab3:
    if not df_all.empty and 'text' in df_all.columns:
        st.dataframe(df_all[['date', 'project', 'text']], use_container_width=True)
    else:
        st.write("No recent logs fetched.")