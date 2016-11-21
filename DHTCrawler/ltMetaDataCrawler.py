# coding: utf8

import logging
import threading
import traceback
import random
import time
import os
import socket
import gevent.pool

from metadata_parser import parse_metadata

from threading import Semaphore

import libtorrent as lt

threading.stack_size(200 * 1024)
socket.setdefaulttimeout(30)

listened_ports = set()


class torrentClientMetaCrawler(threading.Thread):
    def __init__(self, name, task_queue, concurrent=10, timeout=40):
        super(torrentClientMetaCrawler, self).__init__()
        self.setDaemon(True)
        self.save_path = '/tmp/torrentDownloader/' + name + '/'
        self.setName(name)
        self.session = lt.session()
        self.timeout = timeout
        self.pool = gevent.pool.Pool(concurrent)
        r = random.randrange(20000, 30000)
        self.session.listen_on(r, r + 10)
        self.session.add_dht_router('router.bittorrent.com', 6881)
        self.session.add_dht_router('router.utorrent.com', 6881)
        self.session.add_dht_router('dht.transmission.com', 6881)
        self.session.start_dht()
        self.task_queue = task_queue
        self.on_meta_fetched = None
        self.on_crawled_failed = None

    def run(self):
        logging.debug(self.getName() + " started.")
        while True:
            try:
                infohash, address = self.task_queue.get()
                logging.debug(
                    "get infohash :" + infohash.encode('hex') + "from queue. current length" + str(
                        self.task_queue.qsize()))
                self.download_metadata(address, infohash)
            except Exception, e:
                logging.error("error occured while downloading metadata : " + e.message)

    def _fetch_torrent(self, binhash):
        infohash = binhash.encode('hex')
        name = infohash.upper()
        url = 'magnet:?xt=urn:btih:%s' % (name,)
        data = ''
        params = {
            'save_path': self.save_path,
            'storage_mode': lt.storage_mode_t(2),
            'paused': False,
            'auto_managed': False,
            'duplicate_is_error': True}

        handle = None
        try:
            handle = lt.add_magnet_uri(self.session, url, params)
        except:
            return
        if handle is None:
            return

        start_time = time.time()
        status = self.session.status()
        logging.debug('Downloading Metadata:' + str(url))
        handle.set_sequential_download(1)
        down_path = None
        success = False
        for i in xrange(0, self.timeout):
            gevent.sleep(1)
            if handle.has_metadata():
                success = True
                info = handle.get_torrent_info()
                down_path = '/tmp/downloads/%s' % info.name()
                meta = info.metadata()
                dinfo = parse_metadata(meta)
                logging.debug ("[SUCCESS][LTCRAWLER] " + str(dinfo))
                if self.on_meta_fetched:
                    self.on_meta_fetched(infohash, None, meta, start_time)

        self.delete_torrent_file(down_path)
        self.session.remove_torrent(handle)
        if self.on_crawled_failed:
            self.on_crawled_failed(binhash)

        logging.debug("Downloading Timed out ")

    def delete_torrent_file(self, down_path):
        if down_path and os.path.exists(down_path):
            os.system('rm -rf "%s"' % down_path)

    def download_metadata(self, address, binhash):
        self.pool.spawn(self._fetch_torrent, binhash)
