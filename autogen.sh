#!/bin/sh
# Run this to generate all the initial makefiles, etc.

PROJECT=eos-boot-helper
builddir=`pwd`
srcdir=`dirname "$0"`
[ -z "$srcdir" ] && srcdir=.

# Rebuild the autotools
cd "$srcdir"
${AUTORECONF-autoreconf} -iv || exit $?
cd "$builddir"

# Run configure unless NOCONFIGURE set.
if [ -z "$NOCONFIGURE" ]; then
    "$srcdir"/configure "$@"
    echo "Now type 'make' to compile $PROJECT."
else
    echo "Now type './configure && make' to compile $PROJECT."
fi
