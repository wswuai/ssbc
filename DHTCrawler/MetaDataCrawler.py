from threading import Thread
import logging

import math
import socket
from hashlib import sha1
from struct import pack
from time import sleep, time

from bencode2 import bencode
from util import entropy

from metadata_parser import parse_metadata

BT_PROTOCOL = "BitTorrent protocol"
BT_MSG_ID = 20
EXT_HANDSHAKE_ID = 0


def random_id():
    hash = sha1()
    hash.update(entropy(20))
    return hash.digest()


def send_packet(the_socket, msg):
    the_socket.send(msg)


def send_message(the_socket, msg):
    msg_len = pack(">I", len(msg))
    send_packet(the_socket, msg_len + msg)


def send_handshake(the_socket, infohash):
    bt_header = chr(len(BT_PROTOCOL)) + BT_PROTOCOL
    ext_bytes = "\x00\x00\x00\x00\x00\x10\x00\x00"
    peer_id = random_id()
    packet = bt_header + ext_bytes + infohash + peer_id

    send_packet(the_socket, packet)


def check_handshake(packet, self_infohash):
    try:
        bt_header_len, packet = ord(packet[:1]), packet[1:]
        if bt_header_len != len(BT_PROTOCOL):
            return False
    except TypeError:
        return False

    bt_header, packet = packet[:bt_header_len], packet[bt_header_len:]
    if bt_header != BT_PROTOCOL:
        return False

    packet = packet[8:]
    infohash = packet[:20]
    if infohash != self_infohash:
        return False

    return True


def send_ext_handshake(the_socket):
    msg = chr(BT_MSG_ID) + chr(EXT_HANDSHAKE_ID) + bencode({"m": {"ut_metadata": 1}})
    send_message(the_socket, msg)


def request_metadata(the_socket, ut_metadata, piece):
    """bep_0009"""
    msg = chr(BT_MSG_ID) + chr(ut_metadata) + bencode({"msg_type": 0, "piece": piece})
    send_message(the_socket, msg)


def get_ut_metadata(data):
    ut_metadata = "_metadata"
    index = data.index(ut_metadata) + len(ut_metadata) + 1
    return int(data[index])


def get_metadata_size(data):
    metadata_size = "metadata_size"
    start = data.index(metadata_size) + len(metadata_size) + 1
    data = data[start:]
    return int(data[:data.index("e")])


def recvall(the_socket, timeout=5):
    the_socket.setblocking(0)
    total_data = []
    data = ""
    begin = time()

    while True:
        sleep(0.05)
        if total_data and time() - begin > timeout:
            break
        elif time() - begin > timeout * 2:
            break
        try:
            data = the_socket.recv(1024)
            if data:
                total_data.append(data)
                begin = time()
        except Exception:
            pass
    return "".join(total_data)


def download_metadata(address, binhash, timeout):
    metadata = None
    start_time = time()
    try:
        the_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        the_socket.settimeout(timeout)
        the_socket.connect(address)

        # handshake
        send_handshake(the_socket, binhash)
        packet = the_socket.recv(4096)

        # handshake error
        if not check_handshake(packet, binhash):
            return

        # ext handshake
        send_ext_handshake(the_socket)
        packet = the_socket.recv(4096)

        # get ut_metadata and metadata_size
        ut_metadata, metadata_size = get_ut_metadata(packet), get_metadata_size(packet)
        # print 'ut_metadata_size: ', metadata_size

        # request each piece of metadata
        metadata = []
        for piece in range(int(math.ceil(metadata_size / (16.0 * 1024)))):
            request_metadata(the_socket, ut_metadata, piece)
            packet = recvall(the_socket, timeout)
            metadata.append(packet[packet.index("ee") + 2:])

        metadata = "".join(metadata)

        return binhash, address, metadata, start_time

    finally:
        the_socket.close()


class MetaDataCrawler(Thread):
    def __init__(self, q, timeout):
        super(MetaDataCrawler, self).__init__()
        self.setDaemon(True)
        self.task_queue = q
        self.timeout = timeout
        self.on_meta_fetched = None
        self.on_crawled_failed = None
        # self.output_queue = q2

    def run(self):
        logging.debug(self.getName() + " started.")
        while True:
            try:
                binhash, address = self.task_queue.get()
                logging.debug("get binhash :" + binhash.encode('hex') + "from queue. current length" + str(
                    self.task_queue.qsize()))
                try:
                    binhash, address, metadata, start_time = download_metadata(address, binhash, timeout=self.timeout)
                    info = parse_metadata(metadata)
                    infohash = binhash.encode('hex')
                    logging.debug ("[SUCCESS][SIMCRAWLER] " + str(info))
                    if self.on_meta_fetched:
                        self.on_meta_fetched(infohash, address, info, start_time)
                except Exception, e:
                    logging.debug("error occured while download metadata : " + str(e))
                    if self.on_crawled_failed:
                        self.on_crawled_failed(binhash)

            except Exception, e:
                logging.debug(" error occured while MetaDataCrawler Run : " + str(e))
