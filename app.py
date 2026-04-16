# ==========================================
# IMPORTS
# ==========================================
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
    page_title="ubl Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
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
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    env_pass = os.getenv("APP_PASSWORD")
    input_pass = st.session_state.password_input
    if env_pass and input_pass.strip() == env_pass.strip():
        st.session_state.authenticated = True
    else:
        st.error("⛔ Incorrect Password")

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🧠 ubl Brain Login</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.text_input("Enter Access Code", type="password", key="password_input", on_change=check_password)
    st.stop()

# ==========================================
# 3. SETUP CLOUD SERVICES
# ==========================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not OPENROUTER_API_KEY or not PINECONE_API_KEY:
    st.error("⚠️ API Keys missing. Check .env or Streamlit Secrets.")
    st.stop()

LLM_MODEL = "moonshotai/kimi-k2"
INDEX_NAME = "ubl-brain"

@st.cache_resource(show_spinner=False)
def init_services():
    llm = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://ubl-brain.streamlit.app",
            "X-Title": "ubl Brain"
        }
    )
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    return llm, embedder, index

llm_client, embedder, index = init_services()

# ==========================================
# 4. INTELLIGENCE FUNCTIONS
# ==========================================
def clear_all_memory():
    try:
        index.delete(delete_all=True)
        return True
    except Exception as e:
        st.error(f"Error clearing memory: {e}")
        return False

def extract_metadata(text):
    system_prompt = (
        "Extract metadata. Return ONLY valid JSON. "
        "Fields: 'project' (default 'General'), 'tags' (list of strings)."
    )
    try:
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=200, temperature=0.1
        )
        raw = response.choices[0].message.content.replace("json", "").replace("", "").strip()
        meta = json.loads(raw)
        if isinstance(meta.get("tags"), list):
            meta["tags"] = ", ".join(meta["tags"])
        return meta
    except:
        return {"project": "General", "tags": "General"}

def save_memory(text):
    meta = extract_metadata(text)
    now = datetime.datetime.now()
    meta["date"] = now.strftime("%Y-%m-%d %H:%M:%S")
    meta["text"] = text
    doc_id = str(uuid.uuid4())
    vector = embedder.encode(text).tolist()
    index.upsert(vectors=[(doc_id, vector, meta)])
    return meta

def analyze_intent(query, project_filter=None):
    query_vec = embedder.encode(query).tolist()
    filter_dict = {"project": {"$eq": project_filter}} if project_filter and project_filter != "All" else None
    results = index.query(vector=query_vec, top_k=5, include_metadata=True, filter=filter_dict)
    matches = results['matches']
    if not matches:
        return {"type": "message", "content": "📭 No memories found."}

    context_str = "\n".join([
        f"ID: {m['id']} | Date: {m['metadata'].get('date')} | Text: {m['metadata'].get('text')}"
        for m in matches
    ])

    system_prompt = (
        "You are a Second Brain. Rules: "
        "If user wants to DELETE a log, return: `CONFIRM_DELETE: <ID> | <Summary>`. "
        "Else, answer helpfully."
    )

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
with st.sidebar:
    st.title("🧠 ubl Brain")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()
    st.subheader("⚙️ Maintenance")
    if "confirm_clear" not in st.session_state:
        st.session_state.confirm_clear = False

    if st.button("🗑️ Clear Entire Database"):
        st.session_state.confirm_clear = True

    if st.session_state.confirm_clear:
        st.warning("Are you sure? Irreversible!")
        if st.button("Confirm WIPE"):
            if clear_all_memory():
                st.success("Database wiped.")
                st.session_state.confirm_clear = False
                st.rerun()
        if st.button("Cancel"):
            st.session_state.confirm_clear = False
            st.rerun()
    st.divider()

try:
    stats = index.query(vector=[0.1]*384, top_k=50, include_metadata=True)
    data_points = [m['metadata'] for m in stats['matches']]
    df_all = pd.DataFrame(data_points) if data_points else pd.DataFrame()
    unique_projects = ["All"] + list(df_all['project'].unique()) if not df_all.empty else ["All"]
except:
    unique_projects = ["All"]
    df_all = pd.DataFrame()

selected_project = st.selectbox("📂 Filter Context", unique_projects)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 System Online."}]
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
            meta = save_memory(prompt[5:].strip())
            st.session_state.messages.append({"role": "assistant", "content": f"✅ Saved to {meta['project']}"} )
            st.rerun()
        else:
            res = analyze_intent(prompt, selected_project)
            if res["type"] == "message":
                st.session_state.messages.append({"role": "assistant", "content": res["content"]})
                st.rerun()
            elif res["type"] == "confirm_delete":
                st.session_state.pending_delete = res
                st.rerun()

with tab2:
    if not df_all.empty:
        st.plotly_chart(px.pie(df_all, names='project', title="Project Distribution"), use_container_width=True)
    else:
        st.info("No data.")

with tab3:
    if not df_all.empty:
        st.dataframe(df_all[['date', 'project', 'text']], use_container_width=True)
