#!/usr/bin/env bash

echo "stop running nodes"
ps -ef | grep 'python3 node.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9




for ((i = 1 ; i <= $1 ; i++)); do
	# tmux new-session \; send-keys "python3 node.py "$i" "$3"" Enter
	python3 node.py $i &
done