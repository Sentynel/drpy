# Windows

pytaglib: Use Visual Studio to CMake build and install taglib in x64-release mode. Copy the install
file tree to c:\libraries\taglib. Set env var INCLUDE to the path to the taglib include directory.
Pip installing pytaglib should now work.

ffmpeg: Use github.com/Sentynel/ffmpeg-build (based on acoustid/ffmpeg-build). The Github action
should be sufficient, or build manually. Note that the output depends on libwinpthread-1.dll, which
can be found in mingw64 distributions (e.g. git bash).
