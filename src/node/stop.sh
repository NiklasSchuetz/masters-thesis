#!/usr/bin/env bash
ps -ef | grep 'python3 node.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9