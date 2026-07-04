#!/bin/bash
# NeurOS — Start/Stop Script
# Run: ./neur-os.sh start   (starts on port 7447)
#      ./neur-os.sh stop    (stops the server)
#      ./neur-os.sh status  (check if running)
#      ./neur-os.sh backup  (backup database)

DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/backend/data/neur-os.pid"
PORT=7447

case "${1:-start}" in
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "NeurOS is already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    cd "$DIR"
    nohup python3 -m uvicorn backend.main:app --port "$PORT" --host 0.0.0.0 \
      > "$DIR/backend/data/neur-os.log" 2>&1 &
    echo $! > "$PIDFILE"
    echo "NeurOS started on http://localhost:$PORT (PID $!)"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null
      rm -f "$PIDFILE"
      echo "NeurOS stopped"
    else
      echo "NeurOS not running"
    fi
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "NeurOS is running (PID $(cat "$PIDFILE")) on http://localhost:$PORT"
    else
      echo "NeurOS is not running"
    fi
    ;;
  backup)
    curl -s -X POST "http://localhost:$PORT/api/export/backup" | python3 -m json.tool
    ;;
  *)
    echo "Usage: $0 {start|stop|status|backup}"
    exit 1
    ;;
esac
