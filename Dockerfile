FROM porepy/dev

# Install cron and other dependencies
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copy the job script into the container
COPY my-cron-job.sh  /usr/local/bin/my-cron-job.sh
RUN chmod +x /usr/local/bin/my-cron-job.sh

# Add the cron job (runs at midnight every day)
RUN echo "* * * * * /usr/local/bin/my-cron-job.sh" >> /etc/cron.d/my-cron-job

# Give execution rights to cron job
RUN chmod 0644 /etc/cron.d/my-cron-job

# Apply cron jobs
RUN crontab /etc/cron.d/my-cron-job

# Start cron in the foreground
CMD ["cron", "-f"]
