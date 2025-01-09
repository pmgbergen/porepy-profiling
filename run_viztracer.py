"""This runscripts runs a selected porepy benchmark automatically with ``viztracer``
enabled and opens the results in a browser.

The alternative way to plug in the profiler to your script from the command line:
>>> viztracer --min_duration 0.01ms --ignore_frozen --ignore_c_function your_script.py
>>> vizviewer --port 9002 results.json

Example (intended to show basic input and output functionality):
    # If not already installed, get viztracer:
    >>> pip install viztracer
    # Run the script:
    >>> python run_profiler.py --physics poromechanics --geometry 0 --grid_refinement 0
    # This will run a single-phase poromechanics benchmark on the first 2D case with the
    # coarsest grid refinement.
    >>> python run_profiler.py --physics flow --geometry 1 --grid_refinement 2
    # This will run a single-phase flow benchmark on the second 2D case with the finest
    # grid refinement.
    >>> python run_profiler.py --physics poromechanics --geometry 2 --grid_refinement 2
    # This will run a single-phase poromechanics benchmark on a 3D grid with the finest
    # grid refinement.

Note: Running the 3D model on the finest grid requires ~20 GB ram (!), thus is not
    recommended on a local machine.

"""

import argparse
import pathlib
import subprocess
import porepy as pp
# VizTracer is missing stubs or py.typed marker, hence we ignore type errors.
from viztracer import VizTracer  # type: ignore[import]

from benchmarks.model_setups import make_benchmark_model


def run_model_with_tracer(args, model) -> None:
    """Run a model with VizTracer enabled for performance profiling.

    Parameters:
        args: Command-line arguments containing the following attributes:
            - physics (str): The physics of the model.
            - geometry (str): The geometry of the model.
            - grid_refinement (int): The grid refinement level for the model.
            - save_file (str): The file path to save the profiling results. If empty, a
            default name is generated based on chosen physics, geometry, and grid
            refinement.
            - min_duration (int): Minimum duration in microseconds for a function to be
            recorded by VizTracer.
            - keep_output (bool): Whether to keep the output file after viewing it.
        model: The model to be run and profiled.

    Raises:
        ValueError: If ``args.save_file`` does not end in .json.

    Returns:
        None

    """

    if args.save_file == "":
        save_file: str = (
            f"profiling_{args.physics}_{args.geometry}_{args.grid_refinement}.json"
        )
    else:
        if not args.save_file.endswith(".json"):
            raise ValueError(f"{args.save_file=}")
        save_file = args.save_file

    # Run model with viztracer enabled.
    tracer = VizTracer(
        min_duration=args.min_duration,  # μs
        ignore_c_function=True,
        ignore_frozen=True,
    )
    tracer.start()
    model.prepare_simulation()
    print("Num dofs:", model.equation_system.num_dofs())
    # Simulations use a single time step and relaxed Newton tolerance to ensure 1-2
    # Newton iterations. Material parameters are defaults and not realistic, as these
    # bencmarks are focusing on code segments (e.g., AD assembly) independent of
    # parameter realism.
    pp.run_time_dependent_model(
        model,
        {
            "prepare_simulation": False,
            "nl_divergence_tol": 1e8,
            "max_iterations": 25,
            "nl_convergence_tol": 1e-2,
            "nl_convergence_tol_res": 1e-2,
        },
    )
    tracer.stop()

    # Save the results and open them in a browser with vizviewer.
    results_path = pathlib.Path(__file__).parent / save_file
    tracer.save(str(results_path))
    subprocess.run(["vizviewer", "--port", "9002", results_path])
    if not args.keep_output:
        results_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--physics",
        type=str,
        default="flow",
        choices=["flow", "poromechanics"],
        help="Physics to run. Choices are single-phase flow or poromechanics.",
    )
    parser.add_argument(
        "--geometry",
        type=int,
        default=0,
        choices=[0, 1, 2, 3],
        help=(
            "0: 1st 2D case, 1: 2nd 2D case, 2: 2D case with 64 fractures, 3: 3D case."
        ),
    )
    parser.add_argument(
        "--grid_refinement",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Level of grid refinement. For the 2D cases, this corresponds to cell"
        + " sizes 0.1, 0.01, and 0.005. For the 3D cases, this corresponds to 30K,"
        + " 140K, 350K cells.",
    )
    parser.add_argument(
        "--save_file",
        type=str,
        default="",
        help="File to save the viztracer output to. If not specified, the file will be"
        + " named after the chosen physics, geometry, and grid refinement.",
    )
    parser.add_argument(
        "--keep_output",
        action="store_true",
        default=True,
        help="Keep viztracer output after running.",
    )
    parser.add_argument(
        "--min_duration",
        type=float,
        default=1e5,
        help="Profiling will include only the function calls with execution time higher"
        + " than this threshold, μs.",
    )

    args = parser.parse_args()
    model = make_benchmark_model(args.__dict__)
    run_model_with_tracer(args, model)
