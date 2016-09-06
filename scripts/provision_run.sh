PROJECT="$HOME/hsreplay.net"
source "$HOME/env/bin/activate"
export PATH="$VIRTUAL_ENV/nodeenv/bin:$PROJECT/node_modules/.bin:$PATH"

echo "Starting webpack watcher"
webpack --verbose -d \
	--devtool cheap-module-eval-source-map \
	--config "$PROJECT/webpack.config.js" \
	--watch &

echo "Starting scss watcher"
killall -9 sassc
sassc "$PROJECT/hsreplaynet/static/styles/main.scss" "$PROJECT/hsreplaynet/static/styles/main.css" \
	--sourcemap --source-comments \
	--watch &

echo "Starting Django server"
python "$PROJECT/manage.py" runserver 0.0.0.0:8000 &
