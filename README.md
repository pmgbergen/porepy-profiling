# Periodic profiling of PorePy

This repository contains the runscripts for the periodic profiling of [PorePy](https://github.com/pmgbergen/porepy), which allows to trace performance improvement or regression among different commits of the develop branch. The runscripts are based on the [asv](https://github.com/airspeed-velocity/asv) package.

The report can be found here: https://pmgbergen.github.io/porepy-profiling/

## Write your benchmarks

The benchmark cases must be located in the `benchmarks/` folder. Commiting them into the repository will do the job and they will appear in the report when the periodic job runs, typically once a day. To write your benchmark case, see the [asv tutorial](https://asv.readthedocs.io/en/latest/writing_benchmarks.html).

Before pushing the benchmark case, test if it works correctly:

`asv run --python=same --quick --dry-run --launch-method=spawn --show-stderr`

The actual run command (if you want to run the full benchmark suite locally):

`asv run --launch-method=spawn --show-stderr`

Other useful commands: `asv publish` generates html reports, `asv preview` opens the report in a browser.

## Manual profiling

To investigate your program performance, we suggest the [viztracer](https://github.com/gaogaotiantian/viztracer) package. See the quickstart runscript for it: [run_viztracer.py](run_viztracer.py).