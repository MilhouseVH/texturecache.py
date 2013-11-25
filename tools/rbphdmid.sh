#!/bin/sh

#
# Copyright (C) 2013 Neil MacLeod (rbphdmid@nmacleod.com)
#
# Hack to turn off HDMI power when XBMC screensaver
# has been active for the specified number of seconds.
# Default interval is 900 seconds, or 15 minutes.
#
# When the screensaver is disabled, HDMI power will be
# restored and XBMC restarted (Application.Quit()) so that
# the EGL context[1] may be re-established.
#
# If the screensaver is disabled before the power off interval,
# the interval will be cancelled.
#
# Arguments:
#  #1: Power off interval in seconds (after screensaver activated)
#
# In OpenELEC, add the following line to the end of /storage/.config/autostart.sh:
#
# /storage/rbphdmid.sh &
#
# Requires: texturecache.py[2] in /storage with execute permissions.
#
# 1. http://forum.xbmc.org/showthread.php?tid=163016
# 2. https://github.com/MilhouseVH/texturecache.py
#
# Version 0.0.1
#

TVSERVICE=/usr/bin/tvservice
TEXTURECACHE=/storage/texturecache.py
DELAY=${1:-900}
TIMERPID=0

logdbg ()
{
  [ $PPID != 1 ] && echo "$(date +"%F %T"): $1"
}

logmsg ()
{
  echo "[$(basename $0)] $1"
}

enable_hdmi()
{
  if [ -n "$(${TVSERVICE} --status | grep "TV is off")" ]; then
    logdbg "Restoring HDMI power"
    ${TVSERVICE} --preferred >/dev/null
    ${TEXTURECACHE} @xbmc.host=localhost @logfile= power exit
  fi
}

disable_hdmi()
{
  ${TVSERVICE} --off >/dev/null
}

start_timer()
{
  logdbg "HDMI power off in $1 seconds unless cancelled"
  (sleep $1 && disable_hdmi) & 
  TIMERPID=$!
}

stop_timer()
{
  # Check TIMERPID pid is still our scheduled disable_hdmi()...
  if [ ${TIMERPID} != 0 ]; then
    PIDS=" $(pidof $(basename $0)) "
    if [ -n "$(echo "${PIDS}" | grep " ${TIMERPID} ")" ]; then
      kill ${TIMERPID} 2>/dev/null
      if [ $? = 0 ]; then
        logdbg "Cancelled HDMI power off timer"
        sleep 1
      fi
    fi
    TIMERPID=0
  fi
}

#Check we can execute stuff
if [ ! -x ${TVSERVICE} -o ! -x ${TEXTURECACHE} ]; then
  logmsg "Cannot find ${TVSERVICE} or ${TEXTURECACHE} - exiting"
  exit 1
fi

#Exit if we're already running
if [ "$(pidof $(basename $0))" != "$$" ]; then
  logmsg "Already running - exiting"
  exit 1
fi

logmsg "Starting HDMI Power daemon for Raspberry Pi"
logmsg "HDMI Power off delay: ${DELAY} seconds"

while [ : ]; do
  logdbg "Establishing connection with XBMC..."

  ${TEXTURECACHE} @xbmc.host=localhost @logfile= monitor 2>/dev/null | 
    while IFS= read -r line; do
      METHOD="$(echo "${line}" | sed "s/.*: \(.*\..*\).*: {.*/\1/")"

      if [ "${METHOD}" = "GUI.OnScreensaverActivated" ]; then
        logdbg "Screensaver activated"
        start_timer ${DELAY}
      elif [ "${METHOD}" = "GUI.OnScreensaverDeactivated" ]; then
        logdbg "Screensaver deactivated"
        stop_timer
        enable_hdmi
      fi
    done

  logdbg "Waiting for XBMC to (re)start"
  sleep 15
done
