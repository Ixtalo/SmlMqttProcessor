#!/bin/bash
#set -x

## https://github.com/volkszaehler/libsml/tree/d65682222dbaddccf4c2c25d4fb530572e60cbd3
COMMIT_HASH=d65682222dbaddccf4c2c25d4fb530572e60cbd3

LIBSML_URL="https://github.com/volkszaehler/libsml/archive/${COMMIT_HASH}.zip"

CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TEMPFILE="/tmp/libsml.zip"
TARGETDIR="$CURDIR/libsml"

if [ ! -f $TEMPFILE ]; then
  wget --quiet --output-document=$TEMPFILE $LIBSML_URL
fi

if [ ! -d $TARGETDIR ]; then
  unzip -n -q -x -d "$CURDIR" $TEMPFILE
  mv "$CURDIR/libsml-${COMMIT_HASH}" "$TARGETDIR"
fi

pushd "$TARGETDIR"
make --jobs --quiet

popd
make
