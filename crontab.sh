# This runs the script job.sh as a cronjob every hour and redirects its log, both stdout and stderr.
0 * * * * sh /root/app/job.sh >> /var/log/cron.log 2>&1
