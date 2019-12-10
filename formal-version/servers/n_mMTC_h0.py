import sys
import json
import threading
import socket

from h2.connection import H2Connection
from h2.events import RequestReceived
from hyper import HTTP20Connection

# Test Mode:    Listen: localhost:9006
#               Foward: localhost:9010
# Otherwise:    Listen: 10.0.2.3:8080
#               Foward: 10.0.3.4:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
LISTEN_PORT = 9006 if TEST_MODE else 8080
SEND_PORT = 9010 if TEST_MODE else 8080

LOCK = threading.Lock()


class NFVeMBBConnection(object):
    "An object of simple HTTP/2 connection"

    def __init__(self, sock, TEST_MODE, lock):
        self.sock = sock
        self.TEST_MODE = TEST_MODE
        self.lock = lock
        self.conn = H2Connection(client_side=False)

        # Space for incoming request headers
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
                    self.rx_headers = event.headers
                    self.stream_id = event.stream_id

            # Foward request, wait for its response, then send response to where this request from
            if self.rx_headers:
                self.send_response()
                self.foward_request()

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

    def send_response(self):
        body = json.dumps({'Content': 'Recieved by NFVSM'}).encode('utf-8')
        self.conn.send_headers(
            stream_id=self.stream_id,
            headers=[
                (':status', '200'),
                ('server', 'n_mMTC-h2-server/1.0'),
                ('content-length', str(len(body))),
                ('content-type', 'application/json'),
                ('id', str(dict(self.rx_headers)['id']))
            ],
        )
        self.conn.send_data(
            stream_id=self.stream_id,
            data=body,
            end_stream=True
        )

    def foward_request(self):
        send_conn = HTTP20Connection(
            'localhost:9010' if self.TEST_MODE else '10.0.3.4:8080')
        fw_body = json.dumps({
            'SBA_ENTITY': ['AMF', 'NRF', 'AUSF', 'UDM', 'PCF', 'SMF'],
            'MODE': {
                'AMF': 'WAITABLE',
                'NRF': 'REGULAR',
                'AUSF': 'WAITABLE',
                'UDM': 'REGULAR',
                'PCF': 'REGULAR',
                'SMF': 'FAST'
            }
        }).encode('utf-8')
        send_conn.request(
            'POST', '/', headers=dict(self.rx_headers), body=fw_body)
        resp = send_conn.get_response()
        if resp:
            self.lock.acquire()
            print('Fowarded packet to SBAES')
            self.res_body = resp.read()
            print('FW Header: {}'.format(dict(self.rx_headers)))
            print('FW Body: {}'.format(fw_body))
            print('Response: {}'.format(self.res_body))
            print('==========FW')
            self.lock.release()


print('NFV Service mMTC server started at http://{}:{}'.format(
    '0.0.0.0' if TEST_MODE else '10.0.2.3', LISTEN_PORT))
print('Packet will foward to SBA Entity AMF at http://{}:{}'.format(
    '0.0.0.0' if TEST_MODE else '10.0.3.4', SEND_PORT))

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', int(LISTEN_PORT)))
sock.listen(5)

while True:
    try:
        connection = NFVeMBBConnection(sock.accept()[0], TEST_MODE, LOCK)
        th = threading.Thread(target=connection.run_forever)
        th.start()
    except(SystemExit, KeyboardInterrupt):
        break
