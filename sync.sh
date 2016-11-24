#rsync -avzP DHTCrawler root@faithcaiwu.com:/home/ --exclude=ENV --exclude=*.pyc
rsync -avzP ../ssbc root@linode1:/home --exclude=ENV --exclude=*.pyc --exclude=*.git --exclude=*.iml --exclude=*.idea
#rsync -avzP ssbc root@faithcaiwu.com:/home/job/ --exclude=ENV
