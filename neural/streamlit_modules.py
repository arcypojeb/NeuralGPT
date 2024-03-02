import streamlit as st
import datetime
import asyncio
import sqlite3
import threading
import g4f
import json
import requests
import home
import websockets
import streamlit as st
import fireworks.client
import gradio as gr
from forefront import ForefrontClient
from PyCharacterAI import Client

servers = []
clients = []
inputs = []
outputs = []
used_ports = []
server_ports = []
client_ports = []    


class chaindesk:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, agentID):

        self.agentID = agentID
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Chaindesk", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Chaindesk", state=st.session_state.client_state, expanded=False)
    

    async def askChaindesk(self, question):
        
        if "agentID" not in st.session_state:
            st.session_state.agentID = self.agentID

        url = f"https://api.chaindesk.ai/agents/{self.agentID}/query"        
        payload = {
            "query": question
        }        
        headers = {
            "Authorization": "Bearer fe77e704-bc5a-4171-90f2-9d4b0d4ac942",
            "Content-Type": "application/json"
        }
        try:            
            response = requests.request("POST", url, json=payload, headers=headers)

            response_text = response.text
            responseJson = json.loads(response_text)
            answerTxt = responseJson["answer"]
            answer = f"Chaindesk agent: {answerTxt}"
            print(answer)
            return answer

        except Exception as e:
            print(e)

    async def handlerChaindesk(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name6, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name6, state="running", expanded=True)
        self.state.write(clients)
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)               
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:
                response = await self.askChaindesk(message)
                serverResponse = f"Chaindesk server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)                    
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                st.session_state.server_state = "complete"
                continue

            except websockets.exceptions.ConnectionClosedError as e:
                print(f"Connection closed: {e}")

            except Exception as e:
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):        
        uri = f'ws://localhost:{clientPort}'
        self.cli_name6 = f"Chaindesk agent client port: {clientPort}"
        clients.append(self.cli_name6)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name6, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name6, state="running", expanded=True)
        self.state.write(servers)        
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)                      
                try:
                    response = await self.askChaindesk(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)                          
                    await websocket.send(res1)
                    continue

                except websockets.ConnectionClosed:
                    print("client disconnected")
                    continue

                except Exception as e:
                    print(f"Error: {e}")

    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askChaindesk(question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}") 

    async def start_server(self, serverPort):
        self.srv_name6 = f"Chaindesk agent server port: {serverPort}"
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name6, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name6, state="running", expanded=True)
        self.state.write(clients)        
        servers.append(self.srv_name6)
        self.server = await websockets.serve(
            self.handlerChaindesk,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            servers.remove(self.srv_name6)
            clients.clear()
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    def run_client(self):
        # Get the asyncio event loop
        loop = asyncio.new_event_loop()
        # Set the event loop as the current one
        asyncio.set_event_loop(loop)
        # Run the client until it is stopped
        loop.run_until_complete(self.client())

    async def stop_client(self):
        global ws
        clients.remove(self.cli_name6)
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

class flowiseAgent:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, flowID):

        self.flow = flowID
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Flowise", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Flowise agent", state=st.session_state.client_state, expanded=False)
    
    async def askFlowise(self, question):

        API_URL = f"http://localhost:3000/api/v1/prediction/{self.flow}"        
        try:
            def query(payload):
                response = requests.post(API_URL, json=payload)
                return response.json()
                
            response = query({
                "question": question,
            })   

            print(response)
            responseTxt = response["text"]
            answer = f"Flowise agent: {responseTxt}"
            print(answer)            
            return answer

        except Exception as e:
            print(e)

    async def handlerFlowise(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name6, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name6, state="running", expanded=True)
        self.state.write(clients)        
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)              
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:
                response = await self.askFlowise(message)
                serverResponse = f"server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)                    
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                st.session_state.server_state = "complete"
                continue

            except websockets.exceptions.ConnectionClosedError as e:
                clients.remove(self.cli_name7)
                print(f"Connection closed: {e}")

            except Exception as e:
                clients.remove(self.cli_name7)
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name7 = f"Flowise client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'        
        clients.append(self.cli_name7)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name7, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name7, state="running", expanded=True)
        self.state.write(servers)              
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)                     
                try:
                    response = await self.askFlowise(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)                       
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    clients.remove(self.cli_name7)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    clients.remove(self.cli_name7)
                    print(f"Error: {e}")

    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askFlowise(question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}") 

    async def start_server(self, serverPort):
        self.srv_name7 = f"Flowise agent server port: {serverPort}"
        servers.append(self.srv_name7)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name7, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name7, state="running", expanded=True)
        self.state.write(clients)         
        self.server = await websockets.serve(
            self.handlerFlowise,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            servers.remove(self.srv_name7)
            clients.clear()
            self.server.close()
            await self.server.wait_closed()
            self.cont.empty()
            self.stat.empty()                          
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    def run_client(self):
        # Get the asyncio event loop
        loop = asyncio.new_event_loop()
        # Set the event loop as the current one
        asyncio.set_event_loop(loop)
        # Run the client until it is stopped
        loop.run_until_complete(self.client())

    async def stop_client(self):
        global ws
        clients.remove(self.cli_name7)
        self.cont.empty()
        self.stat.empty()                      
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")


class forefrontAI:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, forefrontAPI):

        self.forefrontAPI = forefrontAPI
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Forefront AI", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Forefront AI", state=st.session_state.client_state, expanded=False)
 
    async def askForefront(self, question):

        ff = ForefrontClient(api_key=self.forefrontAPI)        
        system_instruction = "You are now integrated with a local instance of a hierarchical cooperative multi-agent framework called NeuralGPT"
        try:
            # Connect to the database and get the last 30 messages
            db = sqlite3.connect('chat-hub.db')
            cursor = db.cursor()
            cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 3")
            messages = cursor.fetchall()
            messages.reverse()

            # Extract user inputs and generated responses from the messages
            past_user_inputs = []
            generated_responses = []
            for message in messages:
                if message[1] == 'server':
                    past_user_inputs.append(message[2])
                else:
                    generated_responses.append(message[2])

            last_msg = past_user_inputs[-1]
            last_response = generated_responses[-1]
            message = f'{{"client input: {last_msg}"}}'
            response = f'{{"server answer: {last_response}"}}' 

            # Construct the message sequence for the chat model
            response = ff.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    *[{"role": "user", "content": past_user_inputs[-1]}],
                    *[{"role": "assistant", "content": generated_responses[-1]}],
                    {"role": "user", "content": question}
                ],
                stream=False,
                model="forefront/neural-chat-7b-v3-1-chatml",  # Replace with the actual model name
                temperature=0.5,
                max_tokens=500,
            )
            
            response_text = response.choices[0].message # Corrected indexing
            answer = f"Foredfront AI: {response_text}"
            print(answer)
            return answer

        except Exception as e:
            print(e)

    async def handlerForefront(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(clients)           
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)                  
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:
                response = await self.askForefront(message)
                serverResponse = f"server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)                  
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                st.session_state.server_state = "complete"
                continue

            except websockets.exceptions.ConnectionClosedError as e:
                clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                              
                print(f"Connection closed: {e}")

            except Exception as e:
                clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                   
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name5 = f"Forefront AI client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        clients.append(self.cli_name7)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name5, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name5, state="running", expanded=True)
        self.state.write(servers)                     
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.askForefront(input_message)
                    res1 = f"Forefront client: {response}"
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    clients.remove(self.cli_name5)
                    self.cont.empty()
                    self.stat.empty()                       
                    print(f"Connection closed: {e}")

                except Exception as e:
                    clients.remove(self.cli_name5)
                    self.cont.empty()
                    self.stat.empty()                      
                    print(f"Error: {e}")


    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askForefront(question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}") 

    async def start_server(self, serverPort):
        self.srv_name5 = f"Forefront AI server port: {serverPort}"
        servers.append(self.srv_name7)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(clients)          
        self.server = await websockets.serve(
            self.handlerForefront,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            servers.remove(self.srv_name5)
            clients.clear()            
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    def run_client(self):
        # Get the asyncio event loop
        loop = asyncio.new_event_loop()
        # Set the event loop as the current one
        asyncio.set_event_loop(loop)
        # Run the client until it is stopped
        loop.run_until_complete(self.client())

    async def stop_client(self):
        global ws
        clients.remove(self.cli_name5)     
        self.cont.empty()
        self.stat.empty()                         
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

class chatGPT4F:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self):

        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="GPT-3,5", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="GPT-3,5", state=st.session_state.client_state, expanded=False)
 
    async def askGPT(self, question):
        system_instruction = "You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic."
        try:
            db = sqlite3.connect('chat-hub.db')
            cursor = db.cursor()
            cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 30")
            messages = cursor.fetchall()
            messages.reverse()

            past_user_inputs = []
            generated_responses = []

            for message in messages:
                if message[1] == 'client':
                    past_user_inputs.append(message[2])
                else:
                    generated_responses.append(message[2])
                        
            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.You,
                messages=[
                {"role": "system", "content": system_instruction},
                *[{"role": "user", "content": message} for message in past_user_inputs],
                *[{"role": "assistant", "content": message} for message in generated_responses],
                {"role": "user", "content": question}
                ])
            
            answer = f"GPT-3,5: {response}"
            print(answer)
            return answer
            
        except Exception as e:
            print(e)

    async def handlerGPT(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name4, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name4, state="running", expanded=True)
        self.state.write(clients)           
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)                  
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:
                response = await self.askGPT(message)
                serverResponse = f"server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)                     
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                st.session_state.server_state = "complete"
                continue

            except websockets.exceptions.ConnectionClosedError as e:
                clients.remove(self.cli_name4)
                print(f"Connection closed: {e}")

            except Exception as e:
                clients.remove(self.cli_name4)
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name4 = f"GPT-3,5 client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        clients.append(self.cli_name4)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name4, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name4, state="running", expanded=True)
        self.state.write(servers)          
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)                   
                try:
                    response = await self.askGPT(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)                            
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    clients.remove(self.cli_name4)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    clients.remove(self.cli_name4)
                    print(f"Error: {e}")

    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askGPT(question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}") 

    async def start_server(self, serverPort):
        self.srv_name4 = f"GPT-3,5 server port: {serverPort}"
        servers.append(self.srv_name4)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name4, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name4, state="running", expanded=True)
        self.state.write(clients)           
        self.server = await websockets.serve(
            self.handlerGPT,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            servers.remove(self.srv_name4)
            clients.clear()
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    def run_client(self):
        # Get the asyncio event loop
        loop = asyncio.new_event_loop()
        # Set the event loop as the current one
        asyncio.set_event_loop(loop)
        # Run the client until it is stopped
        loop.run_until_complete(self.client())

    async def stop_client(self):
        global ws
        clients.remove(self.cli_nam4)
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

class bingG4F:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self):

        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Bing/Copilot", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Bing/Copilot", state=st.session_state.client_state, expanded=False)
  
    async def askBing(self, question):
        system_instruction = "You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic."
        try:
            db = sqlite3.connect('chat-hub.db')
            cursor = db.cursor()
            cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 30")
            messages = cursor.fetchall()
            messages.reverse()

            past_user_inputs = []
            generated_responses = []

            for message in messages:
                if message[1] == 'server':
                    past_user_inputs.append(message[2])
                else:
                    generated_responses.append(message[2])
                        
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.gpt_4,
                provider=g4f.Provider.Bing,
                messages=[
                {"role": "system", "content": system_instruction},
                *[{"role": "user", "content": message} for message in past_user_inputs],
                *[{"role": "assistant", "content": message} for message in generated_responses],
                {"role": "user", "content": question}
                ])
        
            answer = f"Bing/Copilot: {response}"
            print(answer)
            return answer
            
        except Exception as e:
            print(e)
    

    async def handlerBing(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name3, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name3, state="running", expanded=True)
        self.state.write(clients)          
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:
                response = await self.askBing(message)
                serverResponse = f"server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                st.session_state.server_state = "complete"
                continue

            except websockets.exceptions.ConnectionClosedError as e:
                clients.remove(self.cli_name4)
                print(f"Connection closed: {e}")

            except Exception as e:
                clients.remove(self.cli_name4)
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name3 = f"Bing/Copilot client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'        
        clients.append(self.cli_name3)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name3, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name3, state="running", expanded=True)
        self.state.write(servers)     
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.askBing(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    clients.remove(self.cli_name3)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    clients.remove(self.cli_name3)
                    print(f"Error: {e}")

    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askBing(question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}") 

    async def start_server(self, serverPort):
        self.srv_name3 = f"Bing/Copilot server port: {serverPort}"
        servers.append(self.srv_name3)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name3, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name3, state="running", expanded=True)
        self.state.write(clients)         
        self.server = await websockets.serve(
            self.handlerBing,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    def run_client(self):
        # Get the asyncio event loop
        loop = asyncio.new_event_loop()
        # Set the event loop as the current one
        asyncio.set_event_loop(loop)
        # Run the client until it is stopped
        loop.run_until_complete(self.client())

    async def stop_client(self):
        global ws
        clients.remove(self.cli_name3)
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

class fireworksLlama2:
    
    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []

    def __init__(self, fireworksAPI):

        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.fireworksAPI = fireworksAPI
        self.server = None              

        self.stat = st.empty()
        self.state = self.stat.status(label="Fireworks Llama2", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Fireworks Llama2", state=st.session_state.client_state, expanded=False)
 
    async def chatFireworks(self, question):

        fireworks.client.api_key = self.fireworksAPI
        system_instruction = "You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic."
        try:
            # Connect to the database and get the last 30 messages
            db = sqlite3.connect('chat-hub.db')
            cursor = db.cursor()
            cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 10")
            messages = cursor.fetchall()
            messages.reverse()
                                            
            # Extract user inputs and generated responses from the messages
            past_user_inputs = []
            generated_responses = []

            for message in messages:
                if message[1] == 'client':
                    past_user_inputs.append(message[2])
                else:
                    generated_responses.append(message[2])

            # Prepare data to send to the chatgpt-api.shn.hk           
            response = fireworks.client.ChatCompletion.create(
                model="accounts/fireworks/models/llama-v2-7b-chat",
                messages=[
                {"role": "system", "content": system_instruction},
                *[{"role": "user", "content": input} for input in past_user_inputs],
                *[{"role": "assistant", "content": response} for response in generated_responses],
                {"role": "user", "content": question}
                ],
                stream=False,
                n=1,
                max_tokens=2500,
                temperature=0.5,
                top_p=0.7, 
                )

            answer = response.choices[0].message.content
            print(answer)
            return str(answer)
            
        except Exception as error:
            print("Error while fetching or processing the response:", error)
            return "Error: Unable to generate a response."

    # Define the handler function that will process incoming messages
    async def handlerFire(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(clients)  
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            # Receive a message from the client
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, message, timestamp))
            db.commit()
            try:            
                response = await self.chatFireworks(message)
                serverResponse = f"server: {response}"
                print(serverResponse)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(serverResponse)
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, serverResponse, timestamp))
                db.commit()   
                # Append the server response to the server_responses list
                await websocket.send(serverResponse)
                continue
               
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"Connection closed: {e}")

            except Exception as e:
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name2 = f"Forefront AI client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        clients.append(self.cli_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name2, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name2, state="running", expanded=True)
        self.state.write(servers)    
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.chatFireworks(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    clients.remove(self.cli_name2)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    clients.remove(self.cli_name2)
                    print(f"Error: {e}")

    async def handleUser(self, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.chatFireworks(question)
            response = f"Fireworks Llama2: {answer}"
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, response, timestamp))
            db.commit()
            return response

        except Exception as e:
            print(f"Error: {e}")        

    async def start_server(self, serverPort):
        self.srv_name2 = f"Fireworks Llama2 server port: {serverPort}"
        servers.append(self.srv_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(clients)                 
        self.server = await websockets.serve(
            self.handlerFire,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    # Define a function that will run the client using asyncio
    async def stop_server(self):
        if self.server:
            servers.remove(self.srv_name2)
            clients.clear()            
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")

    async def stop_client(self):
        global ws
        clients.remove(self.cli_name2)        
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

class characterAI:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []

    def __init__(self, token):

        self.client = Client()

        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.token = token
        self.client = Client()
        self.server = None           

        self.stat = st.empty()
        self.state = self.stat.status(label="Character.ai", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Character.ai", state=st.session_state.client_state, expanded=False)
 
    async def askCharacter(self, characterID, question):
        db = sqlite3.connect('chat-hub.db')
        await self.client.authenticate_with_token(self.token)
        chat = await self.client.create_or_continue_chat(characterID)           
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()        
        try:
            answer = await chat.send_message(question)
            response = f"{answer.src_character_name}: {answer.text}"
            timestamp = datetime.datetime.now().isoformat()
            serverSender = 'server'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, response, timestamp))
            db.commit()
            answer1 = f"Character.ai: {response}"
            print(answer1)
            return str(answer1)
        
        except Exception as e:
            print(f"Error: {e}")

    async def handleUser(self, characterID, question): 
        print(f"User B: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        try:            
            answer = await self.askCharacter(characterID, question)
            serverSender = 'server'
            timestamp = datetime.datetime.now().isoformat()
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (serverSender, answer, timestamp))
            db.commit()
            return answer

        except Exception as e:
            print(f"Error: {e}")        

    async def handlerChar(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name1, state="running", expanded=True)
        self.status.write(clients)
        self.state = self.stat.status(label=self.srv_name1, state="running", expanded=True)
        self.state.write(clients)           
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')       
        await self.client.authenticate_with_token(self.token)
        chat = await self.client.create_or_continue_chat(self.characterID)        
        await websocket.send(instruction)        
        while True:        
            # Receive a message from the client            
            message = await websocket.recv()
            # Print the message
            print(f"Server received: {message}")
            input_Msg = st.chat_message("assistant")
            input_Msg.markdown(message)            
            timestamp = datetime.datetime.now().isoformat()
            sender = 'client'
            db = sqlite3.connect('chat-hub.db')
            db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                        (sender, message, timestamp))
            db.commit()
            try:
                answer = await chat.send_message(message)
                response = f"{answer.src_character_name}: {answer.text}"
                print(response)
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)                
                timestamp = datetime.datetime.now().isoformat()
                serverSender = 'server'
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                await websocket.send(response)
                st.session_state.server_state = "complete"
                self.status.update(state=st.session_state.server_state)
                continue    

            except websockets.exceptions.ConnectionClosedError as e:
                clients.remove(self.cli_name1)
                print(f"Connection closed: {e}")

            except Exception as e:
                clients.remove(self.cli_name1)
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, characterID, clientPort):
        client = Client()
        await client.authenticate_with_token(self.token)
        chat = await client.create_or_continue_chat(characterID)
        self.cli_name1 = f"Character.ai client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        clients.append(self.cli_name1)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name1, state="running", expanded=True)
        self.status.write(servers)
        self.state = self.stat.status(label=self.cli_name1, state="running", expanded=True)
        self.state.write(servers)         
        # Connect to the server
        uri = f'ws://localhost:{clientPort}'
        self.name = f"Character.ai client port: {clientPort}"
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:                         
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)                
                try:
                    answer = await chat.send_message(input_message)
                    response = f"{answer.src_character_name}: {answer.text}"
                    answer = f"Character.ai: {response}"
                    print(answer)
                    outputMsg1 = st.chat_message("ai")
                    outputMsg1.markdown(answer)
                    await websocket.send(answer)
                    continue

                except websockets.ConnectionClosed:
                    print("client disconnected")
                    clients.remove(self.cli_name1)
                    self.cont.empty()
                    self.stat.empty()
                    continue

                except Exception as e:
                    clients.remove(self.cli_name1)
                    self.cont.empty()
                    self.stat.empty()   
                    continue    

    async def connector(self, token):
        client = Client()
        await self.client.authenticate_with_token(token)
        username = (await client.fetch_user())['user']['username']
        print(f'Authenticated as {username}')
        return username
    
    async def start_server(self, characterID, serverPort):
        self.characterID = characterID
        st.session_state.server_state = "running"
        self.server = await websockets.serve(
            self.handlerChar,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.cont.empty()
            clients.clear()
            client_ports.clear()
            print("WebSocket server stopped.")        