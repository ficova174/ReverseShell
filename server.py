import socket
import threading
import curses
import time
import queue

class ChatServer:
    def __init__(self, host='', port=5000):
        self.host = host
        self.port = port
        self.running = False
        self.client_socket = None
        
        # Server/UI interface
        self.incoming_queue = queue.Queue()  # Network -> Server -> UI
        self.outgoing_queue = queue.Queue()  # UI -> Server -> Network

    def start(self):
        """Start the server in the background"""
        self.running = True
        # daemon=True so that threads stop when exiting the program
        threading.Thread(target=self._run_server, daemon=True).start()

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()

    def _run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # When we close a TCP connexion there is a TIME_WAIT when the OS is waiting for late packages
            # SO_REUSEADDR tells the OS to reuse the address and not wait for the late packages
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            
            self.incoming_queue.put(f"Server listening on port : {self.port}...")
            
            # We don't want the server to close
            s.settimeout(1.0)
            while self.running:
                try:
                    client_socket, client_addr = s.accept()
                    self.client_socket = client_socket
                    self.incoming_queue.put(f"New client connected : {client_addr[0]}:{client_addr[1]}")
                    break
                except socket.timeout:
                    continue

        threading.Thread(target=self._receive, daemon=True).start()
        threading.Thread(target=self._send, daemon=True).start()

    def _receive(self):
        self.client_socket.settimeout(0.5)
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    self.incoming_queue.put("Client disconnected")
                    self.running = False
                    break
                self.incoming_queue.put(f"Client: {data}")
            except socket.timeout:
                continue
            except Exception:
                break

    def _send(self):
        while self.running:
            try:
                msg = self.outgoing_queue.get(timeout=0.5)
                self.client_socket.sendall(msg.encode())
            except queue.Empty:
                continue
            except Exception:
                break

def update_messages(server, messages):
    """Get all the messages from the server"""
    try:
        while True:
            messages.append(server.incoming_queue.get_nowait())
    except queue.Empty:
        pass

def handle_keypress(key, input_buffer, server, messages):
    """Handle the keyboard and input buffer"""
    if key in (curses.KEY_ENTER, 10, 13):
        if not input_buffer:
            return ""
        if input_buffer.lower() in ("quit", "exit"):
            return "EXIT_CMD"
        
        messages.append(f"Server: {input_buffer}")
        server.outgoing_queue.put(input_buffer)
        return ""
    
    if key in (curses.KEY_BACKSPACE, 127, 8):
        return input_buffer[:-1]
    
    if 32 <= key <= 126:
        return input_buffer + chr(key)
    return input_buffer

def draw_ui(stdscr, chat_win, input_win, messages, input_buffer):
    """Handle the display"""
    # In case we changed our terminal size
    h, w = stdscr.getmaxyx()
    
    chat_win.erase()
    for i, msg in enumerate(messages[-(h - 2):]):
        chat_win.addstr(2 * i, 0, msg[:w-1])
    chat_win.refresh()

    input_win.erase()
    input_win.addstr(0, 0, f">> {input_buffer}"[:w-1])
    input_win.refresh()

def main(stdscr):
    # Draw the cursor
    curses.curs_set(0)
    # getch() becomes non blocking
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()

    chat_win = curses.newwin(h - 2, w, 0, 0)
    input_win = curses.newwin(1, w, h - 1, 0)

    chat_win.idlok(True)
    chat_win.scrollok(True)

    server = ChatServer()
    server.start()

    messages = []
    input_buffer = ""

    draw_ui(stdscr, chat_win, input_win, messages, input_buffer)

    try:
        while server.running:
            update_messages(server, messages)

            key = stdscr.getch()
            if key != -1:
                input_buffer = handle_keypress(key, input_buffer, server, messages)
                if input_buffer == "EXIT_CMD":
                    break

            draw_ui(stdscr, chat_win, input_win, messages, input_buffer)
            time.sleep(0.016)
    finally:
        server.stop()

if __name__ == "__main__":
    curses.wrapper(main)
