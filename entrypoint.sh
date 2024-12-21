#!/bin/sh

# Initialize the machine information
cd ${APP_DIR}
/usr/local/bin/asv machine --yes

# Generate SSH key pair without a passphrase
ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -N ""

# Setting ssh origin to authorize via the generated key
git remote remove origin && \
git remote add origin git@github.com:pmgbergen/porepy-profiling.git &&\
git branch --track origin main
# Printing the public key
echo "SSH key pair has been generated."
echo "Public key (add to GitHub):"
cat /root/.ssh/id_rsa.pub
echo "\n\n"

service cron start
exec tail -f /var/log/cron.log