#!/bin/bash
curl -s "https://api.github.com/repos/ramparte/amplifier-bundle-dev-machine/contents/" | python3 -c "import sys,json; [print(i['type'], i['name']) for i in json.load(sys.stdin)]"
