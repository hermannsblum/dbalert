printenv | sed 's/^\(.*\)$/export \1/g' > /project_env.sh
crond -f
#cron -f
