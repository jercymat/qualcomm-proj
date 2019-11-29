#!/usr/bin/env bash
tmux new-session -d -s sdn5g

tmux rename-window -t sdn5g:1 'mininet'

tmux new-window -t sdn5g:2 -n 'ue'
tmux new-window -t sdn5g:3 -n 'nfv'
tmux new-window -t sdn5g:4 -n 'sba1'
tmux new-window -t sdn5g:5 -n 'sba2'

tmux split-window -v -t sdn5g:3
tmux split-window -h -t sdn5g:3

tmux split-window -v -t sdn5g:4
tmux split-window -h -t sdn5g:4
tmux select-pane -t sdn5g:.1
tmux split-window -h -t sdn5g:4

tmux split-window -v -t sdn5g:5
tmux split-window -h -t sdn5g:5
tmux select-pane -t sdn5g:.1
tmux split-window -h -t sdn5g:5

tmux select-window -t sdn5g:1

tmux attach-session -t sdn5g
