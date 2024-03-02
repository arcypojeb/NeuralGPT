import os
import g4f
import json
import home
import websockets
import datetime
import asyncio
import sqlite3
import requests
import http.server
import socketserver
import fireworks.client
import streamlit as st
import streamlit.components.v1 as components
import gradio as gr
import home
from streamlit_modules import characterAI
from streamlit_modules import fireworksLlama2
from streamlit_modules import bingG4F
from streamlit_modules import chatGPT4F
from streamlit_modules import forefrontAI
from streamlit_modules import flowiseAgent
from streamlit_modules import chaindesk
from PyCharacterAI import Client
from websockets.sync.client import connect

client = Client()

servers = []
clients = []
inputs = []
outputs = []
used_ports = []
server_ports = []
client_ports = []

# Stop the WebSocket server
async def stop_websockets():    
    global server
    if server:
        # Close all connections gracefully
        await server.close()
        # Wait for the server to close
        await server.wait_closed()
        home.servers.clear()
        home.clients.clear()
        print("Stopping WebSocket server...")
    else:
        print("WebSocket server is not running.")

# Stop the WebSocket client
async def stop_client():
    global ws
    # Close the connection with the server
    await ws.close()
    home.clients.clear()    
    print("Stopping WebSocket client...")

async def main():

    st.set_page_config(layout="wide")       
    st.title("serverovnia")        

    if "server_ports" not in st.session_state:
        st.session_state['server_ports'] = ""
    if "client_ports" not in st.session_state:
        st.session_state['client_ports'] = ""
    if "servers" not in st.session_state:
        st.session_state['servers'] = ""
    if "clients" not in st.session_state:
        st.session_state['clients'] = ""
    if "gradio_Port" not in st.session_state:
        st.session_state.gradio_Port = "" 
    if "server" not in st.session_state:
        st.session_state.server = False    
    if "client" not in st.session_state:
        st.session_state.client = False
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "user_ID" not in st.session_state:
        st.session_state.user_ID = ""
    if "gradio_Port" not in st.session_state:
        st.session_state.gradio_Port = ""         
    if "forefront_api" not in st.session_state:
        st.session_state.forefront_api = ""    
    if "tokenChar" not in st.session_state:
        st.session_state.tokenChar = ""           
    if "charName" not in st.session_state:
        st.session_state.charName = ""
    if "character_ID" not in st.session_state:
        st.session_state.character_ID = "" 
    if "flow" not in st.session_state:
        st.session_state.flow = ""        
    if "agentID" not in st.session_state:
        st.session_state.agentID = "" 
    if "googleAPI" not in st.session_state:
        st.session_state.googleAPI = ""        
    if "cseID" not in st.session_state:
        st.session_state.cseID = ""                        
    if "server_state" not in st.session_state:
        st.session_state.server_state = "complete"
    if "client_state" not in st.session_state:
        st.session_state.client_state = "complete"                

    if "http_server" not in st.session_state:
        
        PORT = 8001
        Handler = http.server.SimpleHTTPRequestHandler
        st.session_state.http_server = PORT

        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("serving at port", PORT)
            httpd.serve_forever()    

    c1, c2 = st.columns(2)

    selectServ = st.selectbox("Select source", ("Fireworks", "Bing", "GPT-3,5", "Character.ai", "Forefront", "ChainDesk", "Flowise"))
    
    userInput = st.chat_input("Ask Agent") 

    with c1:
        websocketPort = st.number_input("Websocket server port", min_value=1000, max_value=9999, value=1000)   
        startServer = st.button("Start server")
        stopServer = st.button("Stop server")
        st.text("Server ports")
        serverPorts1 = st.empty()
        serverPorts = serverPorts1.status(label="websocket servers", state=st.session_state.server_state, expanded=False)
        serverPorts.write(home.servers)
    
    with c2:
        clientPort = st.number_input("Websocket client port", min_value=1000, max_value=9999, value=1000)
        runClient = st.button("Start client")
        stopClient = st.button("Stop client")        
        st.text("Client ports")
        clientPorts1 = st.empty()
        clientPorts = clientPorts1.status(label="websocket clients", state=st.session_state.client_state, expanded=False)
        clientPorts.write(home.clients)

    with st.sidebar:
        # WyĹ›wietlanie danych, ktĂłre mogÄ… byÄ‡ modyfikowane na rĂłĹĽnych stronach       
        st.text("Server ports")
        srv_status = st.empty()
        server_status1 = srv_status.status(label="websocket servers", state=st.session_state.server_state, expanded=True)
        server_status1.write(home.servers)
        if st.session_state.server == True:
            st.session_state.server_state = "running"
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state=st.session_state.server_state, expanded=True)
            server_status1.write(home.servers)

        st.text("Client ports")
        cli_status = st.empty()
        client_status1 = cli_status.status(label="websocket clients", state=st.session_state.client_state, expanded=True)
        client_status1.write(home.clients)
        if st.session_state.client == True:
            st.session_state.client_state = "running"
            cli_status.empty()
            client_status1 = cli_status.status(label="websocket clients", state=st.session_state.client_state, expanded=True)
            client_status1.write(home.clients)

    if stopServer:
        stop_websockets

    if stopClient:
        stop_client  

    if  selectServ == "Fireworks":

        fireworksAPI = st.text_input("Fireworks API") 
        
        if startServer:
            st.session_state.server = True
            fireworks.client.api_key = fireworksAPI
            st.session_state.api_key = fireworks.client.api_key
            srv_name1 = f"Fireworks Llama2 server port: {websocketPort}"
            home.servers.append(srv_name1)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers)            
            try:
                server = fireworksLlama2(fireworksAPI)                
                await server.start_server(websocketPort)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            fireworks.client.api_key = fireworksAPI
            st.session_state.api_key = fireworks.client.api_key
            cli_name1 = f"Fireworks Llama2 client port: {clientPort}"
            home.clients.append(cli_name1)
            cli_status.empty()
            client_status1 = cli_status.status(label=cli_name1, state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label=cli_name1, state="running", expanded=True)
            clientPorts.write(home.clients)            
            try:
                client = fireworksLlama2(fireworksAPI)                
                await client.startClient(clientPort)
                print(f"Connecting client on port {clientPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                

        if userInput:        
            print(f"User B: {userInput}")
            user_input = st.chat_message("human")
            user_input.markdown(userInput)
            fireworks1 = fireworksLlama2(fireworksAPI)
            response1 = await fireworks1.handleUser(userInput)
            print(response1)
            outputMsg = st.chat_message("ai") 
            outputMsg.markdown(response1)

    if selectServ == "Bing":

        if startServer:            
            st.session_state.server = True
            srv_name2 = f"Bing/Copilot server port: {websocketPort}"
            home.servers.append(srv_name2)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers) 
            try:      
                server1 = bingG4F()                
                await server1.start_server(websocketPort)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name2 = f"Bing/Copilot client port: {clientPort}"
            home.clients.append(cli_name2)
            cli_status.empty()
            client_status1 = cli_status.status(label=cli_name2, state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label=cli_name2, state="running", expanded=True)
            clientPorts.write(home.clients) 
            try:
                client1 = bingG4F()               
                await client1.startClient(clientPort)
                print(f"Connecting client on port {clientPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                

        if userInput:
            user_input1 = st.chat_message("human")
            user_input1.markdown(userInput)
            bing = bingG4F()
            response = await bing.handleUser(userInput)
            outputMsg1 = st.chat_message("ai") 
            outputMsg1.markdown(response)

    if selectServ == "GPT-3,5":
        
        if startServer:            
            st.session_state.server = True
            srv_name3 = f"GPT-3,5 server port: {websocketPort}"
            home.servers.append(srv_name3)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers) 
            try:      
                server2 = chatGPT4F()                
                await server2.start_server(websocketPort)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name3 = f"GPT-3,5 client port: {clientPort}"
            home.clients.append(cli_name3)
            cli_status.empty()
            client_status1 = cli_status.status(label="clients", state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label="clients", state="running", expanded=True)
            clientPorts.write(home.clients) 
            try:
                client2 = chatGPT4F()               
                await client2.startClient(clientPort)
                print(f"Connecting client on port {clientPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                

        if userInput:
            user_input1 = st.chat_message("human")
            user_input1.markdown(userInput)
            gpt = chatGPT4F()
            response = await gpt.handleUser(userInput)
            outputMsg1 = st.chat_message("ai") 
            outputMsg1.markdown(response)

    if selectServ == "Chaqracter.ai":

        characterToken = st.text_input("Character AI user token") 
        characterID = st.text_input("Your characters ID") 

        if startServer:
            st.session_state.server = True
            srv_name4 = f"Character.ai server port: {websocketPort}"
            home.servers.append(srv_name4)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers)
            try:
                server4 = characterAI(characterToken)                   
                await server4.start_server(characterID, websocketPort)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name4 = f"Character.ai client port: {clientPort}"
            home.clients.append(cli_name4)
            cli_status.empty()
            client_status1 = cli_status.status(label="clients", state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label="clients", state="running", expanded=True)
            clientPorts.write(home.clients)         
            try:
                client4 = characterAI(characterToken)    
                await client4.startClient(characterID, clientPort)
                print(f"Connecting client on port {clientPort}...")
                st.session_state.client = client
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                

        if userInput:
            print(f"User B: {userInput}")
            user_input1 = st.chat_message("human")
            user_input1.markdown(userInput)
            character = characterAI(characterToken)
            response1 = await character.handleUser(characterID, userInput)            
            outputMsg1 = st.chat_message("ai") 
            outputMsg1.markdown(response1)
            print(response1)
            return response1

    if selectServ == "Forefront":

        forefrontAPI = st.text_input("Forefront API") 

        if startServer:
            st.session_state.server = True            
            srv_name5 = f"Forefront AI server port: {websocketPort}"
            home.servers.append(srv_name5)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers)            
            try:
                server5 = forefrontAI(forefrontAPI)                
                await server5.start_server(websocketPort)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name5 = f"Forefront AI client port: {clientPort}"
            home.clients.append(cli_name5)
            cli_status.empty()
            client_status1 = cli_status.status(label="clients", state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label="clients", state="running", expanded=True)
            clientPorts.write(home.clients)            
            try:
                client = forefrontAI(forefrontAPI)                
                await client.startClient(clientPort)
                print(f"Connecting client on port {clientPort}...")
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                     

        if userInput:        
            print(f"User B: {userInput}")
            user_input = st.chat_message("human")
            user_input.markdown(userInput)
            forefront = forefrontAI(forefrontAPI)
            response1 = await forefront.handleUser(userInput)
            print(response1)
            outputMsg = st.chat_message("ai") 
            outputMsg.markdown(response1)

    if selectServ == "ChainDesk":

        agentID = st.text_input("Agent ID")

        if userInput:
            user_input6 = st.chat_message("human")
            user_input6.markdown(userInput)
            chaindesk1 = chaindesk(agentID)
            response6 = await chaindesk1.handleUser(userInput)
            outputMsg = st.chat_message("ai")
            outputMsg.markdown(response6)

        if startServer:
            st.session_state.server = True            
            srv_name6 = f"Chaindesk agent server port: {websocketPort}"
            home.servers.append(srv_name6)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers)      
            try:      
                server6 = chaindesk(agentID)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await server6.start_server(websocketPort)
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name6 = f"Chaindesk agent client port: {clientPort}"
            home.clients.append(cli_name6)
            cli_status.empty()
            client_status1 = cli_status.status(label="clients", state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label="clients", state="running", expanded=True)
            clientPorts.write(home.clients)        
            try:
                client6 = chaindesk(agentID)  
                print(f"Connecting client on port {clientPort}...")
                await client6.startClient(clientPort)
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")  

    if selectServ == "Flowise":
        
        flow = st.text_input("flow ID")

        if userInput:
            user_input6 = st.chat_message("human")
            user_input6.markdown(userInput)
            flowise = flowiseAgent(flow)
            response6 = await flowise.handleUser(userInput)
            outputMsg = st.chat_message("ai")
            outputMsg.markdown(response6)

        if startServer:
            st.session_state.server = True            
            srv_name7 = f"Flowise agent server port: {websocketPort}"
            home.servers.append(srv_name7)
            srv_status.empty()
            server_status1 = srv_status.status(label="websocket servers", state="running", expanded=True)
            server_status1.write(home.servers)
            serverPorts1.empty()
            serverPorts = serverPorts1.status(label="websocket servers", state="running", expanded=True)
            serverPorts.write(home.servers)   
            try:      
                server7 = flowiseAgent(flow)
                print(f"Starting WebSocket server on port {websocketPort}...")
                await server7.start_server(websocketPort)
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")

        if runClient:
            st.session_state.client = True
            cli_name7 = f"Chaindesk agent client port: {clientPort}"
            home.clients.append(cli_name7)
            cli_status.empty()
            client_status1 = cli_status.status(label="clients", state="running", expanded=True)
            client_status1.write(home.clients)
            clientPorts1.empty()            
            clientPorts = clientPorts1.status(label="clients", state="running", expanded=True)
            clientPorts.write(home.clients)     
            try:
                client7 =flowiseAgent(flow)
                print(f"Connecting client on port {clientPort}...")
                await client7.startClient()
                await asyncio.Future()

            except Exception as e:
                print(f"Error: {e}")                          

asyncio.run(main())            