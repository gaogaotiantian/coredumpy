# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest

from .base import TestBase
from .util import normalize_commands


DEBUG_PRINT = os.getenv("GITHUB_ACTIONS", None) is None


class DapServer:
    def __init__(self):
        self._process = None

    def __enter__(self):
        self._process = subprocess.Popen(
            normalize_commands(["coredumpy", "host"]),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        line = self._process.stdout.readline()
        line = self._process.stdout.readline()
        if b"listening for connections" not in line:
            self._process.terminate()
            self._process.wait()
            raise RuntimeError("Failed to start DAP server")

        # This is necessary because it could block the server
        self._stdout_releaser = threading.Thread(target=self.release_pipe, args=(self._process.stdout, ))
        self._stdout_releaser.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process.stdout.close()
            self._process = None
            self._stdout_releaser.join()

    def release_pipe(self, pipe):
        for line in pipe:
            pass

    def kill(self):
        self._process.send_signal(signal.SIGINT)
        self._process.wait()
        self._process.stdout.close()
        self._process = None


class DapClient:
    def __init__(self):
        self.host = "localhost"
        self.port = 6742
        self.seq = 1
        self.message_gen = None

    def __enter__(self):
        self.sock = socket.create_connection((self.host, self.port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_message(self, message):
        """Serialize and send a DAP message with the required headers."""
        assert self.sock is not None, "Socket is not connected"
        json_message = json.dumps(message, ensure_ascii=False)
        content_bytes = json_message.encode("utf-8")
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
        self.sock.sendall(header.encode("utf-8") + content_bytes)
        self.seq += 1

    def send_messages(self, messages):
        """Send multiple DAP messages in one go."""
        assert self.sock is not None, "Socket is not connected"
        data = b""
        for message in messages:
            # ensure_ascii=False to simulate how VSCode works
            json_message = json.dumps(message, ensure_ascii=False)
            content_bytes = json_message.encode("utf-8")
            header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
            data += header.encode("utf-8") + content_bytes
            self.seq += 1
        self.sock.sendall(data)

    def receive_messages(self):
        """Continuously read and process DAP messages from the socket."""
        buffer = b""
        assert self.sock is not None, "Socket is not connected"
        while True:
            data = self.sock.recv(4096)
            if not data:
                # Socket closed by the server.
                break
            buffer += data
            while b"\r\n\r\n" in buffer:
                # Split headers and the rest of the data.
                header_part, rest = buffer.split(b"\r\n\r\n", 1)
                # Parse Content-Length from header.
                match = re.search(rb"Content-Length: (\d+)", header_part)
                if not match:
                    raise ValueError("Missing Content-Length header in DAP message")
                content_length = int(match.group(1))
                if len(rest) < content_length:
                    # Wait for the full message to be received.
                    break
                json_bytes = rest[:content_length]
                try:
                    message = json.loads(json_bytes.decode("utf-8"))
                    if DEBUG_PRINT:
                        print("Received DAP message:", message)
                    yield message
                except json.JSONDecodeError as e:
                    print("Failed to decode JSON message:", e)
                # Remove the processed message from the buffer.
                buffer = rest[content_length:]

    def get_message(self):
        if self.message_gen is None:
            self.message_gen = self.receive_messages()
        return next(self.message_gen)

    def send_initialize(self):
        """Send an 'initialize' request to the DAP server."""
        initialize_request = {
            "type": "request",
            "seq": self.seq,
            "command": "initialize",
            "arguments": {
                "clientID": "coredumpy",
                "clientName": "CoreDumpy",
                "adapterID": "python",
                "pathFormat": "path",
                "linesStartAt1": True,
                "columnsStartAt1": True,
                "supportsVariableType": True,
                "supportsRunInTerminalRequest": False,
                "locale": "en-US"
            }
        }
        self.send_message(initialize_request)

    def send_launch(self, dump_path):
        """Send a 'launch' request to the DAP server."""
        launch_request = {
            "type": "request",
            "seq": self.seq,
            "command": "launch",
            "arguments": {
                "name": "coredumpy",
                "type": "python",
                "request": "launch",
                "program": dump_path,
                "cwd": "",
                "env": {},
                "console": "internalConsole"
            }
        }
        self.send_message(launch_request)

    def send_launch_continue(self, dump_path):
        """Send a 'launch' request and a 'continue' request to the DAP server."""
        launch_request = {
            "type": "request",
            "seq": self.seq,
            "command": "launch",
            "arguments": {
                "name": "coredumpy",
                "type": "python",
                "request": "launch",
                "program": dump_path,
                "cwd": "",
                "env": {},
                "console": "internalConsole"
            }
        }

        continue_request = {
            "type": "request",
            "seq": self.seq + 1,
            "command": "continue",
            "arguments": {
                "threadId": 1
            }
        }
        self.send_messages([launch_request, continue_request])

    def send_threads(self):
        """Send a 'threads' request to the DAP server."""
        threads_request = {
            "type": "request",
            "seq": self.seq,
            "command": "threads"
        }
        self.send_message(threads_request)

    def send_stack_trace(self, thread_id: int):
        """Send a 'stackTrace' request to the DAP server."""
        stack_trace_request = {
            "type": "request",
            "seq": self.seq,
            "command": "stackTrace",
            "arguments": {
                "threadId": thread_id,
                "startFrame": 0,
                "levels": 20
            }
        }
        self.send_message(stack_trace_request)

    def send_source(self, source_reference):
        """Send a 'source' request to the DAP server."""
        source_request = {
            "type": "request",
            "seq": self.seq,
            "command": "source",
            "arguments": {
                "sourceReference": source_reference
            }
        }
        self.send_message(source_request)

    def send_scope(self, frame_id):
        """Send a 'scope' request to the DAP server."""
        scope_request = {
            "type": "request",
            "seq": self.seq,
            "command": "scopes",
            "arguments": {
                "frameId": frame_id
            }
        }
        self.send_message(scope_request)

    def send_variables(self, variables_reference):
        """Send a 'variables' request to the DAP server."""
        variables_request = {
            "type": "request",
            "seq": self.seq,
            "command": "variables",
            "arguments": {
                "variablesReference": variables_reference
            }
        }
        self.send_message(variables_request)

    def send_evaluate(self, frame_id, expression):
        """Send an 'evaluate' request to the DAP server."""
        evaluate_request = {
            "type": "request",
            "seq": self.seq,
            "command": "evaluate",
            "arguments": {
                "frameId": frame_id,
                "expression": expression
            }
        }
        self.send_message(evaluate_request)

    def send_continue(self):
        """Send a 'continue' request to the DAP server."""
        continue_request = {
            "type": "request",
            "seq": self.seq,
            "command": "continue",
            "arguments": {
                "threadId": 1
            }
        }
        self.send_message(continue_request)

    def send_disconnect(self):
        """Send a 'disconnect' request to the DAP server."""
        disconnect_request = {
            "type": "request",
            "seq": self.seq,
            "command": "disconnect",
            "arguments": {
                "restart": False
            }
        }
        self.send_message(disconnect_request)

    def send_nonexist(self, args=None):
        """Send a non-existent request to the DAP server."""
        if args is None:
            args = {}
        nonexist_request = {
            "type": "request",
            "seq": self.seq,
            "command": "nonexist",
            "arguments": args
        }
        self.send_message(nonexist_request)


class PrepareDapTest(TestBase):
    def __init__(self):
        self._server = None
        self._client = None
        self._tmpdir = None

    def __enter__(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._server = DapServer()
        self._server.__enter__()
        self._client = DapClient()
        self._client.__enter__()
        return self._tmpdir.name, self._server, self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._server:
            self._server.__exit__(exc_type, exc_val, exc_tb)
        if self._client:
            self._client.__exit__(exc_type, exc_val, exc_tb)
        if self._tmpdir:
            self._tmpdir.cleanup()


class TestDapServer(TestBase):
    def do_initialize(self, client: DapClient):
        client.send_initialize()
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "initialized")

    def do_launch(self, client: DapClient, path):
        client.send_launch(path)
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "stopped")

    def do_launch_continue(self, client: DapClient, path):
        client.send_launch_continue(path)
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "stopped")
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "stopped")

    def do_threads(self, client: DapClient):
        client.send_threads()
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["threads"]

    def do_stack_trace(self, client: DapClient, thread_id: int):
        client.send_stack_trace(thread_id)
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["stackFrames"]

    def do_source(self, client: DapClient, source_reference):
        client.send_source(source_reference)
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["content"]

    def do_scope(self, client: DapClient, frame_id):
        client.send_scope(frame_id)
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["scopes"]

    def do_variables(self, client: DapClient, variables_reference):
        client.send_variables(variables_reference)
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["variables"]

    def do_evaluate(self, client: DapClient, frame_id, expression):
        client.send_evaluate(frame_id, expression)
        message = client.get_message()
        self.assertTrue(message["success"])
        return message["body"]["result"]

    def do_continue(self, client: DapClient):
        client.send_continue()
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "stopped")
        return

    def do_disconnect(self, client: DapClient):
        client.send_disconnect()
        message = client.get_message()
        self.assertTrue(message["success"])
        message = client.get_message()
        self.assertEqual(message["event"], "exited")
        return message["body"]["exitCode"]

    def do_nonexist(self, client: DapClient, args=None):
        if args is None:
            args = {}
        client.send_nonexist(args=args)
        message = client.get_message()
        self.assertTrue(message["success"])

    def get_local_variable_from_frame(self, client: DapClient, frame_id, variable):
        scopes = self.do_scope(client, frame_id)
        variables = self.do_variables(client, scopes[0]["variablesReference"])
        for var in variables:
            if var["name"] == variable:
                return var

    def get_local_variable_value_from_frame(self, client: DapClient, frame_id, variable):
        var = self.get_local_variable_from_frame(client, frame_id, variable)
        if var is not None:
            return var["value"]

    def test_run(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                class Person:
                    def __init__(self, name):
                        self.name = name
                def g(arg):
                    p = Person("Alice")
                    d = dict(name="Bob", age=30)
                    coredumpy.dump(path={repr(path)})
                    return arg
                def f():
                    x = 142857
                    y = [3, set([4, None])]
                    g(y)
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 1)
            stack_frames = self.do_stack_trace(client, threads[0]["id"])
            self.assertGreaterEqual(len(stack_frames), 3)
            self.assertEqual(stack_frames[0]["name"], "g")
            source_reference = stack_frames[0]["source"]["sourceReference"]

            source = self.do_source(client, source_reference)
            self.assertEqual(script, source)

            frame_id = stack_frames[0]["id"]
            self.assertLess(frame_id, 2 ** 31)
            scopes = self.do_scope(client, frame_id)
            self.assertEqual(len(scopes), 2)

            # non exist frame id
            should_be_empty_scopes = self.do_scope(client, frame_id + 12345678)
            self.assertEqual(len(should_be_empty_scopes), 0)

            self.assertLess(scopes[0]["variablesReference"], 2 ** 31)
            local_variables = self.do_variables(client, scopes[0]["variablesReference"])
            variable_names = set(var["name"] for var in local_variables)
            self.assertEqual(variable_names, {"arg", "p", "d"})

            for var in local_variables:
                variable = self.do_variables(client, var["variablesReference"])
                self.assertGreaterEqual(len(variable), 0)

            # continue should not break stuff
            self.do_continue(client)
            local_variables = self.do_variables(client, scopes[0]["variablesReference"])
            variable_names = set(var["name"] for var in local_variables)
            self.assertEqual(variable_names, {"arg", "p", "d"})

            # Let's do some eval / exec
            self.assertEqual(self.do_evaluate(client, frame_id, "d['age']"), "30")
            self.assertIn("NameError", self.do_evaluate(client, frame_id, "k"))
            self.do_evaluate(client, frame_id, "k = 5")
            self.assertEqual(self.do_evaluate(client, frame_id, "k"), "5")
            self.assertEqual(self.do_evaluate(client, frame_id, "p.name"), "Alice")
            self.do_evaluate(client, frame_id, "p.name = 'Bob'")
            self.assertEqual(self.do_evaluate(client, frame_id, "p.name"), "Bob")
            self.assertIn("SyntaxError", self.do_evaluate(client, frame_id, "p.name ="))
            # eval with wrong frame id
            self.assertEqual(self.do_evaluate(client, frame_id + 12345678, "p.name"), "")

            self.do_nonexist(client)

            self.do_nonexist(client, args={"very long arg": "test_string" * 1000})

            self.do_disconnect(client)

    def test_run_without_launch(self):
        # Make sure the server does not crash if we don't send a launch request
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                def f():
                    x = 142857
                    coredumpy.dump(path={repr(path)})
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 0)
            stack_frames = self.do_stack_trace(client, 0)
            self.assertEqual(len(stack_frames), 0)
            source = self.do_source(client, 0)
            self.assertEqual(source, "")
            scopes = self.do_scope(client, 0)
            self.assertEqual(len(scopes), 0)
            variables = self.do_variables(client, 0)
            self.assertEqual(len(variables), 0)
            self.assertEqual(self.do_evaluate(client, 0, "x"), "")
            self.do_continue(client)
            self.do_disconnect(client)

    def test_torch(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                import torch
                def f():
                    t = torch.tensor([[1, 2], [3, 4]])
                    coredumpy.dump(path={repr(path)})
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 1)
            stack_frames = self.do_stack_trace(client, threads[0]["id"])

            frame_id = stack_frames[0]["id"]
            t = self.get_local_variable_from_frame(client, frame_id, "t")
            self.assertIsNotNone(t)
            assert t is not None
            t_references = t["variablesReference"]
            sub_tensors = self.do_variables(client, t_references)
            self.assertEqual(len(sub_tensors), 2)
            tensor_0 = self.do_variables(client, sub_tensors[0]["variablesReference"])
            self.assertEqual(tensor_0[0]["name"], "0")
            self.assertEqual(tensor_0[0]["value"], "1")
            self.assertEqual(tensor_0[1]["name"], "1")
            self.assertEqual(tensor_0[1]["value"], "2")

            self.do_disconnect(client)

    def test_multithreading(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                import queue
                import threading

                def worker(q_in, q_out):
                    s = "hello"
                    q_out.put(s)
                    q_in.get()

                def main():
                    q_in = queue.Queue()
                    q_out = queue.Queue()
                    thread = threading.Thread(target=worker, args=(q_in, q_out))
                    thread.start()
                    r = q_out.get()
                    coredumpy.dump(path={repr(path)})
                    q_in.put("world")
                    thread.join()

                main()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 2)
            if threads[0]["name"] == "MainThread":
                main_thread_id = threads[0]["id"]
                worker_thread_id = threads[1]["id"]
            else:
                main_thread_id = threads[1]["id"]
                worker_thread_id = threads[0]["id"]
            main_stack_frames = self.do_stack_trace(client, main_thread_id)
            self.assertGreaterEqual(len(main_stack_frames), 2)
            worker_stack_frames = self.do_stack_trace(client, worker_thread_id)
            self.assertGreaterEqual(len(worker_stack_frames), 2)

            frame_id = main_stack_frames[0]["id"]
            r_val = self.get_local_variable_value_from_frame(client, frame_id, "r")
            self.assertEqual(r_val, "hello")
            frame_id = worker_stack_frames[2]["id"]
            s_val = self.get_local_variable_value_from_frame(client, frame_id, "s")
            self.assertEqual(s_val, "hello")

            self.do_disconnect(client)

    def test_multithreading_without_dump_all_threads(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                import queue
                import threading
                coredumpy.config.dump_all_threads = False

                def worker(q_in, q_out):
                    s = "hello"
                    q_out.put(s)
                    q_in.get()

                def main():
                    q_in = queue.Queue()
                    q_out = queue.Queue()
                    thread = threading.Thread(target=worker, args=(q_in, q_out))
                    thread.start()
                    r = q_out.get()
                    coredumpy.dump(path={repr(path)})
                    q_in.put("world")
                    thread.join()

                main()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 1)
            self.do_disconnect(client)

    def test_unicode_file(self):
        # Make sure the server does not crash if we send a unicode file
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "dump文件")
            script = textwrap.dedent(f"""
                import coredumpy
                def f():
                    x = 142857
                    coredumpy.dump(path={repr(path)})
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch_continue(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 1)
            stack_frames = self.do_stack_trace(client, threads[0]["id"])
            self.assertGreaterEqual(len(stack_frames), 2)
            x = self.get_local_variable_value_from_frame(client, stack_frames[0]["id"], "x")
            self.assertEqual(x, "142857")
            self.do_disconnect(client)

    def test_dynamic_code(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            code = f"x=142857; coredumpy.dump(path={repr(path)})"
            script = textwrap.dedent(f"""
                import coredumpy
                code = {repr(code)}
                exec(code)
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch_continue(client, path)
            threads = self.do_threads(client)
            self.assertEqual(len(threads), 1)
            stack_frames = self.do_stack_trace(client, threads[0]["id"])
            self.assertGreaterEqual(len(stack_frames), 2)
            source = stack_frames[0]["source"]
            self.assertEqual(source["sourceReference"], 0)
            self.assertEqual(source["presentationHint"], "deemphasize")

            content = self.do_source(client, source["sourceReference"])
            self.assertIn("unavailable", content)

            x = self.get_local_variable_value_from_frame(client, stack_frames[0]["id"], "x")
            self.assertEqual(x, "142857")
            self.do_disconnect(client)

    def test_launch_invalid_file(self):
        # Make sure the server does not crash if we send an invalid file
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "invalid_dump")
            self.do_initialize(client)
            with self.assertRaises(AssertionError):
                self.do_launch(client, path)
            self.do_disconnect(client)

    @unittest.skipIf(sys.platform == "win32", "Windows is just pure stupid")
    def test_kill(self):
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                def f():
                    x = 142857
                    coredumpy.dump(path={repr(path)})
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            server.kill()

    def test_kill_client(self):
        # Make sure the server does not crash if we stop the client
        with PrepareDapTest() as info:
            tmpdir, server, client = info
            path = os.path.join(tmpdir, "coredumpy_dump")
            script = textwrap.dedent(f"""
                import coredumpy
                def f():
                    x = 142857
                    coredumpy.dump(path={repr(path)})
                f()
            """)
            self.run_script(script)
            self.do_initialize(client)
            self.do_launch(client, path)
            client.sock.close()
            client.sock = None
