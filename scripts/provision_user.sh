#!/usr/bin/env bash

PROJECT="$HOME/hsreplay.net"

mkdir -p "$HOME/.cache" "$HOME/.config/zsh"
echo 'source $HOME/env/bin/activate' > "$HOME/.config/zsh/profile"
echo 'export PATH=$VIRTUAL_ENV/nodeenv/bin:$HOME/node_modules/.bin:$PATH' >> "$HOME/.config/zsh/profile"
cp /etc/skel/.zshrc "$HOME/.zshrc"

python3 -m venv "$HOME/env"
source "$HOME/env/bin/activate"
pip install --upgrade pip setuptools
pip install -r "$PROJECT/requirements/dev.txt"

if [[ ! -e $VIRTUAL_ENV/nodeenv ]]; then
	nodeenv "$VIRTUAL_ENV/nodeenv"
fi
export PATH="$VIRTUAL_ENV/nodeenv/bin:$HOME/node_modules/.bin:$PATH"

# Let's talk about awfulware.
# There are so many layers at which this idiotic issue could have been prevented:
# - If Microsoft didn't make symlinks suck on windows
# - If Windows symlinks, sucky as they may be, were supported on Vagrant
# - If Vagrant didn't sell itself as the solution to "it works on my machine"
# - If those symlinks didn't exist in the first place
# - If npm properly supported prefixing (npm/npm#775)
# - If, more generally, npm wasn't one of the worst package managers ever created
# - If we stopped producing a new package manager for every single bloody language
# - If we as a community, and the JS community in particular, didn't let atrocious
#   engineering decisions plague extremely popular software. Awfulware should not
#   be allowed to become the norm.
# ... but I suppose, if that were the case, Windows wouldn't have been so popular
# in the first place and I wouldn't have to waste my time with this STUPID ISSUE.
# https://github.com/npm/npm/issues/7308
# https://github.com/npm/npm/issues/9901
ln -fs "$PROJECT/package.json" "$HOME/package.json"
# Move typings one level up
sed 's|hsreplaynet/|hsreplay.net/hsreplaynet/|g' "$PROJECT/typings.json" > "$HOME/typings.json"
npm install

if [[ ! -e $PROJECT/hsreplaynet/local_settings.py ]]; then
	cp "$PROJECT/local_settings.example.py" "$PROJECT/hsreplaynet/local_settings.py"
fi

if [[ -e $HOME/joust ]]; then
	git -C "$HOME/joust" fetch -q --all && git -C "$HOME/joust" reset -q --hard origin/master
else
	git clone -q https://github.com/HearthSim/Joust "$HOME/joust"
fi

createdb --username postgres hsreplaynet
python "$PROJECT/manage.py" migrate --no-input
python "$PROJECT/manage.py" load_cards
python "$PROJECT/scripts/initdb.py"

influx --execute "create database hsreplaynet"
influx --execute "create database joust"

if [[ ! -d $PROJECT/hsreplaynet/static/vendor ]]; then
	"$PROJECT/scripts/get_vendor_static.sh"
fi

"$PROJECT/scripts/update_log_data.sh"
