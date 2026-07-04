#!/usr/bin/env sh
set -eu

python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3).read()"
