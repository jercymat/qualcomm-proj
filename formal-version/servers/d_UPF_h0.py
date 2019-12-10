import sys
import json
import threading
import socket

from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived
from hyper import HTTP20Connection

# Test Mode:    Listen: localhost:9002
#               Foward: localhost:9003
# Otherwise:    Listen: 10.0.4.1:8080
#               Foward: 10.0.5.1:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
LISTEN_PORT = 9002 if TEST_MODE else 8080
SEND_PORT = 9003 if TEST_MODE else 8080


class UPF(object):
    "An object of simple HTTP/2 connection"

    # control plane packet buffer database
    CP_BUFFER = []

    def __init__(self, sock, TEST_MODE):
        self.sock = sock
        self.TEST_MODE = TEST_MODE
        self.conn = H2Connection(client_side=False)

        # Space for incoming request headers and body
        self.rx_headers = False
        self.rx_body = False
        self.stream_id = False

        self.cp = False  # True when this pkt is from control plane, false when user plane

        # Sapce for response headers and body
        self.res_headers = False
        self.res_rxts = False
        self.res_body = False

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
                    print(dict(self.rx_headers))
                elif isinstance(event, DataReceived):
                    self.rx_body = event.data
                    print(self.rx_body)

            # Check if packet is from UP or CP and do the right thing
            if self.rx_headers and self.rx_body:
                if dict(self.rx_headers)['plane'] == 'control':
                    self.cp = True
                    self.buffer_control_plane_pkt()
                    self.send_response()
                elif dict(self.rx_headers)['plane'] == 'user':
                    self.cp = False
                    # Wait until control packet comes
                    # while True:
                    #     if self.control_plane_buffer_status() == 'SUCCESS':
                    #         break
                    self.foward_request()
                    self.send_response()
                print('----------')

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

    def buffer_control_plane_pkt(self):
        pkt_id = str(dict(self.rx_headers)['id'])
        body_json = json.loads(self.rx_body)
        print('RESULT DICT: {}'.format(body_json['RESULT']))
        # check if all result is true
        result = all(x for x in body_json['RESULT'].values())
        print('RESULT: {}'.format(result))
        pkt_buffer = {
            'id': pkt_id,
            'RESULT': result
        }
        UPF.CP_BUFFER.append(pkt_buffer)

    def control_plane_buffer_status(self):
        """
        Check control plane buffer and return status

        NOT FOUND: Current UP packet id not found in CP buffer
        SUCCESS: Current UP packet id found in CP buffer and result is good
        FAIL: Current UP packet id found in CP buffer but result is bad
        """
        pkt_id = str(dict(self.rx_headers)['id'])
        found_idx = -1
        status = 'NOT FOUND'

        for idx, buffer in enumerate(UPF.CP_BUFFER):
            if buffer['id'] == pkt_id:
                if buffer['RESULT']:
                    status = 'SUCCESS'
                else:
                    status = 'FAIL'

                found_idx = idx
                break

        if found_idx != -1:
            del UPF.CP_BUFFER[found_idx]

        return status

    def send_response(self):
        body = json.dumps({'Content': 'Recieved by UPF'}).encode('utf-8') if self.cp else self.res_body
        headers = [
            (':status', '200'),
            ('server', 'dp_UPF-h2-server/1.0'),
            ('content-length', str(len(body))),
            ('content-type', 'application/json')
        ]
        if not self.cp:
            headers.append(('rx-timestamp', self.res_rxts))

        self.conn.send_headers(
            stream_id=self.stream_id,
            headers=headers
        )
        self.conn.send_data(
            stream_id=self.stream_id,
            data=body,
            end_stream=True
        )

    def foward_request(self):
        send_conn = HTTP20Connection('0.0.0.0:9003' if self.TEST_MODE else '10.0.5.1:8080')
        send_conn.request('POST', '/', headers=dict(self.rx_headers), body=self.rx_body)
        resp = send_conn.get_response()
        if resp:
            print('Fowarded this request to DN and got response')
            self.res_body = resp.read()
            self.res_rxts = resp.headers['rx-timestamp'][0]


print('Data Plane UPF server started at http://{}:{}'.format('0.0.0.0' if TEST_MODE else '10.0.4.1', LISTEN_PORT))
print('Packets will foward to http://{}:{}'.format('localhost' if TEST_MODE else '10.0.5.1', SEND_PORT))

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', int(LISTEN_PORT)))
sock.listen(5)

while True:
    try:
        connection = UPF(sock.accept()[0], TEST_MODE)
        th = threading.Thread(target=connection.run_forever)
        th.start()
    except(SystemExit, KeyboardInterrupt):
        break
