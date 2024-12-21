FROM porepy/dev:latest

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables to avoid writing .pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# reverting to normal, because it is customized in the porepy image
ENV HOME=/root

# Create work directory
ENV APP_DIR=${HOME}/app
WORKDIR ${APP_DIR}

COPY requirements.txt ${APP_DIR}/

# Install dependencies and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    pip install --no-cache-dir -r requirements.txt && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

# Add GitHub SSH fingerprints to known_hosts
RUN mkdir -p /root/.ssh && \
    touch /root/.ssh/known_hosts && \
    ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts && \
    ssh-keyscan -t ecdsa-sha2-nistp256 github.com >> /root/.ssh/known_hosts && \
    ssh-keyscan -t rsa github.com >> /root/.ssh/known_hosts

# Copy repo
COPY . ${APP_DIR}/
    
# Git credentials
RUN git config --global user.username "Profiling runner" && \
    git config --global user.name "Profiling runner" && \
    git config --global user.email "none@none.com"
    
# Make the script executable and initialize the cron job.
RUN chmod +x ${APP_DIR}/job.sh && \
    chmod +x ${APP_DIR}/entrypoint.sh && \
    # Create the crontab file
    mv ${APP_DIR}/crontab.sh /etc/cron.d/job-cron && \
    chmod 0644 /etc/cron.d/job-cron && \
    crontab /etc/cron.d/job-cron && \
    # Create log file
    touch /var/log/cron.log

CMD ["sh", "-c", "${APP_DIR}/entrypoint.sh"]