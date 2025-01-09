#!/bin/sh

# This script is initialized only once when the container is initially started.
# First, it collects the information about the machine with "asv machine" command.
# Next, it generates a new ssh keypair and prints the public key. The user must
# add this public key to their github account to allow pushes to the porepy-profiling repo.
# When the container is deleted, the keypair is forever gone.
# Finally, it runs the cron service.

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