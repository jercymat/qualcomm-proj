import sys
import json
import time

from hyper import HTTP20Connection

HOST = sys.argv[1]
PORT = sys.argv[2] if len(sys.argv) == 3 else '8080'
PATH = sys.argv[3] if len(sys.argv) == 4 else '/'

TX_TP = 0  # Timestamp of data transmitted
RX_TP = 0  # Timestamp of data recieved by Data Network
RES_TP = 0  # Timestamp of response from Data Network ran back

data = {
    'Content': 'NCCUCS mclab testing'
}
transfer_data = json.dumps(data).encode('utf-8')
headers = {
    'content-length': str(len(transfer_data)),
    'content-type': 'application/json',
    'id': '033bd94b1168d7e4f0d644c3c95e35bf',
    'scenario': 'URLLC'
}

while True:
    conn = HTTP20Connection('{}:{}'.format(HOST, PORT))
    TX_TP = time.time().real
    conn.request('POST', '/', headers=headers, body=transfer_data)
    resp = conn.get_response()
    RES_TP = time.time().real
    RX_TP = float(resp.headers['rx-timestamp'][0])
    # print(json.dumps(dict(resp.headers), indent=4))
    # print(resp.read())
    print('TX - {:.6f} | RX - {:.6f} | RES - {:.6f}'.format(TX_TP, RX_TP, RES_TP))
    print('Transfer Time - {}ms'.format(round((RX_TP - TX_TP) * 1000, 1)))
    print('RTT - {}ms'.format(round((RES_TP - TX_TP) * 1000, 1)))
    time.sleep(1)
