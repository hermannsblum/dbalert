# iterate through comma-separated list of schedule variables
Backup_of_internal_field_separator=$IFS
IFS=,
for station in $DBALERT_STATIONIDS; do
   crontab -l | { cat; echo "$DBALERT_SCHEDULE . /project_env.sh; python3 /dbalert.py --station-id $station > /proc/1/fd/1 2>/proc/1/fd/2"; } | crontab -
done
IFS=$Backup_of_internal_field_separator
crontab -l
printenv | grep -v DBALERT_SCHEDULE | sed 's/^\(.*\)$/export \1/g' > /project_env.sh
crond -f
