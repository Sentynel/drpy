#! /bin/sh
pyinstaller dr-macos.spec
codesign --remove-signature dist/dr.app/Contents/MacOS/Python
codesign --deep -s "Sentynel Code-Signing" dist/dr.app
cd dist
hdiutil create ./dr.dmg -srcfolder dr.app -ov
cd ..
