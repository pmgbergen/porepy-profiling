The report can be found here: https://pmgbergen.github.io/porepy-profiling/

Test if benchmarks work correctly:

`asv run --python=same --quick --dry-run --launch-method=spawn --show-stderr`

Actually run them:

`asv run --launch-method=spawn --show-stderr`

Generate html report:

`asv publish`

Open report in browser:

`asv preview`