FROM porepy/dev:latest

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Create work directory
WORKDIR /app

# Install dependencies, set up the job, and clean up in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    # Clone the profiling repo
    git clone https://github.com/pmgbergen/porepy-profiling.git /app/ && \
    # Make the script executable
    chmod +x /app/job.sh && \
    # Create the crontab file
    echo "* * * * * /app/job.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/job-cron && \
    chmod 0644 /etc/cron.d/job-cron && \
    crontab /etc/cron.d/job-cron && \
    # Create log file
    touch /var/log/cron.log && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

# Create an entry script
RUN echo '#!/bin/sh\nservice cron start\nexec tail -f /var/log/cron.log' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Run the entry script using JSON format for proper signal handling
CMD ["sh", "/entrypoint.sh"]