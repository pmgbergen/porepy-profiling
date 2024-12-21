#!/bin/sh
echo "Job running at: $(date)"

echo "Pulling recent git changes"
git pull

echo "Starting asv profiling"
asv run --python=same --quick --show-stderr --dry-run

echo "Generating html report"
asv publish

echo "Publishing updates on github"
git add -A
git commit -m "Profiling $(date)"
git push

echo "Job completed successfully"