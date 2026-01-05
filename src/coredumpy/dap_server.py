# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import json
import os
import signal
import socket
import sys
import threading
import traceback
from collections import namedtuple
from types import FrameType
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
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

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
        buffer = b""
        while self.running:
            try:
                self.client.settimeout(0.5)
                try:
                    data = self.client.recv(4096)
                    if not data:
                        break

                    buffer += data
                    while b'\r\n\r\n' in buffer:
                        header, rest = buffer.split(b'\r\n\r\n', 1)
                        content_length = 0

                        for line in header.split(b'\r\n'):
                            if line.startswith(b'Content-Length: '):
                                content_length = int(line.split(b': ')[1])

                        if len(rest) >= content_length:
                            content = rest[:content_length]
                            buffer = rest[content_length:]
                            self.process_message(json.loads(content.decode("utf-8")))
                        else:
                            break
                except socket.timeout:  # pragma: no cover
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
                    thread_id = 0
                    program = message.get('arguments', {}).get('program', '')
                    if program:
                        self.debugger = CoredumpyDebugger(program)
                        self.debugger.start()
                        thread_id = int(self.debugger.current_thread)
                    self.send_response(message, {})
                    self.send_event('stopped', {'reason': 'entry', 'threadId': thread_id, 'allThreadsStopped': True})
                elif command == 'threads':
                    if self.debugger:
                        threads = self.debugger.get_threads()
                    else:
                        threads = []
                    self.send_response(message, {'threads': threads})
                elif command == 'stackTrace':
                    if self.debugger:
                        stack_frames = self.debugger.get_stack_trace(message.get('arguments', {}).get('threadId', 0))
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
                elif command == 'evaluate':
                    frame_id = message.get('arguments', {}).get('frameId', 0)
                    expression = message.get('arguments', {}).get('expression', '')
                    if self.debugger:
                        result = self.debugger.get_evaluate(frame_id, expression)
                    else:
                        result = ""
                    self.send_response(message, {'result': result, 'variablesReference': 0})
                elif command in ('continue', 'next', 'stepIn', 'stepOut'):
                    if self.debugger:
                        thread_id = int(self.debugger.current_thread)
                    else:
                        thread_id = 0
                    self.send_response(message, {})
                    self.send_event('stopped', {'reason': 'entry', 'threadId': thread_id, 'allThreadsStopped': True})
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
            extra = "".join(traceback.format_exception(e))
            self.send_error_response(message, extra)

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


class IdAdapter:
    # id is the id of the object in the current process
    # oid is the id of the object in the original dumped process
    # rid is the reference id of the object to DAP clients
    Container = namedtuple('Container', ['id', 'oid', 'rid', 'value'])

    def __init__(self) -> None:
        self._id_index: Dict[int, IdAdapter.Container] = {}
        self._oid_index: Dict[int, IdAdapter.Container] = {}
        self._rid_index: Dict[int, IdAdapter.Container] = {}
        self._rid = 1

    def add(self, obj, oid):
        _id = id(obj)
        if _id not in self._id_index:
            container = self.Container(id=_id, oid=oid, rid=self._rid, value=obj)
            self._id_index[_id] = container
            self._oid_index[oid] = container
            self._rid_index[self._rid] = container
            self._rid += 1

    def object_to_rid(self, obj):
        _id = id(obj)
        if _id in self._id_index:
            return self._id_index[_id].rid
        return 0  # pragma: no cover

    def rid_to_object(self, rid):
        if rid in self._rid_index:
            return self._rid_index[rid].value
        return None


class CoredumpyDebugger:
    def __init__(self, path: str):
        self.path = path
        self.container: Optional[PyObjectContainer] = None
        self.files: Dict[str, str] = {}
        self.threads: Dict[str, Dict[str, Any]] = {}
        self.current_thread: str = ''
        self.sid_to_file: Dict[int, str] = {}
        self.file_to_sid: Dict[str, int] = {}
        self.frame_stacks: Dict[str, List[Dict]] = {}
        self.id_adapter = IdAdapter()

    def start(self) -> None:
        data = load_data_from_path(self.path)
        self.container = data["container"]
        self.files = data["files"]
        self.threads = data["threads"]
        self.current_thread = data["current_thread"]
        assert isinstance(self.container, PyObjectContainer)
        for oid, proxy in self.container._proxies.items():
            self.id_adapter.add(proxy, oid)
        for sid, filename in enumerate(self.files, 1):
            self.file_to_sid[filename] = sid
            self.sid_to_file[sid] = filename
            self.files[filename] = ''.join(self.files[filename])

        self.frame_stacks = {}
        for thread in self.threads:
            self.frame_stacks[thread] = []
            frame: FrameType = self.threads[thread]["frame"]
            while frame:
                source_reference = self.file_to_sid.get(frame.f_code.co_filename, 0)
                source = {
                    'path': os.path.basename(frame.f_code.co_filename),
                    'sourceReference': source_reference,
                    'presentationHint': 'normal' if source_reference != 0 else 'deemphasize'
                }
                self.frame_stacks[thread].append({
                    'id': self.id_adapter.object_to_rid(frame),
                    'name': frame.f_code.co_name,
                    'line': frame.f_lineno,
                    'column': 0,
                    'source': source
                })
                frame = frame.f_back  # type: ignore

    def get_threads(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': int(thread),
                'name': self.threads[thread].get('name', 'Thread'),
            }
            for thread in self.threads
        ]

    def get_stack_trace(self, thread_id: int) -> List[Dict[str, Any]]:
        return self.frame_stacks.get(str(thread_id), [])

    def get_source(self, source_reference: int) -> str:
        if source_reference not in self.sid_to_file:
            return 'source code unavailable'
        filename = self.sid_to_file[source_reference]
        return self.files.get(filename, 'source code unavailable')

    def get_scopes(self, frame_id: int) -> List[Dict[str, Any]]:
        frame = self.id_adapter.rid_to_object(frame_id)
        if frame is None:
            return []
        return [
            {
                'name': 'Local',
                'presentationHint': 'locals',
                'variablesReference': self.id_adapter.object_to_rid(frame.f_locals),
                'expensive': False
            },
            {
                'name': 'Global',
                'presentationHint': 'globals',
                'variablesReference': self.id_adapter.object_to_rid(frame.f_globals),
                'expensive': False
            }
        ]

    def get_variable(self, name, variable) -> Dict[str, Any]:
        if isinstance(variable, PyObjectProxy) or is_container(type(variable)):
            variables_reference = self.id_adapter.object_to_rid(variable)
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
        obj = self.id_adapter.rid_to_object(variables_reference)

        variables = []
        it: Iterable
        if isinstance(obj, dict):
            it = obj.items()
        elif isinstance(obj, PyObjectProxy):
            it = {attr: getattr(obj, attr) for attr in dir(obj)}.items()
        elif isinstance(obj, (set, frozenset, list, tuple)):
            it = enumerate(obj)
        elif isinstance(obj, getattr(sys.modules.get("torch"), "Tensor", type(None))):
            import torch
            assert isinstance(obj, torch.Tensor)
            if obj.dim() == 1:
                it = {i: t.item() for i, t in enumerate(obj)}.items()
            else:
                data = {}
                for i, t in enumerate(obj):
                    self.id_adapter.add(t, id(t))
                    data[i] = t
                it = data.items()
        else:  # pragma: no cover
            print("unexpected type", type(obj))
            return []

        for key, value in it:
            variables.append(self.get_variable(key, value))

        return variables

    def get_evaluate(self, frame_id: int, expression: str) -> str:
        frame = self.id_adapter.rid_to_object(frame_id)
        if not frame:
            return ""

        f_locals = frame.f_locals
        f_globals = frame.f_globals

        try:
            return str(eval(expression, f_globals, f_locals))
        except SyntaxError:
            try:
                exec(expression, f_globals, f_locals)
            except Exception as e:
                return "".join(traceback.format_exception_only(e))
        except Exception as e:
            return "".join(traceback.format_exception_only(e))

        return ""

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
