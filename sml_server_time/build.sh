#!/bin/bash
#set -x

## https://github.com/volkszaehler/libsml/tree/6609c8117ba2c987aea386a7fffb9b4746636be6
LIBSML_URL="https://github.com/volkszaehler/libsml/archive/6609c8117ba2c987aea386a7fffb9b4746636be6.zip"

CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TEMPFILE="/tmp/libsml.zip"
TARGETDIR="$CURDIR/libsml"

if [ ! -f $TEMPFILE ]; then
  wget --quiet --output-document=$TEMPFILE $LIBSML_URL
fi

if [ ! -d $TARGETDIR ]; then
  unzip -n -q -x -d "$CURDIR" $TEMPFILE
  mv "$CURDIR/libsml-6609c8117ba2c987aea386a7fffb9b4746636be6" "$TARGETDIR"
fi

pushd "$TARGETDIR"
make --jobs --quiet

popd
make
