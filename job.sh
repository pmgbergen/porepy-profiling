#!/bin/sh

# This script is executed once in a while via cron. Commiting and pushing changes to it
# should be enough for cron to fetch it (tested).

echo "Job running at: $(date)"

cd /root/app

export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1

# Updating the porepy-profiling repo.
echo "Pulling recent git changes"
git reset --hard main  # This is a safeguard if something unexpected happens.
git pull origin main

echo "Starting asv profiling"
/usr/local/bin/asv run 2eade74a9441050215920da28370e1d701f800fd..develop --steps=10 --skip-existing-commits --launch-method=spawn --show-stderr

echo "Generating html report"
/usr/local/bin/asv publish

# Folder to check
FOLDER_TO_CHECK=".asv/"

# Check for changes. Only commit and push if the new report entries appeared.
if git status --porcelain | grep -q -e "^ M  $FOLDER_TO_CHECK" -e "^?? $FOLDER_TO_CHECK"; then
    echo "Publishing updates on github"
    git add .asv
    git commit -m "Profiling update"
    git push origin main
else
    echo "No changes in $FOLDER_TO_CHECK."
fi

echo "Job completed successfully"