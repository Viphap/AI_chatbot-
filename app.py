import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime
import plotly.graph_objects as go
import time
from concurrent.futures import ThreadPoolExecutor
from chatbot_core import NewsenseClient, chatbot, analyze_data
import google.generativeai as genai
import difflib

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Chatbot - Newsense",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CACHED RESOURCES (FOR SPEED) ---
@st.cache_resource
def get_ai_model(api_key):
    try:
        if not api_key or api_key == "YOUR_KEY":
            st.error("❌ Chưa nhập Gemini API Key trong config.json")
            return None, None
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Thử gọi một câu lệnh cực ngắn để check key có sống không
        _ = model.generate_content("hi", generation_config={"max_output_tokens": 1})
        return model, "Gemini 1.5 Flash"
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            st.error("❌ API Key không có quyền truy cập (Permission Denied)")
        elif "429" in error_msg:
            st.error("⚠️ Quá tải (Rate limit exceeded). Đang dùng bản Free?")
        elif "API_KEY_INVALID" in error_msg:
            st.error("❌ API Key không hợp lệ. Vui lòng kiểm tra lại AI Studio.")
        else:
            st.error(f"❌ Lỗi khởi tạo: {error_msg}")
        return None, None

@st.cache_resource
def get_newsense_client(base_url, user, password):
    try:
        return NewsenseClient(base_url, user, password)
    except:
        return None

@st.cache_data
def get_cached_device_map(_client):
    try:
        devices = _client.get_devices()
        return {d['name']: d['id'] for d in devices}
    except:
        return {}

# --- INITIALIZE SESSION STATE ---
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'all_chat_history' not in st.session_state: st.session_state.all_chat_history = []
if 'kg_df' not in st.session_state: st.session_state.kg_df = pd.DataFrame()
if 'active_page' not in st.session_state: st.session_state.active_page = "💬 Chatbot"

# --- HELPER FUNCTIONS ---
def load_knowledge_graph(path):
    if os.path.exists(path):
        return pd.read_excel(path)
    return pd.DataFrame()

def save_chat_history_by_date(entry):
    try:
        history_dir = "chat_history"
        if not os.path.exists(history_dir): os.makedirs(history_dir)
        date_str = datetime.fromisoformat(entry['timestamp']).strftime("%Y-%m-%d")
        file_path = os.path.join(history_dir, f"history_{date_str}.json")
        
        daily_history = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                daily_history = json.load(f)
        
        daily_history.append(entry)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(daily_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Save error: {e}")

def load_all_history():
    all_history = []
    history_dir = "chat_history"
    if os.path.exists(history_dir):
        for filename in os.listdir(history_dir):
            if filename.endswith(".json"):
                with open(os.path.join(history_dir, filename), 'r', encoding='utf-8') as f:
                    all_history.extend(json.load(f))
    return sorted(all_history, key=lambda x: x.get('timestamp', ''), reverse=True)

def fetch_data_parallel(devices, start, end):
    client = st.session_state.newsense_client
    dev_map = st.session_state.device_map

    def fetch_single(info):
        d_name = info.get("Device")
        v_name = info.get("Tên biến")
        d_id = dev_map.get(d_name) or dev_map.get(difflib.get_close_matches(d_name, dev_map.keys(), n=1, cutoff=0.7)[0] if difflib.get_close_matches(d_name, dev_map.keys()) else None)
        if d_id:
            try:
                df = client.get_timeseries(d_id, v_name, start, end)
                if not df.empty:
                    return {"label": f"{info.get('Tên thiết bị', d_name)} ({v_name})", "data": df, "v": v_name}
            except: pass
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        return [r for r in list(executor.map(fetch_single, devices)) if r]

# --- UI PAGES ---
def chatbot_interaction_page():
    st.title("💬 Chatbot Interaction")
    st.divider()

    for i, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg['role']):
            if msg['role'] == 'user':
                st.write(msg['content'])
            else:
                try:
                    res = json.loads(msg['content'])
                    st.json(res)
                    devices = res.get("devices", [])
                    if devices and res.get("start_date"):
                        data = fetch_data_parallel(devices, res["start_date"], res["end_date"])
                        if data:
                            if res.get("is_latest"):
                                cols = st.columns(len(data))
                                for j, item in enumerate(data):
                                    latest = item['data'].iloc[-1]
                                    cols[j].metric(item['label'], f"{latest['value']:.2f}")
                            
                            if st.toggle("Show Charts", value=True, key=f"tgl_{i}"):
                                for idx, item in enumerate(data):
                                    fig = go.Figure(go.Scatter(x=item['data']['ts'], y=item['data']['value'], name=item['label']))
                                    st.plotly_chart(fig, use_container_width=True, key=f"ch_{i}_{idx}")
                                
                                if st.button("🔍 AI Analysis", key=f"an_btn_{i}"):
                                    with st.spinner("Analyzing..."):
                                        st.info(analyze_data(data, st.session_state.chat_history[i-1]['content'], st.session_state.gemini_model))
                except: st.write(msg['content'])

    if prompt := st.chat_input("Hỏi tôi về dữ liệu thiết bị..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("Gemini 1.5 Flash is thinking..."):
            result, updated_hist = chatbot(prompt, st.session_state.kg_df, st.session_state.chat_history, st.session_state.gemini_model)
            if result:
                st.session_state.chat_history = updated_hist
                save_chat_history_by_date({"timestamp": datetime.now().isoformat(), "query": prompt, "response": result})
        st.rerun()

def history_page():
    st.title("📜 Chat History")
    history = load_all_history()
    if not history:
        st.info("No history found.")
        return
    
    search = st.text_input("🔍 Search queries...")
    for entry in history:
        if search.lower() in entry['query'].lower():
            with st.expander(f"🕒 {entry['timestamp'][:16]} | {entry['query'][:50]}..."):
                st.write(f"**Query:** {entry['query']}")
                st.json(entry['response'])

def kg_editor_page(config):
    st.title("📊 Knowledge Graph Editor")
    if st.session_state.kg_df.empty:
        st.session_state.kg_df = load_knowledge_graph(config['knowledge_graph']['path'])
    
    edited_df = st.data_editor(st.session_state.kg_df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save Knowledge Graph"):
        edited_df.to_excel(config['knowledge_graph']['path'], index=False)
        st.session_state.kg_df = edited_df
        st.success("Saved!")

# --- MAIN APP ---
def main():
    config = {
        "api": {"gemini_api_key": "YOUR_KEY", "base_url": "URL", "tb_user": "USER", "tb_pass": "PASS"},
        "knowledge_graph": {"path": "knowledge_graph.xlsx"}
    }
    # In real use, load from your config.json
    try:
        with open('config.json', 'r') as f: config = json.load(f)
    except: pass

    # Initialization
    model, m_name = get_ai_model(config['api']['gemini_api_key'])
    client = get_newsense_client(config['api']['base_url'], config['api']['tb_user'], config['api']['tb_pass'])
    
    if model and client:
        st.session_state.gemini_model = model
        st.session_state.newsense_client = client
        st.session_state.device_map = get_cached_device_map(client)
    else:
        st.error("Model or Client failed to initialize. Check config.json")
        return

    # Sidebar
    with st.sidebar:
        st.title("🤖 AI Chatbot")
        st.success(f"Model: {m_name}")
        st.divider()
        if st.button("💬 Chatbot", use_container_width=True): st.session_state.active_page = "💬 Chatbot"
        if st.button("📜 History", use_container_width=True): st.session_state.active_page = "📜 History"
        if st.button("📊 KG Editor", use_container_width=True): st.session_state.active_page = "📊 KG Editor"
        st.divider()
        if st.button("🗑️ Clear Current Chat"):
            st.session_state.chat_history = []
            st.rerun()

    # Routing
    if st.session_state.active_page == "💬 Chatbot": chatbot_interaction_page()
    elif st.session_state.active_page == "📜 History": history_page()
    elif st.session_state.active_page == "📊 KG Editor": kg_editor_page(config)

if __name__ == "__main__":
    main()