import sys
import threading
import socket

from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived
from hyper import HTTP20Connection

# Test Mode:    Listen: localhost:9001
#               Data Plane: localhost:9002
#               Control Plane: localhost:9004,9005,9006
# Otherwise:    Listen: 10.0.1.1:8080
#               Data Plane: 10.0.4.1:8080
#               Control Plane: 10.0.2.1,2,3:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
LISTEN_PORT = 9001 if TEST_MODE else 8080

LOCK = threading.Lock()


class UAMConnection(object):
    "An object of simple HTTP/2 connection"

    def __init__(self, sock, TEST_MODE, lock):
        self.sock = sock
        self.TEST_MODE = TEST_MODE
        self.lock = lock
        self.conn = H2Connection(client_side=False)

        # Packet datas
        self.rx_headers = False
        self.rx_body = False
        self.rx_scenario = False
        self.stream_id = False
        self.res_rxts = False  # rx-timestamp from data network

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
                    self.rx_scenario = str(dict(self.rx_headers)['scenario'])
                    self.stream_id = event.stream_id
                elif isinstance(event, DataReceived):
                    self.rx_body = event.data

            # Foward request, wait for its response, then send response to where this request from
            if self.rx_headers and self.rx_body and self.rx_scenario:
                self.foward_data_plane_packet()
                self.send_control_plane_packet()
                self.send_response()

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

    def send_response(self):
        self.conn.send_headers(
            stream_id=self.stream_id,
            headers=[
                (':status', '200'),
                ('server', 'dp_DN-h2-server/1.0'),
                ('content-length', str(len(self.res_body))),
                ('content-type', 'application/json'),
                ('rx-timestamp', self.res_rxts)
            ],
        )
        self.conn.send_data(
            stream_id=self.stream_id,
            data=self.res_body,
            end_stream=True
        )

    def send_control_plane_packet(self):
        "Generate a control plane packet and send to NFV Services"
        ip = {
            'URLLC': 'localhost:9004',
            'eMBB': 'localhost:9005',
            'mMTC': 'localhost:9006'
        } if self.TEST_MODE else {
            'URLLC': '10.0.2.1:8080',
            'eMBB': '10.0.2.2:8080',
            'mMTC': '10.0.2.3:8080'
        }
        scenario = self.rx_scenario
        send_headers = {
            'id': str(dict(self.rx_headers)['id'])
        }
        send_conn = HTTP20Connection(ip[scenario])
        send_conn.request('GET', '/', headers=send_headers)
        resp = send_conn.get_response()
        if resp:
            self.lock.acquire()
            print('Sent control plane packet to NFV {} Service at {}'.format(scenario, ip[scenario]))
            print('CP FW Header: {}'.format(send_headers))
            print('Response: {}'.format(resp.read()))
            print('==========CP-FW')
            self.lock.release()

    def foward_data_plane_packet(self):
        "Duplicate a data plane packet and send to UPF"
        upf_ip = 'localhost:9002' if self.TEST_MODE else '10.0.4.1:8080'
        fw_headers = {
            'content-length': str(len(self.rx_body)),
            'content-type': 'application/json',
            'id': str(dict(self.rx_headers)['id']),
            'plane': 'user'
        }
        send_conn = HTTP20Connection('{}'.format(upf_ip))
        send_conn.request('POST', '/', headers=fw_headers, body=self.rx_body)
        resp = send_conn.get_response()
        if resp:
            self.lock.acquire()
            print('Fowarded User Plane packet to UPF')
            print('UP FW Header: {}'.format(fw_headers))
            print('UP FW Body: {}'.format(self.rx_body))
            self.res_body = resp.read()
            print('Response: {}'.format(self.res_body))
            self.res_rxts = resp.headers['rx-timestamp'][0]
            print('==========UP-FW')
            self.lock.release()


print('UAM server started at http://{}:{}'.format('0.0.0.0' if TEST_MODE else '10.0.1.1', LISTEN_PORT))
print('Packets will foward to {}'.format('test server' if TEST_MODE else 'NFVSM'))

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', int(LISTEN_PORT)))
sock.listen(5)

while True:
    try:
        connection = UAMConnection(sock.accept()[0], TEST_MODE, LOCK)
        th = threading.Thread(target=connection.run_forever)
        th.start()
    except(SystemExit, KeyboardInterrupt):
        break
