#! /bin/sh
pyinstaller --add-binary="assets/ffmpeg.exe;assets" --add-binary="assets/libwinpthread-1.dll;assets" --add-binary="assets/tag.dll;." -Fw dr.py
