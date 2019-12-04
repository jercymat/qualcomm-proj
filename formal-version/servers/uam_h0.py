import eventlet
import sys

from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived
from hyper import HTTP20Connection

PORT = sys.argv[1]
FWD_HOST = sys.argv[2]
FWD_PORT = sys.argv[3]


class FowarderConnection(object):
    "An object of simple HTTP/2 connection"

    def __init__(self, sock, fwd_host, fwd_port):
        self.sock = sock
        self.fwd_host = fwd_host
        self.fwd_port = fwd_port
        self.conn = H2Connection(client_side=False)

        # Space for incoming request headers and body
        self.rx_headers = False
        self.rx_body = False
        self.stream_id = False
        # Sapce for response headers and body
        self.res_headers = False
        self.res_rxts = False

        print('new socket')

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

            # Foward request, wait for its response, then send response to where this request from
            if self.rx_headers and self.rx_body:
                self.foward_request()
                self.send_response()
                print('----------')

            data_to_send = self.conn.data_to_send()
            if data_to_send:
                self.sock.sendall(data_to_send)

            # self.conn.end_stream(self.stream_id)

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

    def foward_request(self):
        send_conn = HTTP20Connection('{}:{}'.format(self.fwd_host, self.fwd_port))
        send_conn.request('POST', '/', headers=dict(self.rx_headers), body=self.rx_body)
        resp = send_conn.get_response()
        if resp:
            print('Fowarded this request and got response')
            self.res_body = resp.read()
            self.res_rxts = resp.headers['rx-timestamp'][0]


print('HTTP/2 server started at http://0.0.0.0:{}'.format(PORT))
print('Packets will foward to   http://{}:{}'.format(FWD_HOST, FWD_PORT))

sock = eventlet.listen(('0.0.0.0', int(PORT)))
pool = eventlet.GreenPool()

while True:
    try:
        connection = FowarderConnection(sock.accept()[0], FWD_HOST, FWD_PORT)
        pool.spawn_n(connection.run_forever)
    except(SystemExit, KeyboardInterrupt):
        break
