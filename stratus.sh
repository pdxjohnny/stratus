#! /bin/sh
# /etc/init.d/stratus
#
# Starts or stops the stratus server

#Edit these variables!
RUN_USER=username

case "$1" in
  start)
    echo "Starting stratus..."
    sudo -H -b -u $RUN_USER python -m stratus start
    ;;
  stop)
    echo "Stoping stratus..."
    sudo -H -b -u $RUN_USER python -m stratus stop
    ;;
  *)
    echo "Usage: service stratus {start|stop}"
    exit 1
    ;;
esac

exit 0
