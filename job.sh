#!/bin/sh
echo "Job running at: $(date)"

cd /root/app

echo "Pulling recent git changes"
git pull origin main

echo "Starting asv profiling"
/usr/local/bin/asv run NEW --steps=10

echo "Generating html report"
/usr/local/bin/asv publish

echo "Publishing updates on github"
git add .asv
git commit -m "Profiling update"
git push origin main

echo "Job completed successfully"