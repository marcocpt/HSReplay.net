#!/usr/bin/env bash

PROJECT="$HOME/hsreplay.net"

mkdir -p "$HOME/.cache" "$HOME/.config/zsh"
echo 'source $HOME/env/bin/activate' > "$HOME/.config/zsh/profile"
echo 'export PATH=$VIRTUAL_ENV/nodeenv/bin:$PATH' >> "$HOME/.config/zsh/profile"
cp /etc/skel/.zshrc "$HOME/.zshrc"

python3 -m venv "$HOME/env"
source "$HOME/env/bin/activate"
pip install --upgrade -r "$PROJECT/requirements/dev.txt"

if [[ ! -e $VIRTUAL_ENV/nodeenv ]]; then
	nodeenv "$VIRTUAL_ENV/nodeenv" --prebuilt
fi
export PATH="$VIRTUAL_ENV/nodeenv/bin:$PROJECT/node_modules/.bin:$PATH"

npm -C "$PROJECT" install

createdb --username postgres hsreplaynet
python "$PROJECT/manage.py" migrate --no-input
python "$PROJECT/manage.py" load_cards

if [[ ! -d $PROJECT/hsreplaynet/static/vendor ]]; then
	"$PROJECT/scripts/get_vendor_static.sh"
fi

python "$PROJECT/scripts/initdb.py"


"$PROJECT/scripts/update_log_data.sh"

webpack --verbose -d \
	--devtool cheap-module-eval-source-map \
	--config "$PROJECT/webpack.config.js" \
	--watch &

sassc "$PROJECT/hsreplaynet/static/styles/main.scss" "$PROJECT/hsreplaynet/static/styles/main.css" \
	--sourcemap --source-comments \
	--watch &


python "$PROJECT/manage.py" runserver 0.0.0.0:8000
