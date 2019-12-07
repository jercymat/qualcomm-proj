import sys
import json
import time
import hashlib

from hyper import HTTP20Connection

# Test Mode: Send to localhost:9001
# Otherwise: Send to 10.0.1.1:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
HOST = 'localhost' if TEST_MODE else '10.0.1.1'
SEND_PORT = 9001 if TEST_MODE else 8080

TX_TP = 0  # Timestamp of data transmitted
RX_TP = 0  # Timestamp of data recieved by Data Network
RES_TP = 0  # Timestamp of response from Data Network ran back

pkt_cnt = 1

data = {
    'Content': 'NCCUCS mclab testing'
}
transfer_data = json.dumps(data).encode('utf-8')
headers = {
    'content-length': str(len(transfer_data)),
    'content-type': 'application/json',
    'scenario': 'mMTC'
}

while True:
    conn = HTTP20Connection('{}:{}'.format(HOST, SEND_PORT))

    # Add SHA256 encrypted id to header i.e. sha256('URLLC-PKT-0132')
    headers['id'] = hashlib.sha256(
        'mMTC-PKT-{:0>4d}'.format(pkt_cnt)).hexdigest()

    TX_TP = time.time().real
    conn.request('POST', '/', headers=headers, body=transfer_data)
    print('Sending mMTC packet into system')
    print('headers: {}'.format(headers))

    resp = conn.get_response()
    RES_TP = time.time().real
    RX_TP = float(resp.headers['rx-timestamp'][0])

    print(json.dumps(dict(resp.headers), indent=4))
    print(resp.read())
    print('TX - {:.6f} | RX - {:.6f} | RES - {:.6f}'.format(TX_TP, RX_TP, RES_TP))
    print('Transfer Time - {}ms'.format(round((RX_TP - TX_TP) * 1000, 1)))
    print('RTT - {}ms'.format(round((RES_TP - TX_TP) * 1000, 1)))
    print('-------------')
    # print('System Works!')

    pkt_cnt += 1
    time.sleep(1)
