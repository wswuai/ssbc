from gevent import monkey

monkey.patch_all()

from DHTCrawler import DHTServer

from MetaDataCrawler import MetaDataCrawler
from ltMetaDataCrawler import torrentClientMetaCrawler

import threading
import logging
from time import sleep
import os

import context

logging.basicConfig(
    level=logging.INFO, format="%(threadName)s:%(levelname)s:%(message)s"
)

servers = []
simple_crawlers = []
lt_crawlers = []

DHT_CRAWLER_THREAD = 100

METADATA_CRAWLER_THREAD = 0

SIM_CRAWLER_TIMEOUT = 7

LIB_TORRENT_CRAWLER_TIMEOUT = 60

LIBTORRENT_CRAWLER_INSTANCES = 1

LIBTORRENT_CRAWLER_CONCURRENT_TASK = 50

DB_WRITER_THREAD = 2

if __name__ == '__main__':
    REFRESH_INTERVAL = 2
    for i in range(0, DHT_CRAWLER_THREAD):
        server = DHTServer("0.0.0.0", 6881 + i, 200)
        server.setName("DHTCrawler-" + str(i))
        server.start()
        servers.append(server)
        server.on_announce_peers_callback = context.announce_peer_callback
        # TODO : DONOT DE COMMENT, NOT IMPLED
        # server.on_get_peers_callback = context.get_peers_request_callback

    for i in range(0, METADATA_CRAWLER_THREAD):
        crawler = MetaDataCrawler(context.announce_peer_queue, timeout=SIM_CRAWLER_TIMEOUT)
        crawler.on_meta_fetched = context.metadata_getted_callback
        crawler.on_crawled_failed = context.on_crawled_failed
        crawler.setName("MetaCrawler-" + str(i))
        crawler.start()
        simple_crawlers.append(crawler)

    for i in range(0, LIBTORRENT_CRAWLER_INSTANCES):
        ltCrawler = torrentClientMetaCrawler(name="LTCRAWLER-" + str(i),
                                             task_queue=context.announce_peer_queue,
                                             concurrent=LIBTORRENT_CRAWLER_CONCURRENT_TASK,
                                             timeout=LIB_TORRENT_CRAWLER_TIMEOUT
                                             )
        ltCrawler.on_meta_fetched = context.metadata_getted_callback
        ltCrawler.on_crawled_failed = context.on_crawled_failed
        ltCrawler.start()
        lt_crawlers.append(ltCrawler)

    print "all thread created! start crawling !"

    while True:
        try:
            last_success = context.success_count
            sleep(REFRESH_INTERVAL)
            dht_alive = [i for i in servers if i.isAlive()]
            crawler_alive = [i for i in simple_crawlers if i.isAlive()]
            lt_crawler_alive = [i for i in lt_crawlers if i.isAlive()]

            now_success = context.success_count

            print "[STATUS] DHT(%d/%d) SimCrawler(%d/%d) LT Crawler(%d/%d) Success/Failed(%d/ %d) FilterSize(%d)\n" \
                  "[QSTATS] ANNOUNCE(%d) META(%d) [RATE] %s items/sec" % (
                      len(servers),
                      len(dht_alive),
                      len(simple_crawlers),
                      len(crawler_alive),
                      len(lt_crawlers),
                      len(lt_crawler_alive),
                      now_success,
                      context.failed_count,
                      len(context.filter_impl),
                      context.announce_peer_queue.qsize(),
                      context.metadata_queue.qsize(),
                      (now_success - last_success) / REFRESH_INTERVAL,
                  )

        except KeyboardInterrupt, e:
            print(" exit caused by Keyboard Interrupt")
            os._exit(0)
        except Exception, e:
            logging.error(e.message)
