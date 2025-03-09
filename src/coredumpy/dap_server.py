# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import json
import socket
import threading
import signal
import sys
from typing import Dict, Any, List

from .coredumpy import load_data_from_path
from .py_object_proxy import PyObjectProxy
from .type_support import is_container


class DebugAdapterServer:
    def __init__(self, host: str = 'localhost', port: int = 6742):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sequence = 1
        self.debugger = None
        self.running = True
        self.clients = []

    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(1)
            print(f"[Server] Debug adapter server successfully bound to {self.host}:{self.port}", flush=True)
            print(f"[Server] Server socket created and listening for connections", flush=True)
            print("[Server] Press Ctrl+C to exit", flush=True)
        except Exception as e:
            print(f"[Server] Error binding server: {e}", flush=True)
            return

        while self.running:
            try:
                self.server.settimeout(0.5)
                try:
                    client, addr = self.server.accept()
                    print(f"[Server] New client connection accepted from {addr}", flush=True)
                    self.clients.append(client)
                    client_thread = threading.Thread(target=self.handle_client, args=(client,))
                    client_thread.daemon = True
                    client_thread.start()
                    print(f"[Server] Started client handler thread for {addr}", flush=True)
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"Error in server loop: {e}")
                break

        self.shutdown()

    def handle_client(self, client: socket.socket):
        print("[Client] Client handler started", flush=True)
        buffer = ""
        while self.running:
            try:
                client.settimeout(0.5)
                try:
                    data = client.recv(4096).decode('utf-8')
                    if not data:
                        break

                    buffer += data
                    while '\r\n\r\n' in buffer:
                        header, rest = buffer.split('\r\n\r\n', 1)
                        content_length = 0

                        for line in header.split('\r\n'):
                            if line.startswith('Content-Length: '):
                                content_length = int(line.split(': ')[1])
                        
                        if len(rest) >= content_length:
                            content = rest[:content_length]
                            buffer = rest[content_length:]
                            self.process_message(client, json.loads(content))
                        else:
                            break
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"Error handling client: {e}")
                break

        if client in self.clients:
            self.clients.remove(client)
        try:
            client.close()
        except:
            pass

    def process_message(self, client: socket.socket, message: Dict[str, Any]):
        try:
            print("[Client] Processing message:", message, flush=True)
            if message.get('type') == 'request':
                command = message.get('command')
                if command == 'initialize':
                    # We don't really support anything
                    self.send_response(client, message, {})
                    self.send_event(client, 'initialized', {})
                elif command == 'launch':
                    program = message.get('arguments', {}).get('program', '')
                    if program:
                        self.debugger = CoredumpyDebugger(program)
                        self.debugger.start()
                    self.send_response(client, message, {})
                    self.send_event(client, 'stopped', {'reason': 'entry', 'threadId': 1})
                elif command == 'threads':
                    self.send_response(client, message, {'threads': [{'id': 1, 'name': 'Thread 1'}]})
                elif command == 'stackTrace':
                    if self.debugger:
                        stack_frames = self.debugger.get_stack_trace()
                    else:
                        stack_frames = []
                    self.send_response(client, message, {'stackFrames': stack_frames, 'totalFrames': len(stack_frames)})
                elif command == 'source':
                    source_reference = message.get('arguments', {}).get('sourceReference', 0)
                    if self.debugger:
                        source = self.debugger.get_source(source_reference)
                    else:
                        source = {}
                    self.send_response(client, message, {'content': source, 'mimeType': 'text/x-python'})
                elif command == 'scopes':
                    frame_id = message.get('arguments', {}).get('frameId', 0)
                    if self.debugger:
                        scopes = self.debugger.get_scopes(frame_id)
                    else:
                        scopes = []
                    self.send_response(client, message, {'scopes': scopes})
                elif command == 'variables':
                    variables_reference = message.get('arguments', {}).get('variablesReference', 0)
                    if self.debugger:
                        variables = self.debugger.get_variables(variables_reference)
                    else:
                        variables = []
                    self.send_response(client, message, {'variables': variables})
                elif command == 'disconnect':
                    if self.debugger:
                        self.debugger.stop()
                        self.debugger = None
                    self.send_response(client, message, {})
                    self.send_event(client, 'exited', {'exitCode': 0})
                    self.running = False
                else:
                    self.send_response(client, message, {})

        except Exception as e:
            self.send_error_response(client, message, str(e))

    def send_message(self, client: socket.socket, message: Dict[str, Any]):
        print("[Client] Sending message:", message, flush=True)
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        client.send(header.encode('utf-8'))
        client.send(content.encode('utf-8'))

    def send_response(self, client: socket.socket, request: Dict[str, Any], body: Dict[str, Any]):
        self.send_message(client, {
            'type': 'response',
            'request_seq': request.get('seq', 0),
            'success': True,
            'command': request.get('command', ''),
            'body': body
        })

    def send_error_response(self, client: socket.socket, request: Dict[str, Any], message: str):
        self.send_message(client, {
            'type': 'response',
            'request_seq': request.get('seq', 0),
            'success': False,
            'command': request.get('command', ''),
            'message': message
        })

    def send_event(self, client: socket.socket, event: str, body: Dict[str, Any]):
        self.send_message(client, {
            'type': 'event',
            'event': event,
            'seq': self.sequence,
            'body': body
        })
        self.sequence += 1

    def shutdown(self):
        self.running = False
        
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        try:
            self.server.close()
        except:
            pass
        
        if self.debugger:
            self.debugger.stop()
            self.debugger = None


class CoredumpyDebugger:
    def __init__(self, path: str):
        self.path = path
        self.process = None
        self.current_line = 0
        self.current_file = ''
        self.variables = {}
        self.stack_frames = []
        self.container = None
        self.frame = None
        self.files = {}
        self.sid_to_file = {}
        self.file_to_sid = {}
        self.fid_to_frame = {}
        self.frame_stack = []
        self.real_id_to_id = {}

    def start(self):
        self.container, self.frame, self.files = load_data_from_path(self.path)
        for oid, proxy in self.container._proxies.items():
            self.real_id_to_id[id(proxy)] = oid
        for sid, filename in enumerate(self.files):
            self.file_to_sid[filename] = sid
            self.sid_to_file[sid] = filename
            self.files[filename] = ''.join(self.files[filename])

        self.frame_stack = []
        frame = self.frame
        while frame:
            self.fid_to_frame[id(frame)] = frame
            if frame.f_code.co_filename not in self.file_to_sid:
                source = {'path': frame.f_code.co_filename}
            else:
                source = {'sourceReference': self.file_to_sid[frame.f_code.co_filename]}
            self.frame_stack.append({
                'id': id(frame),
                'name': frame.f_code.co_name,
                'line': frame.f_lineno,
                'column': 0,
                'source': source
            })
            frame = frame.f_back

    def get_stack_trace(self) -> List[Dict[str, Any]]:
        return self.frame_stack

    def get_source(self, source_reference: int) -> str:
        filename = self.sid_to_file[source_reference]
        return self.files.get(filename, '')

    def get_scopes(self, frame_id: int) -> List[Dict[str, Any]]:
        frame = self.fid_to_frame.get(frame_id)
        if frame is None:
            return []
        return [
            {
                'name': 'Local',
                'presentationHint': 'locals',
                'variablesReference': id(frame.f_locals),
                'expensive': False
            },
            {
                'name': 'Global',
                'presentationHint': 'globals',
                'variablesReference': id(frame.f_globals),
                'expensive': False
            }
        ]
    
    def get_variable(self, name, variable) -> Dict[str, Any]:
        if isinstance(variable, PyObjectProxy) or is_container(type(variable)):
            variables_reference = id(variable)
        else:
            variables_reference = 0

        return {
            'name': str(name),
            'value': str(variable),
            'type': str(type(variable)),
            'variablesReference': variables_reference
        }

    def get_variables(self, variables_reference: int) -> List[Dict[str, Any]]:
        if self.container is None:
            return []
        obj = self.container.get_object(self.real_id_to_id[variables_reference])

        variables = []
        if isinstance(obj, dict):
            it = obj.items()
        elif isinstance(obj, PyObjectProxy):
            it = {attr: getattr(obj, attr) for attr in dir(obj)}
        elif isinstance(obj, (set, frozenset, list, tuple)):
            it = enumerate(obj)
        else:
            print("unexpected type", type(obj))
            return []
        
        for key, value in it:
            variables.append(self.get_variable(key, value))

        return variables

    def stop(self):
        pass


def run_server():
    server = DebugAdapterServer()
    
    def signal_handler(sig, frame):
        print("\nReceived Ctrl+C, shutting down...")
        server.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    run_server()
    sys.exit(0)
