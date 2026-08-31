#!/bin/bash

SESSION="bbb-transcription"
DIR="/home/mohammad/ESL_python"
VENV="$DIR/ennv/bin/activate"

tmux kill-session -t "$SESSION" 2>/dev/null

tmux new-session -d -s "$SESSION" -n "services" -c "$DIR"

# -----------------------------
# FORCE BLACK TMUX UI
# -----------------------------

tmux set-option -t "$SESSION" status-style "bg=black,fg=colour46"

tmux set-option -t "$SESSION" status-left \
'#[bg=black,fg=colour46,bold] BBB TRANSCRIPTION '

tmux set-option -t "$SESSION" status-right \
'#[bg=black,fg=colour51]%H:%M #[bg=black,fg=colour46]%Y-%m-%d '

tmux set-option -t "$SESSION" window-status-style \
"bg=black,fg=colour240"

tmux set-option -t "$SESSION" window-status-current-style \
"bg=black,fg=colour46,bold"

tmux set-option -t "$SESSION" message-style \
"bg=black,fg=colour46"

tmux set-option -t "$SESSION" mode-style \
"bg=black,fg=colour46"

tmux set-option -t "$SESSION" pane-border-status top

tmux set-option -t "$SESSION" pane-border-style \
"bg=black,fg=colour22"

tmux set-option -t "$SESSION" pane-active-border-style \
"bg=black,fg=colour46,bold"

tmux set-option -t "$SESSION" pane-border-format \
'#[bg=black,fg=colour46] #{?pane_active,▶, } #[bg=black,fg=colour51,bold]#{pane_title} #[bg=black,fg=colour240]| pane #{pane_index} #[bg=black]'

# -----------------------------
# Pane 1 — Meeting Events
# -----------------------------

tmux select-pane -t "$SESSION:0.0" -T "MEETING EVENTS"

tmux send-keys -t "$SESSION:0.0" \
  "export NO_COLOR=1; printf '\033[0m\033[40m\033[92m'; clear; printf '\033[40m\033[92m'; source $VENV && python3 create_event_listener.py" C-m

# -----------------------------
# Pane 2 — Caption API
# -----------------------------

tmux split-window -h -t "$SESSION:0" -c "$DIR"

tmux select-pane -t "$SESSION:0.1" -T "CAPTION API"

tmux send-keys -t "$SESSION:0.1" \
  "export NO_COLOR=1; printf '\033[0m\033[40m\033[96m'; clear; printf '\033[40m\033[96m'; source $VENV && uvicorn https_listener:app --host 0.0.0.0 --port 8000 --no-use-colors" C-m

# -----------------------------
# Pane 3 — Audio Fork
# -----------------------------

tmux split-window -v -t "$SESSION:0.1" -c "$DIR"

tmux select-pane -t "$SESSION:0.2" -T "AUDIO FORK"

tmux send-keys -t "$SESSION:0.2" \
  "export NO_COLOR=1; printf '\033[0m\033[40m\033[95m'; clear; printf '\033[40m\033[95m'; source $VENV && python3 main.py" C-m

# Arrange panes
tmux select-layout -t "$SESSION:0" tiled

# Attach
tmux attach -t "$SESSION"
