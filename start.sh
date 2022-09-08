crontab -l | { cat; echo "$DBALERT_SCHEDULE . /project_env.sh; python3 /dbalert.py > /proc/1/fd/1 2>/proc/1/fd/2"; } | crontab -
printenv | grep -v DBALERT_SCHEDULE | sed 's/^\(.*\)$/export \1/g' > /project_env.sh
crond -f
