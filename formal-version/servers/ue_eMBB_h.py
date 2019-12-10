import sys
import json
import time
import hashlib
import threading

from hyper import HTTP20Connection

# Test Mode: Send to localhost:9001
# Otherwise: Send to 10.0.1.1:8080
TEST_MODE = True if len(sys.argv) == 2 and sys.argv[1] == '--test' else False
HOST = 'localhost' if TEST_MODE else '10.0.1.1'
SEND_PORT = 9001 if TEST_MODE else 8080

pkt_cnt = 1
pkt_per_s = 200
expr_time = 1

data = {
    'Content {}'.format(x): 'NCCUCS mclab testing {}'.format(x) for x in range(1, 51)
}
transfer_data = json.dumps(data).encode('utf-8')
headers = {
    'content-length': str(len(transfer_data)),
    'content-type': 'application/json',
    'scenario': 'eMBB'
}


def send_packet(pkt_cnt):
    print('Sending eMBB packet {:0>4d} into system\nheaders: {}'.format(pkt_cnt, headers))
    conn = HTTP20Connection('{}:{}'.format(HOST, SEND_PORT))

    # Add SHA256 encrypted id to header i.e. sha256('eMBB-PKT-0132')
    headers['id'] = hashlib.sha256('eMBB-PKT-{:0>4d}'.format(pkt_cnt)).hexdigest()
    # headers['id'] = 'eMBB-PKT-{:0>4d}'.format(pkt_cnt)

    TX_TP = time.time().real
    conn.request('POST', '/', headers=headers, body=transfer_data)

    resp = conn.get_response()
    RES_TP = time.time().real
    RX_TP = float(resp.headers['rx-timestamp'][0])
    print('Response of eMBB packet {:0>4d}:'.format(pkt_cnt))
    print(json.dumps(dict(resp.headers)))
    print(resp.read())
    print('TX - {:.6f} | RX - {:.6f} | RES - {:.6f}'.format(TX_TP, RX_TP, RES_TP))
    print('Transfer Time - {}ms | RTT - {}ms'.format(round((RX_TP - TX_TP) * 1000, 1), round((RES_TP - TX_TP) * 1000, 1)))
    print('-------------')
    # print('System Works!')

    pkt_cnt += 1


while pkt_cnt <= pkt_per_s * expr_time:
    th = threading.Thread(target=send_packet, args=(pkt_cnt,))
    th.start()

    pkt_cnt += 1
    time.sleep(1 / pkt_per_s)
