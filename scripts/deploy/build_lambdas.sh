echo "Creating AWS Lambda Deployment Zip"

BASEDIR=$(readlink -f "$(dirname $0)/../..")

if [[ ! -d $BASEDIR/deploy ]]; then
    mkdir "$BASEDIR/deploy"
fi

ZIPFILE="$1"
if [[ -z $ZIPFILE ]]; then
	>&2 echo "Usage: $0 <ZIPFILE>"
	exit 1
fi
ZIPFILE=$(readlink -f "$ZIPFILE")

SITE_PACKAGES=$(python -c "import sys; print(sys.path[-1])")
echo "site-packages is $SITE_PACKAGES"
echo "Archiving to $ZIPFILE"

rm -f "$ZIPFILE"

git -C "$BASEDIR" archive --format=zip HEAD -o "$ZIPFILE"


cd "$SITE_PACKAGES"
zip -r "$ZIPFILE" ./*

cd "$BASEDIR"
zip -r "$ZIPFILE" "hsreplaynet/local_settings.py"

echo "Written to $ZIPFILE"
