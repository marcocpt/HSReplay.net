PROJECT="$HOME/hsreplay.net"
source "$HOME/env/bin/activate"
export PATH="$VIRTUAL_ENV/nodeenv/bin:$HOME/node_modules/.bin:$PATH"

echo "Starting webpack watcher"
killall -9 -q node
webpack --verbose -d \
	--devtool cheap-module-eval-source-map \
	--config "$PROJECT/webpack.config.js" \
	--watch &

echo "Starting scss watcher"
killall -9 -q sassc
sassc "$PROJECT/hsreplaynet/static/styles/main.scss" "$PROJECT/hsreplaynet/static/styles/main.css" \
	--sourcemap --source-comments \
	--watch &

echo "Starting Django server"
killall -9 -q python
python "$PROJECT/manage.py" runserver 0.0.0.0:8000
