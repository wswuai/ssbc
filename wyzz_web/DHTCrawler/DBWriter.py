import threading

import MySQLdb

import logging

import traceback

import metadata as md


class DBWriter(threading.Thread):
    def __init__(self, q, host, port, username, passwd, connection=None):
        super(DBWriter, self).__init__()
        self.q = q
        self.url = host
        self.username = username
        self.passwd = passwd
        self.port = port

        if connection is not None:
            self.conn = connection
        else:
            self.conn = MySQLdb.connect(host=host, user=username, passwd=passwd, db='ssbc', charset='utf8')

        self.conn.ping()

        self.cursor = self.conn.cursor()

    def run(self):

        while True:
            try:
                infohash, address, info, start_time = self.q.get()
                md.save_metadata(self.cursor, infohash, address, start_time, info)
            except Exception, e:
                traceback.print_stack()
                logging.error("error occured while DBWriter running : " + str(e))
