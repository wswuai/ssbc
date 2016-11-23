import threading

import MySQLdb

import logging

import traceback

import metadata as md


class DBWriter(threading.Thread):
    def __init__(self, q, host, port, username, passwd):
        super(DBWriter, self).__init__()
        self.q = q
        self.url = host
        self.username = username
        self.passwd = passwd
        self.port = port

        conn = MySQLdb.connect(host,username, passwd)

        conn.ping()

        self.cursor = conn.cursor()

    def run(self):

        while True:
            try:
                infohash, address, metadata, start_time = self.q.get()
                md.save_metadata(self.cursor, infohash, address, start_time, metadata)
                print "successful write to db."
            except Exception, e:
                traceback.print_stack()
                logging.error("error occured while DBWriter running : " + str(e))
