#!/usr/bin/env bash

echo 'deb http://cloudfront.debian.net/debian jessie-backports main
deb-src http://cloudfront.debian.net/debian jessie-backports main' > /etc/apt/sources.list.d/backports.list
echo "deb https://repos.influxdata.com/debian jessie stable" > /etc/apt/sources.list.d/influxdb.list
wget https://repos.influxdata.com/influxdb.key -qO - | apt-key add -

apt-get update -q
apt-get install -qy apt-transport-https
apt-get dist-upgrade -qy
apt-get install -qy \
	zsh curl git htop tree unzip vim \
	python3 python3-dev python3-venv \
	gcc g++ libxml2 libxml2-dev libxslt1-dev \
	postgresql libpq-dev supervisor influxdb
apt-get install -qy -t jessie-backports redis-server

# Enable trust authentication for postgresql
sed -i 's/all *postgres *peer/all postgres trust/' /etc/postgresql/9.4/main/pg_hba.conf
systemctl restart postgresql

systemctl start influxdb

if [[ ! -e /etc/skel/.zshrc ]]; then
	wget -q https://raw.githubusercontent.com/jleclanche/dotfiles/master/.zshrc -O /etc/skel/.zshrc
fi

chsh -s /bin/zsh
chsh -s /bin/zsh vagrant
cp /etc/skel/.zshrc "$HOME/.zshrc"
mkdir -p "$HOME/.cache"
