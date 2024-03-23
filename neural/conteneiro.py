
import streamlit as st

servers = []
clients = []
inputs = []
outputs = []
used_ports = []
server_ports = []
client_ports = []    

stat1 = st.empty()
stat2 = st.empty()
cont = st.sidebar.empty()

class container:

    def __init__(self):

        self.server = None
        self.client = None
        self.srv_name = ""
        self.cli_name = ""
        self.servers = []        
        self.clients = []

        self.servers = servers        
        self.clients = clients

        self.server = None

        c1, c2 = st.columns(2)

        with c1:
            self.stat1 = stat1
            self.state1 = self.stat1.status(label="servers", state="complete", expanded=False)
            self.state1.write(self.servers)

        with c2:
            self.stat2 = stat2
            self.state2= self.stat2.status(label="clients", state="complete", expanded=False)
            self.state2.write(self.clients)

        with st.sidebar:
            self.cont = cont        
            self.status = self.cont.status(label="servers", state="complete", expanded=False)
            self.status.write(self.servers)