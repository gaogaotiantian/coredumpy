# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import json
import signal
import socket
import threading
from typing import Any, Dict, Iterable, List, Optional

from .coredumpy import load_data_from_path
from .py_object_proxy import PyObjectProxy
from .py_object_container import PyObjectContainer
from .type_support import is_container


class DebugAdapterServer:
    def __init__(self, host: str = 'localhost', port: int = 6742):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        self.client_threads: List[DebugAdapterHandler] = []

    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(1)
            print(f"[Server] Debug adapter server successfully bound to {self.host}:{self.port}", flush=True)
            print("[Server] Server socket created and listening for connections", flush=True)
            print("[Server] Press Ctrl+C to exit", flush=True)
        except Exception as e:  # pragma: no cover
            print(f"[Server] Error binding server: {e}", flush=True)
            return

        while self.running:
            try:
                self.server.settimeout(0.5)
                try:
                    client, addr = self.server.accept()
                    print(f"[Server] New client connection accepted from {addr}", flush=True)
                    client_thread = DebugAdapterHandler(self, client)
                    client_thread.start()
                    self.client_threads.append(client_thread)
                    print(f"[Server] Started client handler thread for {addr}", flush=True)
                except socket.timeout:
                    self.update_client_threads()
                    continue
            except Exception as e:  # pragma: no cover
                if self.running:
                    print(f"Error in server loop: {e}")
                break

        self.shutdown()

    def update_client_threads(self):
        for client_thread in self.client_threads[:]:
            if not client_thread.is_alive():
                self.client_threads.remove(client_thread)

    def shutdown(self):
        self.running = False

        for thread in self.client_threads[:]:
            try:
                thread.close()
            except Exception:  # pragma: no cover
                pass

        try:
            self.server.close()
        except Exception:  # pragma: no cover
            pass


class DebugAdapterHandler(threading.Thread):
    def __init__(self, server: DebugAdapterServer, client: socket.socket):
        super().__init__(daemon=True)
        self.client = client
        self.running = True
        self.sequence = 1
        self.debugger: Optional[CoredumpyDebugger] = None

    def run(self):
        print("[Client] Client handler started", flush=True)
        buffer = ""
        while self.running:
            try:
                self.client.settimeout(0.5)
                try:
                    data = self.client.recv(4096).decode('utf-8')
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
                            self.process_message(json.loads(content))
                        else:
                            break
                except socket.timeout:
                    continue
            except Exception as e:  # pragma: no cover
                if self.running:
                    print(f"Error handling client: {e}")
                break

        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass

    def process_message(self, message: Dict[str, Any]):
        try:
            print("[Client] Processing message:", message, flush=True)
            if message.get('type') == 'request':
                command = message.get('command')
                if command == 'initialize':
                    # We don't really support anything
                    self.send_response(message, {})
                    self.send_event('initialized', {})
                elif command == 'launch':
                    program = message.get('arguments', {}).get('program', '')
                    if program:
                        self.debugger = CoredumpyDebugger(program)
                        self.debugger.start()
                    self.send_response(message, {})
                    self.send_event('stopped', {'reason': 'entry', 'threadId': 1})
                elif command == 'threads':
                    self.send_response(message, {'threads': [{'id': 1, 'name': 'Thread 1'}]})
                elif command == 'stackTrace':
                    if self.debugger:
                        stack_frames = self.debugger.get_stack_trace()
                    else:
                        stack_frames = []
                    self.send_response(message, {'stackFrames': stack_frames, 'totalFrames': len(stack_frames)})
                elif command == 'source':
                    source_reference = message.get('arguments', {}).get('sourceReference', 0)
                    if self.debugger:
                        source = self.debugger.get_source(source_reference)
                    else:
                        source = ""
                    self.send_response(message, {'content': source, 'mimeType': 'text/x-python'})
                elif command == 'scopes':
                    frame_id = message.get('arguments', {}).get('frameId', 0)
                    if self.debugger:
                        scopes = self.debugger.get_scopes(frame_id)
                    else:
                        scopes = []
                    self.send_response(message, {'scopes': scopes})
                elif command == 'variables':
                    variables_reference = message.get('arguments', {}).get('variablesReference', 0)
                    if self.debugger:
                        variables = self.debugger.get_variables(variables_reference)
                    else:
                        variables = []
                    self.send_response(message, {'variables': variables})
                elif command == 'disconnect':
                    if self.debugger:
                        self.debugger.stop()
                        self.debugger = None
                    self.send_response(message, {})
                    self.send_event('exited', {'exitCode': 0})
                    self.running = False
                else:
                    self.send_response(message, {})

        except Exception as e:
            self.send_error_response(message, str(e))

    def send_message(self, message: Dict[str, Any]):
        print("[Client] Sending message:", message, flush=True)
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        self.client.send(header.encode('utf-8'))
        self.client.send(content.encode('utf-8'))

    def send_response(self, request: Dict[str, Any], body: Dict[str, Any]):
        self.send_message({
            'type': 'response',
            'request_seq': request.get('seq', 0),
            'success': True,
            'command': request.get('command', ''),
            'body': body
        })

    def send_error_response(self, request: Dict[str, Any], message: str):
        self.send_message({
            'type': 'response',
            'request_seq': request.get('seq', 0),
            'success': False,
            'command': request.get('command', ''),
            'message': message
        })

    def send_event(self, event: str, body: Dict[str, Any]):
        self.send_message({
            'type': 'event',
            'event': event,
            'seq': self.sequence,
            'body': body
        })
        self.sequence += 1

    def close(self):
        self.running = False
        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass
        print("[Client] Client handler closed", flush=True)


class CoredumpyDebugger:
    def __init__(self, path: str):
        self.path = path
        self.process = None
        self.current_line = 0
        self.current_file = ''
        self.container: Optional[PyObjectContainer] = None
        self.frame = None
        self.files: Dict[str, str] = {}
        self.sid_to_file: Dict[int, str] = {}
        self.file_to_sid: Dict[str, int] = {}
        self.fid_to_frame: Dict[int, Any] = {}
        self.frame_stack: List[Dict] = []
        self.real_id_to_id: Dict[int, str] = {}

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
        if self.container is None:  # pragma: no cover
            return []
        obj = self.container.get_object(self.real_id_to_id[variables_reference])

        variables = []
        it: Iterable
        if isinstance(obj, dict):
            it = obj.items()
        elif isinstance(obj, PyObjectProxy):
            it = {attr: getattr(obj, attr) for attr in dir(obj)}.items()
        elif isinstance(obj, (set, frozenset, list, tuple)):
            it = enumerate(obj)
        else:  # pragma: no cover
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
    except Exception as e:  # pragma: no cover
        print(f"Unexpected error: {e}")
