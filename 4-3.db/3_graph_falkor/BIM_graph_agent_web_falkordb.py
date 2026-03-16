"""
BIM Graph Agent Web Interface - Simple ChatBot Style (FalkorDB)

Streamlit web app for BIM data querying using natural language with FalkorDB.
Dark mode chatbot interface with minimal design.

Usage: streamlit run BIM_graph_agent_web_falkordb.py
Contact: Taewook Kang (laputa99999@gmail.com)
"""

import streamlit as st
import sys
from pathlib import Path
from BIM_graph_agent_falkordb import BIMGraphAgent, load_environment

# Configure page
st.set_page_config(
    page_title="BIM ChatBot (FalkorDB)",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Add project source to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Dark theme CSS
st.markdown("""
<style>
.stApp {
    background-color: #1a1a1a;
    color: #ffffff;
}
.chat-container {
    background-color: #2d2d30;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    min-height: 100px;
    max-height: 400px;
    overflow-y: auto;
}
.user-msg {
    background-color: #007acc;
    color: white;
    padding: 10px 15px;
    border-radius: 15px 15px 5px 15px;
    margin: 5px 0 5px auto;
    max-width: 80%;
    text-align: right;
}
.bot-msg {
    background-color: #404040;
    color: #ffffff;
    padding: 10px 15px;
    border-radius: 15px 15px 15px 5px;
    margin: 5px auto 5px 0;
    max-width: 80%;
}
.stTextInput > div > div > input {
    background-color: #404040;
    color: #ffffff;
    border: 1px solid #555555;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'last_processed' not in st.session_state:
    st.session_state.last_processed = ""

# Initialize BIM Graph Agent
@st.cache_resource
def get_agent():
    try:
        env_config = load_environment()
        agent = BIMGraphAgent()
        
        if agent.setup_falkordb(
            host=env_config['host'],
            port=env_config['port'],
            username=env_config['username'],
            password=env_config['password'],
            graph_name=env_config['graph_name']
        ):
            return agent
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
    return None

# Main interface
st.title("BIM Graph Agent (FalkorDB)")
st.caption("AI-powered BIM data query system")

# Get agent instance
if not st.session_state.initialized:
    with st.spinner("Initializing agent..."):
        st.session_state.agent = get_agent()
        st.session_state.initialized = True
        if st.session_state.agent:
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Hello! Ask me about your BIM data. Examples: List all windows with their properties, What is the area of room A204, Show me all doors in the project, What are the properties of room A204"
            })

# Only show chat interface if agent is initialized
if st.session_state.initialized and st.session_state.agent:
    # Chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            # Check if message needs markdown rendering
            if msg.get("format") == "markdown":
                # Display markdown content with proper formatting
                st.markdown(msg["content"], unsafe_allow_html=True)
            else:
                # Regular text display
                st.markdown(f'<div class="bot-msg">{msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Input area
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "Your question:", 
            value=st.session_state.user_input,
            placeholder="Ask about BIM data...", 
            label_visibility="collapsed",
            key="user_input_field"
        )
    with col2:
        send_btn = st.button("Send", type="primary")

    # Handle input when Send button is clicked OR Enter key is pressed (text_input changed)
    # Check if user_input differs from stored value and hasn't been processed yet
    input_changed = (user_input != st.session_state.user_input) and (len(user_input.strip()) > 0) and (user_input != st.session_state.last_processed)
    
    if (send_btn and user_input.strip()) or input_changed:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Mark this query as processed to prevent re-processing
        st.session_state.last_processed = user_input
        
        # Process query
        with st.spinner("Processing..."):
            try:
                response = st.session_state.agent.process_query(user_input)
                # Store response with markdown formatting support
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "format": "markdown"  # Mark as markdown content
                })
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        
        # Clear input by setting session state to empty
        st.session_state.user_input = ""
        
        # Refresh page to show new messages and cleared input
        st.rerun()
else:
    st.error("Agent not initialized. Please refresh the page.")
