import os
import streamlit_modules
import asyncio
import http.server
import socketserver
import streamlit as st

servers = []
clients = []
inputs = []
outputs = []
states = []
used_ports = []
connections = []
server_ports = []
client_ports = []

st.set_page_config(layout="wide")

if "http_server" not in st.session_state:
    
    PORT = 8001
    Handler = http.server.SimpleHTTPRequestHandler
    st.session_state.http_server = PORT

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("serving at port", PORT)
        httpd.serve_forever()

if "client_state" not in st.session_state:
    st.session_state.client_state = "complete"
if "server_state" not in st.session_state:
    st.session_state.server_state = "complete"          

# Wyświetlanie danych, które mogą być modyfikowane na różnych stronach
server_status1 = st.status(label="websocket servers", state=st.session_state.server_state, expanded=False)
server_status = st.sidebar.status(label="websocket servers", state=st.session_state.server_state, expanded=False)
server_status1.write(streamlit_modules.servers)
server_status.write(streamlit_modules.servers)

client_status1 = st.status(label="websocket clients", state=st.session_state.client_state, expanded=False)
client_status = st.sidebar.status(label="websocket clients", state=st.session_state.client_state, expanded=False)
client_status1.write(streamlit_modules.clients)
client_status.write(streamlit_modules.clients)

async def main():

    # Inicjalizacja danych w st.session_state
    if "server_ports" not in st.session_state:
        st.session_state['server_ports'] = ""
    if "client_ports" not in st.session_state:
        st.session_state["client_ports"] = ""
    if "servers" not in st.session_state:
        st.session_state['servers'] = streamlit_modules.servers
    if "clients" not in st.session_state:
        st.session_state["clients"] = streamlit_modules.clients
    if "user_ID" not in st.session_state:
        st.session_state.user_ID = ""
    if "gradio_Port" not in st.session_state:
        st.session_state.gradio_Port = ""              
    if "googleAPI" not in st.session_state:
        st.session_state.googleAPI = ""
    if "cseID" not in st.session_state:
        st.session_state.cseID = ""
    if "server" not in st.session_state:
        st.session_state.server = False    
    if "client" not in st.session_state:
        st.session_state.client = False
    if "client_state" not in st.session_state:
        st.session_state.client_state = "complete"
    if "server_state" not in st.session_state:
        st.session_state.server_state = "complete"        


    st.title("NeuralGPT")

    c1, c2 = st.columns(2)

    with c1:
        st.text("Server ports")
        srv_state = st.empty()
        server_status1 = srv_state.status(label="active servers", state=st.session_state.client_state, expanded=False)
        if st.session_state.server == True:
            st.session_state.server_state = "running"
            server_status1.update(state=st.session_state.client_state, expanded=True)
            server_status1.write(streamlit_modules.servers)

    with c2:   
        st.text("Client ports")        
        cli_state = st.empty()
        client_status1 = cli_state.status(label="active clients", state=st.session_state.client_state, expanded=False)
        if st.session_state.client == True:    
            st.session_state.client_state = "running"
            client_status1.update(state=st.session_state.client_state, expanded=True)
            client_status1.write(streamlit_modules.clients)

    with st.sidebar:

        srv_sidebar = st.empty()
        cli_sidebar = st.empty()        
        server_status = srv_sidebar.status(label="los serveros", state=st.session_state.client_state, expanded=True)
        client_status = cli_sidebar.status(label="los clientos", state=st.session_state.client_state, expanded=False)
        server_status.write(streamlit_modules.servers)
        client_status.write(streamlit_modules.clients)

        if st.session_state.server == True:
            srv_sidebar.empty()
            st.session_state.server_state = "running"
            server_status = srv_sidebar.status(label="servers", state=st.session_state.client_state, expanded=True)
            server_status.write(streamlit_modules.servers)

        if st.session_state.client == True:
            cli_sidebar.empty()
            st.session_state.client_state = "running"
            client_status = cli_sidebar.status(label="clients", state=st.session_state.client_state, expanded=True)
            client_status.write(streamlit_modules.clients)

# Uruchomienie aplikacji
asyncio.run(main())