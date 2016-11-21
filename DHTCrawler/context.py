from Queue import Queue
from Queue import Full

import logging

get_request_queue = Queue(200)

announce_peer_queue = Queue(100000)

metadata_queue = Queue(5000)

filter_impl = set()

failed_count = 0

success_count = 0


import threading
filter_lock = threading.RLock()

def isFiltered(binhash):
    filter_lock.acquire()
    try:
        if binhash in filter_impl:
            return True
        else:
            filter_impl.add(binhash)
            return False
    finally:
        filter_lock.release()

def removeFiltered(binhash):
    # filter_lock.acquire()
    # try:
    #     if binhash in filter_impl:
    #         filter_impl.remove(binhash)
    # finally:
    #     filter_lock.release()

    pass

def announce_peer_callback(binhash, address):
    try:
        logging.debug(
            "put announce_peer msg  to Queue , NowLength : " + str(announce_peer_queue.qsize()) + " From : " + str(
                address))
        if isFiltered(binhash):
            logging.debug("filtered out of announce_peer_queue : " + binhash.encode('hex'))
        announce_peer_queue.put([binhash, address], block=False)
    except Full:
        logging.debug("DROP announce_peer message caused by Queue is Full.")


def get_peers_request_callback(binhash, address):
    try:
        logging.debug(
            "put peers_request msg  to Queue , NowLength : " + str(get_request_queue.qsize()) + " From : " + str(
                address))
        if isFiltered(binhash):
            return
        get_request_queue.put([binhash, address], block=False)
    except Full:
        logging.error("DROP peers_request message caused by Queue is Full.")



def on_crawled_failed(infohash):
    removeFiltered(infohash)
    global failed_count
    failed_count += 1

def metadata_getted_callback(infohash, address, metadata, start_time):
    global success_count
    success_count += 1

    try:
        logging.debug(
            "put metadata msg to Queue , NowLength : " + str(metadata_queue.qsize()) +
            " From : " + str(address)
        )
        metadata_queue.put([infohash, address, metadata, start_time])
    except Full:
        logging.error("DROP metadata message caused by Queue is FULL. ")
    pass
