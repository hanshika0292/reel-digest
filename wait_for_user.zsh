# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Hanshika Gupta. See LICENSE.
# Sourced by run_digest.sh and run_events.sh.
#
# While the lid is closed, macOS wakes for ~2 seconds every 15 minutes ("dark wake"), and launchd fires a missed
# 7:47 run then. That run crawls along in 2-second slices for hours until Instagram times out. So wait until
# someone is actually at the Mac:
#   - the screen is on: a dark wake has only CPU + Network, no Graphics, in `pmset -g systemstate`;
#   - and the keyboard or trackpad was touched in the last 10 minutes. HIDIdleTime alone isn't enough: it stops
#     counting while the Mac sleeps, so last night's typing still looks recent during a dark wake.
# A run started by hand passes at once.

user_present() {
  pmset -g systemstate | grep -q Graphics || return 1
  local idle
  idle=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
  (( ${idle:-0} <= 600 ))
}

wait_for_user() {
  until user_present; do
    sleep 60
  done
}
