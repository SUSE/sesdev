
# make sure all minions are responding
set +ex
LOOP_COUNT="0"
while true ; do
  set -x
  sleep 5
  set +x
  if [ "$LOOP_COUNT" -ge "20" ] ; then
    echo "ERROR: minion(s) not responding to ping?"
    exit 1
  fi
  LOOP_COUNT="$((LOOP_COUNT + 1))"
  set -x
  MINIONS_RESPONDING="$(salt '*' test.ping | grep True | wc --lines)"
  if [ "$MINIONS_RESPONDING" = "{{ nodes|length }}" ]; then
    break
  fi
  set +x
done
set -ex
