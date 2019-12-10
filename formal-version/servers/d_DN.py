import json
import time
import sys
import threading
import socket

from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived

# Test Mode: Listen localhost:9003
# Otherwise: Listen 10.0.5.1:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
HOST = 'localhost' if TEST_MODE else '10.0.5.1'
LISTEN_PORT = 9003 if TEST_MODE else 8080


class RecieverConnection(object):
    "An object of simple HTTP/2 connection"

    def __init__(self, sock, TEST_MODE):
        self.sock = sock
        self.TEST_MODE = TEST_MODE
        self.conn = H2Connection(client_side=False)
        self.rx_headers = False
        self.stream_id = False

    def run_forever(self):
        self.conn.initiate_connection()
        self.sock.sendall(self.conn.data_to_send())

        while True:
            data = self.sock.recv(65535)
            if not data:
                break

            events = self.conn.receive_data(data)

            for event in events:
                if isinstance(event, RequestReceived):
                    print(dict(event.headers))
                    self.rx_headers = event.headers
                    self.stream_id = event.stream_id
                elif isinstance(event, DataReceived):
                    print(event.data)

            if self.rx_headers:
                self.send_response()

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

    def send_response(self):
        response_data = json.dumps({'Content': 'Data recieved by Data Network'})
        self.conn.send_headers(
            stream_id=self.stream_id,
            headers=[
                (':status', '200'),
                ('server', 'dp_DN-h2-server/1.0'),
                ('content-length', str(len(response_data))),
                ('content-type', 'application/json'),
                ('rx-timestamp', '{:.6f}'.format(time.time().real))
            ],
        )
        self.conn.send_data(
            stream_id=self.stream_id,
            data=response_data,
            end_stream=True
        )


print('HTTP/2 server started at http://{}:{}'.format('localhost' if TEST_MODE else '10.0.5.1', LISTEN_PORT))

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', int(LISTEN_PORT)))
sock.listen(5)

while True:
    try:
        connection = RecieverConnection(sock.accept()[0], TEST_MODE)
        th = threading.Thread(target=connection.run_forever)
        th.start()
    except(SystemExit, KeyboardInterrupt):
        break
