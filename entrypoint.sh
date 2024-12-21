#!/bin/sh
service cron start
exec tail -f /var/log/cron.log