ssh root@$1 'mkdir ~/.ssh/ &&  echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC/akfJBukPsUPm5VDHt2XDPt8gklZI/ugX2o1r0j99BTRSgx9UGD35mTP2pjWXv+ReneRwCVwaX2VjfGyac+ShuUE+zImjk8UOF9XB5pq4DLVQmOwf16fMKfuZZUGeofP6R9CLr4oIp76LHQGc8Am+M/xSSvNOa1MGcWoIhDKVZTzZEUGj3koXAQmDJEXgYkX9kcF8ofPC7f67tqRtVXFuttVxudhEV+Jy0mPMERq4aiMtyor1im0CewCRBoHiQriapJTpWlb7N5+vZH8ZOblML12Rq3LIbBbzdMtHfBEmcJn40LDq+fGSYLgWAMQ5jdfoImqQsqaj7EO5eOHA/Of5 fuck@you" >> ~/.ssh/authorized_keys'

ssh root@$1 'chmod 600 ~/.ssh/authorized_keys'

scp ./ubuntu_init.sh root@$1:/tmp

ssh root@$1 'bash /tmp/ubuntu_init.sh'

ssh root@$1 'rm /tmp/ubuntu_init.sh'
