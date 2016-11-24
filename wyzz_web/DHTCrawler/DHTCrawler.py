

import socket
from collections import deque
from hashlib import sha1
from socket import inet_ntoa
from struct import unpack
from threading import Timer, Thread
from time import sleep

from threading import RLock
from bencode2 import bencode, bdecode
from util import entropy

import logging

BOOTSTRAP_NODES = (
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881)
)

TID_LENGTH = 2
RE_JOIN_DHT_INTERVAL = 3.0
AUTO_FIND_INTERVAL = 0.05
TOKEN_LENGTH = 2

MAX_QUEUE_LT = 30
MAX_QUEUE_PT = 200


class KNode(object):
    def __init__(self, nid, ip, port):
        self.nid = nid
        self.ip = ip
        self.port = port


class DHTServer(Thread):
    def __str__(self):
        return """
------
Thread Name :  {0}
Message Processed:  {1}
is_Alive : {2}
------
""".format(self.name, self.msg_cnt, self.is_alive())

    def __init__(self, bind_ip, bind_port, max_node_qsize):
        Thread.__init__(self)
        self.setDaemon(True)
        self.max_node_qsize = max_node_qsize
        self.nid = self.random_id()
        self.nodes = deque(maxlen=max_node_qsize)

        # self.master = master
        self.bind_ip = bind_ip
        self.bind_port = bind_port

        self.process_request_actions = {
            "get_peers": self.on_get_peers_request,
            "announce_peer": self.on_announce_peer_request,
        }

        self.ufd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.ufd.bind((self.bind_ip, self.bind_port))

        self.timer(1, self.run_network_rejoin)
        self.timer(2, self.run_auto_send_find_node)

        self.on_get_peers_callback = None
        self.on_announce_peers_callback = None
        self.receiver_lock = RLock()
        self.transmit_lock = RLock()

        self.msg_cnt = 0

    """ main thread event loop to process DHT events """

    def run_network_rejoin(self):
        while True:
            try:
                sleep(RE_JOIN_DHT_INTERVAL)
                if len(self.nodes) == 0:
                    logging.debug("self.nodes == 0 , rejoin network.")
                    self.join_DHT()

            except Exception, e:
                logging.error("Error occured when rejoin DHT network:" + e.message)

    def run(self):
        logging.debug(self.getName() + " started.")
        # self.rejoin_DHT()
        while True:
            try:
                self.receiver_lock.acquire()
                (data, address) = self.ufd.recvfrom(65536)
                try:
                    msg = bdecode(data)
                except:
                    continue
                self.msg_cnt += 1
                self.on_message(msg, address)
            except Exception, e:
                logging.info("main thread exception ")
            finally:
                self.receiver_lock.release()

    """ Low level method to send KRPC """

    def send_krpc(self, msg, address):
        try:
            self.transmit_lock.acquire()
            if address is None or address[0] is None or address[1] is None:
                return
            self.ufd.sendto(bencode(msg), address)
        except Exception, e:
            logging.debug("ERROR while send_krpc : " + str(e))
            # import pdb
            # pdb.set_trace()
        finally:
            self.transmit_lock.release()

    def on_message(self, msg, address):
        try:
            if msg["y"] == "r":
                if msg["r"].has_key("nodes"):
                    self.process_find_node_response(msg, address)
            elif msg["y"] == "q":
                try:
                    self.process_request_actions[msg["q"]](msg, address)
                except KeyError:
                    self.play_dead(msg, address)
        except KeyError:
            logging.debug("KeyError while on_message")

    def on_get_peers_request(self, msg, address):
        try:
            logging.debug("get_peers_request from : " + str(address))
            infohash = msg["a"]["info_hash"]
            tid = msg["t"]
            nid = msg["a"]["id"]
            token = infohash[:TOKEN_LENGTH]
            msg = {
                "t": tid,
                "y": "r",
                "r": {
                    "id": self.get_neighbor(infohash, self.nid),
                    "nodes": "",
                    "token": token
                }
            }

            if self.on_get_peers_callback:
                self.on_get_peers_callback(infohash, address)
            # TODO : impl new here.
            # self.master.log_hash(infohash, address)
            self.send_krpc(msg, address)
        except KeyError:
            logging.debug("KeyError while on_get_peers_request")
            pass

    def on_announce_peer_request(self, msg, address):
        try:
            logging.debug("get_announce_peer_request from : " + str(address))
            binhash = msg["a"]["info_hash"]
            token = msg["a"]["token"]
            nid = msg["a"]["id"]
            tid = msg["t"]

            if binhash[:TOKEN_LENGTH] == token:
                if msg["a"].has_key("implied_port") and msg["a"]["implied_port"] != 0:
                    port = address[1]
                else:
                    port = msg["a"]["port"]
                # TODO : impl new here.
                if self.on_announce_peers_callback:
                    self.on_announce_peers_callback(binhash, address)
                logging.debug(" get binhash " + " from :" + address[0] + " port : " + str(port))

        except Exception, e:
            logging.error("ERROR while on_announce_peer_request:" + e.message)

        finally:
            self.ok(msg, address)

    def play_dead(self, msg, address):
        try:
            tid = msg["t"]
            msg = {
                "t": tid,
                "y": "e",
                "e": [202, "Server Error"]
            }
            self.send_krpc(msg, address)
        except KeyError:
            pass

    def ok(self, msg, address):
        try:
            tid = msg["t"]
            nid = msg["a"]["id"]
            msg = {
                "t": tid,
                "y": "r",
                "r": {
                    "id": self.get_neighbor(nid, self.nid)
                }
            }
            self.send_krpc(msg, address)
        except KeyError:
            pass

    """ send find node request to address, if nid is None, nid is self. """

    def send_find_node(self, address, nid=None):
        logging.debug("send find node to : " + str(address))

        nid = self.get_neighbor(nid, self.nid) if nid else self.nid
        tid = entropy(TID_LENGTH)
        msg = {
            "t": tid,
            "y": "q",
            "q": "find_node",
            "a": {
                "id": nid,
                "target": self.random_id()
            }
        }
        self.send_krpc(msg, address)

    def join_DHT(self):
        for address in BOOTSTRAP_NODES:
            self.send_find_node(address)

    def run_auto_send_find_node(self):
        while True:
            try:
                sleep(AUTO_FIND_INTERVAL)
                if len(self.nodes) == 0:
                    continue
                node = self.nodes.popleft()
                self.send_find_node((node.ip, node.port), node.nid)
            except Exception, e:
                sleep(0.5)
                logging.error("  Error Occured while run_auto_send_find_node." + str(e))

    def process_find_node_response(self, msg, address):
        logging.debug("Process find_node_response , FROM : " + str(address))
        nodes = self.decode_nodes(msg["r"]["nodes"])
        for node in nodes:
            (nid, ip, port) = node
            if len(nid) != 20:
                logging.debug("len != 20 , FROM : " + str(address))
                continue
            if ip == self.bind_ip:
                logging.debug("ip == bind_ip , FROM : " + str(address))
                continue
            n = KNode(nid, ip, port)
            self.nodes.append(n)

    @staticmethod
    def timer(t, f):
        timer = Timer(t, f)
        timer.setDaemon(True)
        timer.start()

    @staticmethod
    def random_id():
        h = sha1()
        h.update(entropy(20))
        return h.digest()

    @staticmethod
    def get_neighbor(target, nid, end=10):
        return target[:end] + nid[end:]

    @staticmethod
    def decode_nodes(nodes):
        n = []
        length = len(nodes)
        if (length % 26) != 0:
            return n

        for i in range(0, length, 26):
            nid = nodes[i:i + 20]
            ip = inet_ntoa(nodes[i + 20:i + 24])
            port = unpack("!H", nodes[i + 24:i + 26])[0]
            n.append((nid, ip, port))

        return n
