#import os

bind='0.0.0.0:5678'

workers=4

backlog=2048

worker_class="gevent" #sync, gevent,meinheld

debug=False

pidfile='log/web.pid'

loglevel='info'

accesslog='log/server.log'

errorlog='log/error.log'

daemon=False
#daemon=True