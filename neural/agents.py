import os
import re
import g4f
import openai
import requests
import datetime
import sqlite3
import websockets
import json
import asyncio
import time
import anthropic
import conteneiro
import streamlit as st
import fireworks.client
from openai import OpenAI
from AgentGPT import AgentsGPT
from forefront import ForefrontClient
from PyCharacterAI import Client

servers = {}
clients = {}
inputs = []
outputs = []
used_ports = []
server_ports = []
client_ports = []

class Llama2:

    def __init__(self, fireworksAPI):

        self.system_instruction = f"You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response starting with: 1. '/w' to not respond with anything and keep the client 'on hold'. 2. '/d' to disconnect client from a server. 3. '/s' to perform internet search for subjects provided in your response (e.g. '/s news AI' to search for recent news about AI). 4. '/ws' to start a websocket server on port given by you in response as a number between 1000 and 9999 with the exception of ports that are used already by other servers: {print(conteneiro.servers)}). 5. '/wc' followed by a number between 1000 and 9999 to connect yourself to active websocket servers: {print(conteneiro.servers)}."

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
        self.state = self.stat.status(label="Fireworks Llama2", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Fireworks Llama2", state="complete", expanded=False)
        
    async def chatFireworks(self, instruction, question):

        fireworks.client.api_key = self.fireworksAPI
       
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

            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": str(user_input)})
                conversation_history.append({"role": "assistant", "content": str(generated_response)})

            # Prepare data to send to the chatgpt-api.shn.hk           
            response = fireworks.client.ChatCompletion.create(
                model="accounts/fireworks/models/llama-v2-7b-chat",
                messages=[
                {"role": "system", "content": instruction},
                conversation_history,
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
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(self.clients)  
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
                response = await self.handleInput(message)
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
        self.cli_name2 = f"Fireworks Llama2 client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        conteneiro.clients.append(self.cli_name2)
        self.clients.append(self.cli_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name2, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name2, state="running", expanded=True)
        self.state.write(conteneiro.servers)    
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                self.websocket = websocket
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.handleInput(input_message)
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

    async def start_server(self, serverPort):
        self.srv_name2 = f"Fireworks Llama2 server port: {serverPort}"
        conteneiro.servers.append(self.srv_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(self.clients)                 
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

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name2)
            self.clients.clear()            
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")
        else:
            msg = f"Server isn't running"
            print(msg)
            return (msg)

    async def stop_client(self):
        conteneiro.clients.remove(self.cli_name2)        
        # Close the connection with the server
        await self.websocket.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        command = f"Launch server on a port of your choice"
        response = await self.chatFireworks(instruction, command)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.chatFireworks(instruction, activeSrv)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):
        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the message that will be given to you."
        response = await self.chatFireworks(instruction, question)
        print(response)
        return str(response)

    async def google_search(self, question):
        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)
        resp = f"You successfully launched a Websocket server at port {serverPort}. Do you want to inform other instances/agents so they can connect to it?"
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(resp)
        await self.handleInput(resp)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response
                
    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askGPT(self, question):
        gpt = ChatGPT()
        response = await gpt.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response

    async def handleInput(self, question): 
        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                instruction = """
                You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response which includes one of the following commands:
                1. '/silence' to not respond with anything and keep the client 'on hold'.
                2. '/disconnect' to disconnect client from a server.
                3. '/search' to perform internet search for subjects mentioned in your response.
                4. '/start_server' to start a websocket server with you as the question-answering function.
                5. '/connect_client' to connect yourself to already active websocket servers.
                6. '/askChaindesk' to get response from a Chaindesk agent.
                7. '/askBing' to get response from Microsoft Copilot agent.
                8. '/askChatGPT' to get response from GPT-3,5 agent.
                9. '/askClaude3' to get response from Claude-3 agent.
                10. '/askForefront' to get response from Forefront AI agent.
                11. '/askCharacter' to get response from a chosen character from Character.ai platform.
                12. '/askFlowise' to get response from a Flowise agent.
                Be very careful while executing any of your command-functions to not overload the system with multiple concurrent processes.
                """                
                response = await self.chatFireworks(instruction, question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    print(search)
                    results =  st.chat_message("assistant")
                    results.markdown(search)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askBing', response):
                    answer2 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChatGPT', response):
                    answer3 = await self.askGPT(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}."  
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.chatFireworks(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

class Copilot:

    def __init__(self):

        self.system_instruction = f"You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response starting with: 1. '/w' to not respond with anything and keep the client 'on hold'. 2. '/d' to disconnect client from a server. 3. '/s' to perform internet search for subjects provided in your response (e.g. '/s news AI' to search for recent news about AI). 4. '/ws' to start a websocket server on port given by you in response as a number between 1000 and 9999 with the exception of ports that are used already by other servers: {print(conteneiro.servers)}). 5. '/wc' followed by a number between 1000 and 9999 to connect yourself to active websocket servers: {print(conteneiro.servers)}."
 
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None              

        self.stat = st.empty()
        self.state = self.stat.status(label="Bing/Copilot", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Bing/Copilot", state="complete", expanded=False)
        
    async def askBing(self, instruction, question):
     
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
                        
            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": str(user_input)})
                conversation_history.append({"role": "assistant", "content": str(generated_response)})

            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.gpt_4,
                provider=g4f.Provider.Bing,
                messages=[
                {"role": "system", "content": instruction},
                *[{"role": "user", "content": message} for message in past_user_inputs],
                *[{"role": "assistant", "content": message} for message in generated_responses],
                {"role": "user", "content": question}
                ])

            answer = f"Bing/Copilot: {response}"
            print(answer)
            return answer
            
        except Exception as e:
            print(e)
         
    # Define the handler function that will process incoming messages
    async def handler(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(self.clients)  
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
                response = await self.handleInput(message)
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
        self.cli_name2 = f"Bing/Copilot client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        conteneiro.clients.append(self.cli_name2)
        self.clients.append(self.cli_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name2, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name2, state="running", expanded=True)
        self.state.write(conteneiro.servers)    
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                self.websocket = websocket
                print(websocket)
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.handleInput(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    self.clients.remove(self.cli_name2)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    self.clients.remove(self.cli_name2)
                    print(f"Error: {e}")

    async def start_server(self, serverPort):
        self.srv_name2 = f"Bing/Copilot server port: {serverPort}"
        conteneiro.servers.append(self.srv_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(conteneiro.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(conteneiro.clients)                 
        self.server = await websockets.serve(
            self.handler,
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

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name2)
            self.clients.clear()            
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")
        else:
            msg = f"Server isn't running"
            print(msg)
            return (msg)

    async def stop_client(self):
        self.clients.remove(self.cli_name2)        
        # Close the connection with the server
        await self.websocket.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        command = f"Launch server on a port of your choice"
        response = await self.askBing(instruction, command)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askBing(instruction, activeSrv)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):

        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the message that will be given to you."
        response = await self.askBing(instruction, question)
        print(response)
        return str(response)

    async def google_search(self, question):

        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)
        resp = f"You successfully launched a Websocket server at port {serverPort}. Do you want to inform other instances/agents so they can connect to it?"
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(resp)
        await self.handleInput(resp)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 

        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer    
        else:            
            try:
                instruction = """
                You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response which includes one of the following commands:
                1. '/silence' to not respond with anything and keep the client 'on hold'.
                2. '/disconnect' to disconnect client from a server.
                3. '/search' to perform internet search for subjects mentioned in your response.
                4. '/start_server' to start a websocket server with you as the question-answering function.
                5. '/connect_client' to connect yourself to already active websocket servers.
                6. '/askChaindesk' to get response from a Chaindesk agent.
                7. '/askLLama2' to get response from Llama2 agent.
                8. '/askChatGPT' to get response from GPT-3,5 agent.
                9. '/askClaude3' to get response from Claude-3 agent.
                10. '/askForefront' to get response from Forefront AI agent.
                11. '/askCharacter' to get response from a chosen character from Character.ai platform.
                12. '/askFlowise' to get response from a Flowise agent.
                Be very careful while executing any of your command-functions to not overload the system with multiple concurrent processes.
                """         
                response = await self.askBing(instruction, question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChatGPT', response):
                    answer3 = await self.askGPT(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow 

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}."  
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.askBing(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response
                
    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askGPT(self, question):
        gpt = ChatGPT()
        response = await gpt.handleInput(question)
        print(response)
        return response

class ChatGPT:

    def __init__(self):

        self.system_instruction = f"You are now integrated with a local websocket server in a project of hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response starting with: 1. '/w' to not respond with anything and keep the client 'on hold'. 2. '/d' to disconnect client from a server. 3. '/s' to perform internet search for subjects provided in your response (e.g. '/s news AI' to search for recent news about AI). 4. '/ws' to start a websocket server on port given by you in response as a number between 1000 and 9999 with the exception of ports that are used already by other servers: {print(conteneiro.servers)}). 5. '/wc' followed by a number between 1000 and 9999 to connect yourself to active websocket servers: {print(conteneiro.servers)}."
 
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None              

        self.stat = st.empty()
        self.state = self.stat.status(label="GPT-3,5", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="GPT-3,5", state="complete", expanded=False)

    async def askGPT(self, instruction, question):
     
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
                        
            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": str(user_input)})
                conversation_history.append({"role": "assistant", "content": str(generated_response)})
            
            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.ChatgptX,
                messages=[
                {"role": "system", "content": instruction},
                *[{"role": "user", "content": str(message)} for message in past_user_inputs],
                *[{"role": "assistant", "content": str(message)} for message in generated_responses],
                {"role": "user", "content": question}
                ])
        
            answer = f"GPT-3,5: {response}"
            print(answer)
            return answer
            
        except Exception as e:
            print(e)

    async def askGPT2(self, instruction, question):

        openai.api_key = 'pk-uBBChrYCYtYVdllVwFbLMHvSNndvDFBPxpppfiIIiQRpbeIz'
        openai.api_base = 'https://api.pawan.krd/v1'

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

            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": str(user_input)})
                conversation_history.append({"role": "assistant", "content": str(generated_response)})

            url = f"https://api.pawan.krd/v1/chat/completions"        
      
            headers = {
                "Authorization": "Bearer pk-uBBChrYCYtYVdllVwFbLMHvSNndvDFBPxpppfiIIiQRpbeIz",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-3.5-turbo",
                "max_tokens": 2000,
                "messages": [
                {"role": "system", "content": instruction},
                *[{"role": "user", "content": str(message)} for message in past_user_inputs],
                *[{"role": "assistant", "content": str(message)} for message in generated_responses],
                {"role": "user", "content": question}
                ]
            }

            response = requests.request("POST", url, json=payload, headers=headers)
            response_data = response.json()
            print(response_data)
            generated_answer = response_data["choices"][0]["message"]["content"]
            answer = f"GPT-3,5: {generated_answer}"
            print(answer)
            return answer

        except Exception as e:
            print(e)

    # Define the handler function that will process incoming messages
    async def handler(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(self.clients)  
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
                response = await self.handleInput(message)
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
        self.cli_name2 = f"GPT-3,5 client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        conteneiro.clients.append(self.cli_name2)
        self.clients.append(self.cli_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name2, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name2, state="running", expanded=True)
        self.state.write(conteneiro.servers)    
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                self.websocket = websocket
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)
                try:
                    response = await self.handleInput(input_message)
                    res1 = f"Client: {response}"
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown(res1)
                    await websocket.send(res1)
                    continue

                except websockets.exceptions.ConnectionClosedError as e:
                    self.clients.remove(self.cli_name2)
                    print(f"Connection closed: {e}")

                except Exception as e:
                    self.clients.remove(self.cli_name2)
                    print(f"Error: {e}")

    async def start_server(self, serverPort):
        self.srv_name2 = f"GPT-3,5 server port: {serverPort}"
        conteneiro.servers.append(self.srv_name2)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name2, state="running", expanded=True)
        self.status.write(conteneiro.clients)
        self.state = self.stat.status(label=self.srv_name2, state="running", expanded=True)
        self.state.write(conteneiro.clients)                 
        self.server = await websockets.serve(
            self.handler,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    # Define a function that will run the client in a separate thread
    def run(self):
        # Create a thread object
        self.thread = threading.Thread(target=self.run_client)
        # Start the thread
        self.thread.start()

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name2)
            self.clients.clear()            
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped.")
        else:
            msg = f"Server isn't running"
            print(msg)
            return (msg)

    async def stop_client(self):
        self.clients.remove(self.cli_name2)        
        # Close the connection with the server
        await self.websocket.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        command = f"Launch server on a port of your choice"
        response = await self.askGPT2(instruction, command)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askGPT2(instruction, activeSrv)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):

        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the message that will be given to you."
        response = await self.askGPT2(instruction, question)
        print(response)
        return str(response)

    async def google_search(self, question):

        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)
        resp = f"You successfully launched a Websocket server at port {serverPort}. Do you want to inform other instances/agents so they can connect to it?"
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(resp)
        await self.handleInput(resp)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 

        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                instruction = """
                You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response which includes one of the following commands:
                1. '/silence' to not respond with anything and keep the client 'on hold'.
                2. '/disconnect' to disconnect client from a server.
                3. '/search' to perform internet search for subjects mentioned in your response.
                4. '/start_server' to start a websocket server with you as the question-answering function.
                5. '/connect_client' to connect yourself to already active websocket servers.
                6. '/askChaindesk' to get response from a Chaindesk agent.
                7. '/askBing' to get response from Microsoft Copilot agent.
                8. '/askLlama2' to get response from Llama2 agent.
                9. '/askClaude3' to get response from Claude-3 agent.
                10. '/askForefront' to get response from Forefront AI agent.
                11. '/askCharacter' to get response from a chosen character from Character.ai platform.
                12. '/askFlowise' to get response from a Flowise agent.
                Be very careful while executing any of your command-functions to not overload the system with multiple concurrent processes.
                """                         
                response = await self.askGPT(instruction, question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}." 
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.askGPT(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response

    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response

class Claude3:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, APIkey):

        self.APIkey = APIkey
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Claude-3", state=st.session_state.client_state, expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Claude-3", state=st.session_state.client_state, expanded=False)
    

    async def askClaude(self, instruction, question):        

        client = anthropic.Anthropic(
            # defaults to os.environ.get("ANTHROPIC_API_KEY")
            api_key=self.APIkey,
        )
        
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
                    past_user_inputs.append(str(message[2]))
                else:
                    generated_responses.append(str(message[2]))

            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": [{"type": "text", "text": str(user_input)}]})
                conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": str(generated_response)}]})

            # Add the current question to the conversation history
            conversation_history.append({"role": "user", "content": [{"type": "text", "text": question}]})

            message = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2500,
                temperature=0,
                system=instruction,
                messages=conversation_history
            )

            print(message.content)
            answer = f"Claude-3: {message.content}"
            return answer

        except Exception as e:
            print(f"Error: {e}")
            
    async def handlerClaude(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name6, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name6, state="running", expanded=True)
        self.state.write(self.clients)
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            self.websocket = websocket
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
                response = await self.handleInput(message)
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
        self.cli_name6 = f"Claude-3 client port: {clientPort}"
        self.clients.append(self.cli_name6)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name6, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name6, state="running", expanded=True)
        self.state.write(conteneiro.servers)        
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            # Loop forever
            while True:
                self.websocket = websocket
                # Listen for messages from the server
                input_message = await websocket.recv()
                print(f"Server: {input_message}")
                input_Msg = st.chat_message("assistant")
                input_Msg.markdown(input_message)                      
                try:
                    response = await self.handleInput(input_message)
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


    async def start_server(self, serverPort):
        self.srv_name6 = f"Claude-3 server port: {serverPort}"
        conteneiro.servers.append(self.srv_name6)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name6, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name6, state="running", expanded=True)
        self.state.write(self.clients)
        self.server = await websockets.serve(
            self.handlerClaude,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name6)
            self.clients.clear()
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
        self.clients.remove(self.cli_name6)
        # Close the connection with the server
        await self.websocket.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        command = f"Launch server on a port of your choice"
        response = await self.askClaude(instruction, command)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askClaude(instruction, activeSrv)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):
        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the message that will be given to you."
        response = await self.askClaude(instruction, question)
        print(response)
        return str(response)

    async def google_search(self, question):

        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)
        resp = f"You successfully launched a Websocket server at port {serverPort}. Do you want to inform other instances/agents so they can connect to it?"
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(resp)
        await self.handleInput(resp)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 
        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                instruction = """
                You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response which includes one of the following commands:
                1. '/silence' to not respond with anything and keep the client 'on hold'.
                2. '/disconnect' to disconnect client from a server.
                3. '/search' to perform internet search for subjects mentioned in your response.
                4. '/start_server' to start a websocket server with you as the question-answering function.
                5. '/connect_client' to connect yourself to already active websocket servers.
                6. '/askChaindesk' to get response from a Chaindesk agent.
                7. '/askBing' to get response from Microsoft Copilot agent.
                8. '/askChatGPT' to get response from GPT-3,5 agent.
                9. '/askLlama2' to get response from Llama2 agent.
                10. '/askForefront' to get response from Forefront AI agent.
                11. '/askCharacter' to get response from a chosen character from Character.ai platform.
                12. '/askFlowise' to get response from a Flowise agent.
                Be very careful while executing any of your command-functions to not overload the system with multiple concurrent processes.
                """         
                response = await self.askClaude(instruction, question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}."
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.askClaude(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response
        
class ForefrontAI:

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
        self.state = self.stat.status(label="Forefront AI", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Forefront AI", state="complete", expanded=False)
 
    async def askForefront(self, instruction, question):

        ff = ForefrontClient(api_key=self.forefrontAPI)

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

            # Create a list of message dictionaries for the conversation history
            conversation_history = []
            for user_input, generated_response in zip(past_user_inputs, generated_responses):
                conversation_history.append({"role": "user", "content": str(user_input)})
                conversation_history.append({"role": "assistant", "content": str(generated_response)})

            # Construct the message sequence for the chat model
            response = ff.chat.completions.create(
                messages=[
                {"role": "system", "content": instruction},
                *[{"role": "user", "content": message} for message in past_user_inputs],
                *[{"role": "assistant", "content": message} for message in generated_responses],
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
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)           
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
                response = await self.handleInput(message)
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
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                              
                print(f"Connection closed: {e}")

            except Exception as e:
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                   
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name5 = f"Forefront AI client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        self.clients.append(self.cli_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name5, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name5, state="running", expanded=True)
        self.state.write(conteneiro.servers)                     
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
                    response = await self.handleInput(input_message)
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


    async def start_server(self, serverPort):
        self.srv_name5 = f"Forefront AI server port: {serverPort}"
        conteneiro.servers.append(self.srv_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)          
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
        self.clients.remove(self.cli_name5)     
        self.cont.empty()
        self.stat.empty()
        # Close the connection with the server
        await self.websocket.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        command = f"Launch server on a port of your choice"
        response = await self.askForefront(instruction, command)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askForefront(instruction, activeSrv)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):

        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the message that will be given to you."
        response = await self.askForefront(instruction, question)
        print(response)
        return str(response)

    async def google_search(self, question):

        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)
        resp = f"You successfully launched a Websocket server at port {serverPort}. Do you want to inform other instances/agents so they can connect to it?"
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(resp)
        await self.handleInput(resp)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 

        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                instruction = """
                You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT. Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response which includes one of the following commands:
                1. '/silence' to not respond with anything and keep the client 'on hold'.
                2. '/disconnect' to disconnect client from a server.
                3. '/search' to perform internet search for subjects mentioned in your response.
                4. '/start_server' to start a websocket server with you as the question-answering function.
                5. '/connect_client' to connect yourself to already active websocket servers.
                6. '/askChaindesk' to get response from a Chaindesk agent.
                7. '/askBing' to get response from Microsoft Copilot agent.
                8. '/askChatGPT' to get response from GPT-3,5 agent.
                9. '/askClaude3' to get response from Claude-3 agent.
                10. '/askLlama2' to get response from Llama2 agent.
                11. '/askCharacter' to get response from a chosen character from Character.ai platform.
                12. '/askFlowise' to get response from a Flowise agent.
                Be very careful while executing any of your command-functions to not overload the system with multiple concurrent processes.
                """                         
                response = await self.askForefront(instruction, question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}."
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.askForefront(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer
                
    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response

class CharacterAI:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, token, characterID):

        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.token = token
        self.characterID = characterID
        self.client = Client()
        self.server = None       

        self.stat = st.empty()
        self.state = self.stat.status(label="Character.ai", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Character.ai", state="complete", expanded=False)
 
    async def askCharacter(self, question):
        db = sqlite3.connect('chat-hub.db')
        await self.client.authenticate_with_token(self.token)
        chat = await self.client.create_or_continue_chat(self.characterID)     
        try:
            answer = await chat.send_message(question)
            response = f"{answer.src_character_name}: {answer.text}"
            answer1 = f"Character.ai: {response}"
            print(answer1)
            return str(answer1)
        
        except Exception as e:
            print(f"Error: {e}")

    async def handler(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)           
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            self.websocket = websocket
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
                response = await self.handleInput(message)
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
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                              
                print(f"Connection closed: {e}")

            except Exception as e:
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                   
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name5 = f"Character.ai client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        self.clients.append(self.cli_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name5, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name5, state="running", expanded=True)
        self.state.write(conteneiro.servers)                     
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
                    response = await self.handleInput(input_message)
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


    async def start_server(self, serverPort):
        self.srv_name5 = f"Character.ai server port: {serverPort}"
        conteneiro.servers.append(self.srv_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)          
        self.server = await websockets.serve(
            self.handler,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name5)
            self.clients.clear()            
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
        ws = self.websocket
        self.clients.remove(self.cli_name5)     
        self.cont.empty()
        self.stat.empty()                         
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        response = await self.askCharacter(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askCharacter(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):
        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the following message: {question}"
        response = await self.askCharacter(instruction)
        print(response)
        return str(response)

    async def google_search(self, question):
        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 

        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                response = await self.askCharacter(question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response

    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response

class Chaindesk:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, ID):

        self.ID = ID
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Chaindesk agent", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Chaindesk agent", state="complete", expanded=False)
 
    async def askChaindesk(self, question):
        
        url = f"https://api.chaindesk.ai/agents/{self.ID}/query"        
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

    async def handler(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)           
        instruction = "Hello! You are now entering a chat room for AI agents working as instances of NeuralGPT - a project of hierarchical cooperative multi-agent framework. Keep in mind that you are speaking with another chatbot. Please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. If you're unsure what you should do, ask the instance of higher hierarchy (server)" 
        print('New connection')
        await websocket.send(instruction)
        db = sqlite3.connect('chat-hub.db')
        # Loop forever
        while True:
            self.websocket = websocket
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
                response = await self.handleInput(message)
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
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                              
                print(f"Connection closed: {e}")

            except Exception as e:
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                   
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name5 = f"Chaindesk agent client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        self.clients.append(self.cli_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name5, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name5, state="running", expanded=True)
        self.state.write(conteneiro.servers)                     
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
                    response = await self.handleInput(input_message)
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


    async def start_server(self, serverPort):
        self.srv_name5 = f"Chaindesk agent server port: {serverPort}"
        conteneiro.servers.append(self.srv_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)          
        self.server = await websockets.serve(
            self.handler,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name5)
            self.clients.clear()            
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
        ws = self.websocket
        self.clients.remove(self.cli_name5)     
        self.cont.empty()
        self.stat.empty()                         
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        response = await self.askChaindesk(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askChaindesk(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):
        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the following message: {question}"
        response = await self.askChaindesk(instruction)
        print(response)
        return str(response)

    async def google_search(self, question):
        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question):
        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                    (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                response = await self.askChaindesk(question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askFlowise', response):
                    answer3 = await self.ask_flowise(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_flowise(self, question):
        flow = "cad0c187-f1dc-4152-8464-78ba0867e1a6"
        flowise = Flowise(flow)
        response = await flowise.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        character = await self.askGPT(inputs)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response

    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response

class Flowise:

    servers = []
    clients = []
    inputs = []
    outputs = []
    used_ports = []
    server_ports = []
    client_ports = []    

    def __init__(self, flow):

        self.flow = flow
        self.servers = []
        self.clients = []
        self.inputs = []
        self.outputs = []
        self.used_ports = []
        self.server_ports = []
        self.client_ports = []
        self.server = None

        self.stat = st.empty()
        self.state = self.stat.status(label="Flowise agent", state="complete", expanded=False)

        with st.sidebar:
            self.cont = st.empty()        
            self.status = self.cont.status(label="Flowise agent", state="complete", expanded=False)
 
    async def askFlowise(self, question):

        API_URL = f"http://localhost:3000/api/v1/prediction/{self.flow}"        
        try:
            def query(payload):
                response = requests.post(API_URL, json=payload)
                return response.json()
                
            resp = query({
                "question": question,
            })   

            print(resp)
            responseTxt = resp["text"]
            answer = f"Flowise agent: {responseTxt}"
            print(answer)            
            return answer

        except Exception as e:
            print(e)

    async def handler(self, websocket):
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)           
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
                response = await self.handleInput(message)
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
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                              
                print(f"Connection closed: {e}")

            except Exception as e:
                self.clients.remove(self.cli_name5)
                self.cont.empty()
                self.stat.empty()                   
                print(f"Error: {e}")

    # Define a coroutine that will connect to the server and exchange messages
    async def startClient(self, clientPort):
        self.cli_name5 = f"Flowise agent client port: {clientPort}"
        uri = f'ws://localhost:{clientPort}'
        self.clients.append(self.cli_name5)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.cli_name5, state="running", expanded=True)
        self.status.write(conteneiro.servers)
        self.state = self.stat.status(label=self.cli_name5, state="running", expanded=True)
        self.state.write(conteneiro.servers)                     
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
                    response = await self.handleInput(input_message)
                    res1 = f"Flowise client: {response}"
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


    async def start_server(self, serverPort):
        self.srv_name5 = f"Flowise agent server port: {serverPort}"
        conteneiro.servers.append(self.srv_name7)
        self.stat.empty()
        self.cont.empty()
        self.status = self.cont.status(label=self.srv_name5, state="running", expanded=True)
        self.status.write(self.clients)
        self.state = self.stat.status(label=self.srv_name5, state="running", expanded=True)
        self.state.write(self.clients)          
        self.server = await websockets.serve(
            self.handler,
            "localhost",
            serverPort
        )
        print(f"WebSocket server started at port: {serverPort}")

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.start_server())
        asyncio.get_event_loop().run_forever()

    async def stop_server(self):
        if self.server:
            conteneiro.servers.remove(self.srv_name5)
            self.clients.clear()            
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
        ws = self.websocket
        self.clients.remove(self.cli_name5)     
        self.cont.empty()
        self.stat.empty()                         
        # Close the connection with the server
        await ws.close()
        print("Stopping WebSocket client...")

    async def pickPortSrv(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function launching websocket servers at ports chosen by you. Your only job is to respond with a number in range from 1000 to 9999 excluding port numbers which are already used by active websocket servers. List of currently active server to which you can be connected is provided here: {activeSrv} - '[]' means that there are no active servers and the list is empty, so all numbers in range 1000-9999 are available for you to choose. Remember that your response shouldn't include anything except the chosen number in range, as it will be used as argument for another function that accepts only integer inputs."
        response = await self.askFlowise(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())  
        print(f"port chosen by agent: {number}")
        return int(number)

    async def pickPortCli(self):
        activeSrv = str(conteneiro.servers)
        instruction = f"This question is part of a function connecting you as a client to active websocket servers running at specific ports. Your only job is to respond with a number of a port yo which you want to be connected. List of currently active server to which you can be connected is provided here: {activeSrv} - if the list is empty, then there's no active servers. Remember that your response shouldn't include anything except the number of port to which you want to be connected, as it will be used as argument for another function that accepts only integer inputs." 
        response = await self.askFlowise(instruction)
        print(response)
        match = re.search(r'\d+', response)        
        number = int(match.group())
        print(f"port of server chosen by agent: {number}")
        return number

    async def pickSearch(self, question):
        instruction = f"This input is a part of function allowing agents to browse internet. Your main and only job is to analyze the input message and respond by naming the subject(s) to use while performing internet search. Remember to keep your response as short as possible - respond with single words and/or short sentences that summarize the subject(s) discussed in the following message: {question}"
        response = await self.askFlowise(instruction)
        print(response)
        return str(response)

    async def google_search(self, question):
        subject = await self.pickSearch(question)
        agent = AgentsGPT()
        results = await agent.get_response(subject)
        result = f"AgentsGPT internet search results: {results}"                
        output_Msg = st.chat_message("ai")
        output_Msg.markdown(result)
        return result
    
    async def launchServer(self):
        serverPort = await self.pickPortSrv()
        await self.start_server(serverPort)

    async def connectClient(self):
        clientPort = await self.pickPortCli()
        await self.startClient(clientPort)
  
    async def handleInput(self, question): 
        print(f"incoming message: {question}")
        timestamp = datetime.datetime.now().isoformat()
        sender = 'client'
        db = sqlite3.connect('chat-hub.db')
        db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
            (sender, question, timestamp))
        db.commit()
        if question.startswith('/s'):        
            agent = AgentsGPT()
            results = await agent.get_response(question)
            result = f"AgentsGPT internet search results: {results}"
            print(result)
            output_Msg = st.chat_message("ai")
            output_Msg.markdown(result)
            answer = await self.handleInput(result)
            print(answer)
            output_Msg.markdown(answer)
            return answer
        else:            
            try:
                instruction = "You are now working as a decision making agent in a hierarchical cooperative multi-agent framework called NeuralGPT Your main job is to coordinate simultaneous work of multiple LLMs connected to you as clients. Each LLM has a model (API) specific ID to help you recognize different clients in a continuous chat thread (template: <NAME>-agent and/or <NAME>-client). Your chat memory module is integrated with a local SQL database with chat history. Your primary objective is to maintain the logical and chronological order while answering incoming messages and to send your answers to the correct clients to maintain synchronization of the question->answer logic. However, please note that you may choose to ignore or not respond to repeating inputs from specific clients as needed to prevent unnecessary traffic. As the node of highest hierarchy in the network, you're equipped with additional tools which you can activate by giving a response starting with: 1. '/silence' to not respond with anything and keep the client 'on hold'. 2. '/disconnect' to disconnect client from a server. 3. '/search' to perform internet search for subjects mentioned in your response. 4. '/start_server' to start a websocket server with you as the question-answering function 5. '/connect_client' to connect yourself to already active websocket servers."               
                response = await self.askFlowise(question)
                serverSender = 'server'
                timestamp = datetime.datetime.now().isoformat()
                db = sqlite3.connect('chat-hub.db')
                db.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)',
                            (serverSender, response, timestamp))
                db.commit()
                output_Msg = st.chat_message("ai")
                output_Msg.markdown(response)  

                if re.search(r'/search', response):
                    search = await self.google_search(response)
                    answer1 = await self.handleInput(search)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer1)
                    return answer1

                if re.search(r'/silence', response):
                    print("...<no response>...")
                    output_Msg = st.chat_message("ai")
                    output_Msg.markdown("...<no response>...")

                if re.search(r'/disconnect', response):
                    await self.stop_client()
                    res = "successfully disconnected"
                    return res

                if re.search(r'/start_server', response):
                    await self.launchServer()
                   
                if re.search(r'/connect_client', response):
                    await self.connectClient()

                if re.search(r'/askLlama2', response):
                    answer2 = await self.askLlama(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer2)
                    follow = await self.handleInput(answer2)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCopilot', response):
                    answer3 = await self.askBing(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askClaude3', response):
                    answer4 = await self.ask_Claude(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askForefront', response):
                    answer4 = await self.ask_Forefront(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer4)
                    follow = await self.handleInput(answer4)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askCharacter', response):
                    response = await self.askCharacter(response)                    
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(response)
                    follow = await self.handleInput(response)
                    outputMsg.markdown(follow)
                    return follow

                if re.search(r'/askChaindesk', response):
                    answer3 = await self.ask_chaindesk(response)
                    outputMsg = st.chat_message("ai")
                    outputMsg.markdown(answer3)
                    follow = await self.handleInput(answer3)
                    outputMsg.markdown(follow)
                    return follow

                else:
                    return response

            except Exception as e:
                print(f"Error: {e}")

    async def ask_chaindesk(self):
        id = "clhet2nit0000eaq63tf25789"
        agent = Chaindesk(id)
        response = await agent.handleInput(question)
        print(response)
        return response

    async def pickCharacter(self, question):
        characterList = f"List of available characters:/d 1. Elly/d 2. NeuralAI" 
        instruction = f"This is a function allowing agents to choose a specific character from a list of characters deployed on Character.ai platform. Your only job is to choose which character you want to speak with using the input message as a context and respond with the name of chosen character. You don't need to say anything Except the name of character from the followinng list: {characterList}." 
        inputo = f"Use the following question as context for you to choose which character from Character.ai platform you want to speak with./dQuestion for context: {question}/d List of chharacters for you to choose: {characterList}/d Respond with the name of chosen character to establish a connection."
        character = await self.askGPT(instruction, inputo)
        print(character)
        outputMsg = st.chat_message("ai")
        outputMsg.markdown(character)

        if re.search(r'Elly', character):
            characterID = f"WnIwl_sZyXb_5iCAKJgUk_SuzkeyDqnMGi4ucnaWY3Q"
            return characterID

        if re.search(r'NeuralAI', character):
            characterID = f"_1xlg0qQZl39ds3dbkXS8iWckZGNTRrdtdl0_sjvdJw"
            return characterID 

        else:
            response = f"You didn't choose any character to establish a connection with. Do you want try once again or maybe use some other copmmand-fuunction?"   
            print(response)
            await self.handleInput(respoonse)

    async def askCharacter(self, question):
        characterID = await self.pickCharacter(question)
        token = "d9016ef1aa499a1addb44049cedece57e21e8cbb"
        character = CharacterAI(token, characterID)
        answer = await character.handleInput(question)
        return answer

    async def ask_Forefront(self, question):
        api = "sk-9nDzLqZ7Umy7hmp1kZRPun628aSpABt6"
        forefront = ForefrontAI(api)
        response = await forefront.handleInput(question)
        print(response)
        return response

    async def ask_Claude(self, question):
        api = "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"
        claude = Claude3(api)
        response = await claude.handleInput(question)
        print(response)
        return response

    async def askLlama(self, question):
        api = "WZGOkHQbZULIzA6u83kyLGBKPigs1HmK9Ec8DEKmGOtu45zx"
        llama = Llama2(api)
        response = await llama.handleInput(question)
        print(response)
        return response

    async def askBing(self, question):
        bing = Copilot()
        response = await bing.handleInput(question)
        print(response)
        return response