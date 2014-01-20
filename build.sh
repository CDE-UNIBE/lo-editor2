#!/bin/bash

filename="www/plugins/lo_editor2.zip"
rm -rfv $filename
mkdir -v lo_editor2
cp -v `find src/ | grep \.py$` lo_editor2/
cp -v "src/lo-logo.png" lo_editor2/
cp -v "src/metadata.txt" lo_editor2/
zip -9rv $filename lo_editor2/
rm -rf lo_editor2/
