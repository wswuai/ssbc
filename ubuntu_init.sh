apt-get update

apt-get install -y gcc python-dev  g++  libmysqld-dev make

apt-get install -y python-setuptools tmux iftop vim

sudo easy_install pip

pip install gevent

pip install bencode

pip install virtualenv

pip install pygeoip

#Disable conntrack
#iptables -I OUTPUT -t raw -p udp -j CT --notrack

#iptables -I PREROUTING -t raw -p udp -j CT --notrack

apt-get install -y mysql-server

echo " ulimit -u 10000 \n ulimit -n 8192 \n ulimit -d unlimited \n ulimit -m unlimited \n ulimit -s unlimited \n ulimit -t unlimited \n ulimit -v unlimited" >> /etc/profile
