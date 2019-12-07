import eventlet
import sys
import json

from h2.connection import H2Connection
from h2.events import RequestReceived
from hyper import HTTP20Connection

# Test Mode:    Listen: localhost:9005
#               Foward: localhost:9010
# Otherwise:    Listen: 10.0.2.2:8080
#               Foward: 10.0.3.4:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
LISTEN_PORT = 9005 if TEST_MODE else 8080
SEND_PORT = 9010 if TEST_MODE else 8080


class NFVeMBBConnection(object):
    "An object of simple HTTP/2 connection"

    def __init__(self, sock, TEST_MODE):
        self.sock = sock
        self.TEST_MODE = TEST_MODE
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
                    print(dict(self.rx_headers))

            # Foward request, wait for its response, then send response to where this request from
            if self.rx_headers:
                self.send_response()
                self.foward_request()
                print('----------')

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

    def send_response(self):
        body = json.dumps({'Content': 'Recieved by NFVSM'}).encode('utf-8')
        self.conn.send_headers(
            stream_id=self.stream_id,
            headers=[
                (':status', '200'),
                ('server', 'n_eMBB-h2-server/1.0'),
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
            'SBA_ENTITY': ['AMF', 'NRF', 'AUSF', 'UDM', 'PCF', 'AF', 'SMF'],
            'MODE': {
                'AMF': 'FAST',
                'NRF': 'REGULAR',
                'AUSF': 'REGULAR',
                'UDM': 'REGULAR',
                'PCF': 'WAITABLE',
                'AF': 'FAST',
                'SMF': 'FAST'
            }
        }).encode('utf-8')
        send_conn.request(
            'POST', '/', headers=dict(self.rx_headers), body=fw_body)
        resp = send_conn.get_response()
        if resp:
            print('Fowarded packet to SBAES')
            self.res_body = resp.read()
            print('Header: {}'.format(dict(self.rx_headers)))
            print('Body: {}'.format(fw_body))
            print('Response: {}'.format(self.res_body))


print('NFV Service eMBB server started at http://{}:{}'.format(
    '0.0.0.0' if TEST_MODE else '10.0.2.2', LISTEN_PORT))
print('Packet will foward to SBA Entity AMF at http://{}:{}'.format(
    '0.0.0.0' if TEST_MODE else '10.0.3.4', SEND_PORT))

sock = eventlet.listen(('0.0.0.0', int(LISTEN_PORT)))
pool = eventlet.GreenPool()

while True:
    try:
        connection = NFVeMBBConnection(sock.accept()[0], TEST_MODE)
        pool.spawn_n(connection.run_forever)
    except(SystemExit, KeyboardInterrupt):
        break
