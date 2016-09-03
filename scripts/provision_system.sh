#!/usr/bin/env bash

echo 'deb http://cloudfront.debian.net/debian jessie-backports main
deb-src http://cloudfront.debian.net/debian jessie-backports main' > /etc/apt/sources.list.d/backports.list

apt-get update
apt-get dist-upgrade -qy
apt-get install -qy \
	zsh tree \
	python3 python3-dev python3-venv \
	gcc g++ libxml2 libxml2-dev libxslt1-dev \
	postgresql libpq-dev
apt-get install -qy -t jessie-backports redis-server

# Enable trust authentication for postgresql
sed -i 's/all *postgres *peer/all postgres trust/' /etc/postgresql/9.4/main/pg_hba.conf
systemctl restart postgresql

wget -q https://raw.githubusercontent.com/jleclanche/dotfiles/master/.zshrc -O /etc/skel/.zshrc

chsh -s /bin/zsh
chsh -s /bin/zsh vagrant
cp /etc/skel/.zshrc "$HOME/.zshrc"
mkdir -p "$HOME/.cache"
