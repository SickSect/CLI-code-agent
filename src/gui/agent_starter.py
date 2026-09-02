import json
import logging
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path


class AgentConnector:
    def __init__(self, port=9999, b_app_path=None, backend_mode = 'subprocess'):
        self.port = port
        self.process = None # future back end listener
        self.socket = None # will init later
        self.connected = False
        self.backend_mode = backend_mode

        if b_app_path is None:
            logging.warn('[FRONT] AGent starter does not have definite b_app_path, will use default value.')
            b_app_path = Path(__file__).parent / "codeagent" / "cli.py"
            if not b_app_path.exists():
                logging.error('[FRONT] Did not find b_app_path.')
            else:
                self.b_app_path = b_app_path

    def start_agent_app(self):
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    self.b_app_path,
                    "bridge",
                    "--port", str(self.port),
                    "--exec",
                    "--iterations", "5",
                    "--backend", self.backend_mode,
                    "--timeout", "30"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=1,
                universal_newlines=True
            )

            # Запускаем потоки для чтения логов
            import threading
            threading.Thread(target=self._read_stdout, daemon=True).start()
            threading.Thread(target=self._read_stderr, daemon=True).start()

            logging.info('[FRONT] Agent started.')
            return True
        except FileNotFoundError:
            logging.error('[FRONT] Could not find b_app_path.')
            return False

    def _read_stdout(self):
        for line in iter(self.process.stdout.readline, b''):
            if line:
                logging.info(f'[AGENT STDOUT] {line.decode().strip()}')

    def _read_stderr(self):
        for line in iter(self.process.stderr.readline, b''):
            if line:
                logging.error(f'[AGENT STDERR] {line.decode().strip()}')

    # Добавь проверку в create_connection
    def create_connection(self, connection_attempts=10):
        logging.info('[FRONT] Start creating connection.')

        # Проверяем жив ли процесс
        if self.process and self.process.poll() is not None:
            logging.error(f'[FRONT] Agent process died with code: {self.process.returncode}')
            return False

        for att in range(connection_attempts):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect(('127.0.0.1', self.port))
                self.connected = True
                logging.info('[FRONT] Connection established.')
                return True
            except ConnectionRefusedError:
                logging.warning(f'[FRONT] Connection refused. Attempt {att + 1}/{connection_attempts}')
                time.sleep(0.5)
            except Exception as e:
                logging.error(f'[FRONT] Could not connect to agent: {e}')
                time.sleep(0.5)

        return False

    def send_msg(self, msg):
        if not self.connected:
            logging.warning('[FRONT] Agent is not connected.')
            return None

        logging.info(f'[FRONT] Sending message: {msg}')
        bytes = json.dumps(msg, ensure_ascii=False).encode('utf-8')
        self.socket.send(struct.pack('>I', len(bytes)))
        self.socket.send(bytes)

        try:
            size_data = self.socket.recv(4)
            if not size_data:
                logging.error('[FRONT] No data received (connection closed)')
                return None

            size = struct.unpack('>I', size_data)[0]
            logging.info(f'[FRONT] Expecting response size: {size}')

            data = b''
            while len(data) < size:
                chunk = self.socket.recv(min(4096, size - len(data)))
                if not chunk:
                    raise ConnectionError('Connection closed by remote host')
                data += chunk

            response = json.loads(data.decode('utf-8'))
            logging.info(f'[FRONT] Received response: {response}')
            return response

        except Exception as e:
            logging.error(f'[FRONT] Could not receive msg: {e}')
            return None

