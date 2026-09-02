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
                    sys.executable,  # path to python
                    self.b_app_path, # path to back app
                    "bridge",
                    "--port", str(self.port),
                    "--exec",
                    "--iterations", "5" # will use default value - later cfg
                    "--backend", self.backend_mode, # TODO change it later with allow to chose
                    "--timeout", "30"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=1,
                universal_newlines=True
            )
            logging.info('[FRONT] Agent started.')
            return True
        except FileNotFoundError:
            logging.error('[FRONT] Could not find b_app_path.')
            return False

    def create_connection(self, connection_attempts=10):
        logging.info('[FRONT] Start creating connection.')
        for att in range(connection_attempts):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect(('127.0.0.1', self.port))
                self.connected = True
                logging.info('[FRONT] Connection established.')
            except ConnectionRefusedError as e:
                logging.error('[FRONT] Connection refused. Trying again.')
                time.sleep(0.5)
            except Exception as e:
                logging.error('[FRONT] Could not connect to agent.')

    def send_msg(self, msg):
        if not self.connected:
            logging.warning('[FRONT] Agent is not connected.')
            return None
        bytes = json.dumps(msg, ensure_ascii=False).encode('utf-8')
        self.socket.send(struct.pack('>I', len(bytes))) # SEND LENGTH AT FIRST
        self.socket.send(bytes) # NEXT SENDING OUT MSG
        try:
            size_data = self.socket.recv(4) # GET BYTES
            data = b''
            while len(data) < size_data:
                chunk = self.socket.recv(min(4096, size_data-len(data)))
                if not chunk:
                    raise ConnectionError('Connection closed by remote host')
                data += chunk
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logging.error('[FRONT] Could not send msg to agent.')
            return None

