import socket
import threading
import curses
import time
import queue

HOST = '4.tcp.eu.ngrok.io'
PORT = 17031

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()

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

def update_messages(client, messages):
    try:
        while True:
            messages.append(client.incoming_queue.get_nowait())
    except queue.Empty:
        pass

def handle_keypress(key, input_buffer, client, messages):
    if key in (curses.KEY_ENTER, 10, 13):
        if not input_buffer:
            return ""
        if input_buffer.lower() in ("quit", "exit"):
            return "EXIT_CMD"

        messages.append(f"Client: {input_buffer}")
        client.outgoing_queue.put(input_buffer)
        return ""

    if key in (curses.KEY_BACKSPACE, 127, 8):
        return input_buffer[:-1]

    if 32 <= key <= 126:
        return input_buffer + chr(key)
    return input_buffer

def draw_ui(stdscr, chat_win, input_win, messages, input_buffer):
    h, w = stdscr.getmaxyx()
    
    chat_win.erase()
    for i, msg in enumerate(messages[-(h - 2):]):
        chat_win.addstr(2 * i, 0, msg[:w-1])
    chat_win.refresh()

    input_win.erase()
    input_win.addstr(0, 0, f">> {input_buffer}"[:w-1])
    input_win.refresh()

def main(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()

    chat_win = curses.newwin(h - 2, w, 0, 0)
    input_win = curses.newwin(1, w, h - 1, 0)

    chat_win.idlok(True)
    chat_win.scrollok(True)

    client = ChatClient(HOST, PORT)
    messages = ["Welcome to ChatCLI", ""]
    input_buffer = ""

    draw_ui(stdscr, chat_win, input_win, messages, input_buffer)

    if not client.connect():
        update_messages(client, messages)
        draw_ui(stdscr, chat_win, input_win, messages, "Press a key to quit")
        stdscr.nodelay(False)
        stdscr.getch()
        return

    try:
        while client.running:
            update_messages(client, messages)

            key = stdscr.getch()
            if key != -1:
                input_buffer = handle_keypress(key, input_buffer, client, messages)
                if input_buffer == "EXIT_CMD":
                    break

            draw_ui(stdscr, chat_win, input_win, messages, input_buffer)
            time.sleep(0.016)
    finally:
        client.stop()

if __name__ == "__main__":
    curses.wrapper(main)
