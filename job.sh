#!/bin/sh
echo "Job running at: $(date)"

cd /root/app

export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1

echo "Pulling recent git changes"
git reset --hard main
git pull origin main

echo "Starting asv profiling"
/usr/local/bin/asv run NEW --steps=10 --launch-method=spawn --show-stderr

echo "Generating html report"
/usr/local/bin/asv publish

# Folder to check
FOLDER_TO_CHECK=".asv/"

# Check for changes
if git status --porcelain | grep -q -e "^ M  $FOLDER_TO_CHECK" -e "^?? $FOLDER_TO_CHECK"; then
    echo "Publishing updates on github"
    git add .asv
    git commit -m "Profiling update"
    git push origin main
else
    echo "No changes in $FOLDER_TO_CHECK."
fi

echo "Job completed successfully"