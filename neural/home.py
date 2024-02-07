import asyncio
import streamlit as st

servers = {}
inputs = []
outputs = []
used_ports = []
server_ports = []
client_ports = []

st.set_page_config(layout="wide")

async def main():
    
    st.session_state.update(st.session_state)

    if "server_ports" not in st.session_state:
        st.session_state['server_ports'] = ""
    if "client_ports" not in st.session_state:
        st.session_state['client_ports'] = ""
    if "user_ID" not in st.session_state:
        st.session_state.user_ID = ""
    if "servers" not in st.session_state:
        st.session_state.servers = None
    if "server" not in st.session_state:
        st.session_state.server = None    
    if "clients" not in st.session_state:
        st.session_state.clients = None    
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "tokenChar" not in st.session_state:
        st.session_state.tokenChar = None              
    if "charName" not in st.session_state:
        st.session_state.charName = None
    if "character_ID" not in st.session_state:
        st.session_state.character_ID = None 

    if  st.session_state.server == None:
        st.session_state.active_page = 'clients'
    else: st.session_state.active_page = 'servers'

    st.title("NeuralGPT")
        
    serverPorts = st.sidebar.container(border=True)
    serverPorts.markdown(st.session_state['server_ports'])
    st.sidebar.text("Client ports")
    clientPorts = st.sidebar.container(border=True)
    clientPorts.markdown(st.session_state['client_ports'])
    st.sidebar.text("Charavter.ai ID")
    user_id = st.sidebar.container(border=True)
    user_id.markdown(st.session_state.user_ID)

asyncio.run(main())