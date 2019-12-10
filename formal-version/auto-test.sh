#!/usr/bin/env bash
tmux new-session -d -s test1

tmux rename-window -t test1:1 'ue'

tmux new-window -t test1:2 -n 'uam-nfv'
tmux new-window -t test1:3 -n 'sbaes-1'
tmux new-window -t test1:4 -n 'sbaes-2'
tmux new-window -t test1:5 -n 'dp'

tmux split-window -v -t test1:3
tmux split-window -h -t test1:3

tmux split-window -v -t test1:4
tmux split-window -h -t test1:4
tmux select-pane -t test1:.1
tmux split-window -h -t test1:4

tmux split-window -v -t test1:5
tmux split-window -h -t test1:5
tmux select-pane -t test1:.1
tmux split-window -h -t test1:5

tmux select-window -t test1:1

tmux attach-session -t test1
