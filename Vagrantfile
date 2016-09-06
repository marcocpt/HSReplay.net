# -*- mode: ruby -*-
# vi: set ft=ruby :


Vagrant.configure("2") do |config|
	config.vm.box = "debian/contrib-jessie64"

	config.vm.hostname = "hsreplaynet.local"
	config.vm.network "forwarded_port", guest: 8000, host: 8000

	config.vm.synced_folder ".", "/home/vagrant/hsreplay.net"

	config.vm.provision "shell",
		path: "scripts/provision_system.sh"

	config.vm.provision "shell",
		path: "scripts/provision_user.sh",
		privileged: false
end
