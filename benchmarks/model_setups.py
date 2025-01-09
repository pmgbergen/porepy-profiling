import warnings
from typing import Optional, Type

import porepy as pp
# Models 1 and 4 use FractureSolidConstants class, others use its parent SolidConstants.
from porepy.examples.flow_benchmark_2d_case_1 import BoundaryConditions as Case1BC
from porepy.examples.flow_benchmark_2d_case_1 import (
    FlowBenchmark2dCase1Model,
    FractureSolidConstants,
)
from porepy.examples.flow_benchmark_2d_case_1 import Geometry as Case1Geo
from porepy.examples.flow_benchmark_2d_case_1 import Permeability as Case1Permeability
from porepy.examples.flow_benchmark_2d_case_3 import (
    Case3aBoundaryConditions as Case3aBC,
)
from porepy.examples.flow_benchmark_2d_case_3 import FlowBenchmark2dCase3aModel
from porepy.examples.flow_benchmark_2d_case_3 import Geometry as Case3Geo
from porepy.examples.flow_benchmark_2d_case_3 import Permeability as Case3Permeability
from porepy.examples.flow_benchmark_2d_case_4 import BoundaryConditions as Case4BC
from porepy.examples.flow_benchmark_2d_case_4 import FlowBenchmark2dCase4Model
from porepy.examples.flow_benchmark_2d_case_4 import Geometry as Case4Geo
from porepy.examples.flow_benchmark_3d_case_3 import BoundaryConditions as Case3dBC
from porepy.examples.flow_benchmark_3d_case_3 import FlowBenchmark3dCase3Model
from porepy.examples.flow_benchmark_3d_case_3 import Geometry as Case3dGeo
from porepy.examples.flow_benchmark_3d_case_3 import Permeability as Case3dPermeability
from porepy.models.poromechanics import Poromechanics


# Ignore type errors inherent to the ``Poromechanics`` class.
class Case1Poromech2D(  # type: ignore[misc]
    Case1Permeability,
    Case1Geo,
    Case1BC,
    Poromechanics,
):
    pass


class Case3aPoromech2D(  # type: ignore[misc]
    Case3Permeability,
    Case3Geo,
    Case3aBC,
    Poromechanics,
):
    pass


class Case3Poromech3D(  # type: ignore[misc]
    Case3dPermeability,
    Case3dGeo,
    Case3dBC,
    Poromechanics,
):
    pass


class Case4Poromech2D(  # type: ignore[misc]
    Case4Geo,
    Case4BC,
    Poromechanics,
):
    pass


def make_benchmark_model(args: dict):
    """Create a benchmark model based on the provided arguments.

    Parameters:
        args: Command-line arguments containing the following
            attributes:
            - geometry (int): Specifies the geometry type (0, 1, or 2). Geometry 0 and 1
            are 2D grids, geometry 2 is a 2D grid with 64 fractures, and geometry 3 is a
            3D grid.
            - grid_refinement (int): Specifies the grid refinement level.
            - physics (str): Specifies the type of physics ("flow" or "poromechanics").

    Returns:
        model: An instance of the selected benchmark model with the specified
            parameters.

    Raises:
        ValueError: If the geometry or grid_refinement values are invalid, or if the
            combination of geometry and physics is not supported.

    """
    # Set up fixed model parameters.
    model_params = {
        "material_constants": {"solid": FractureSolidConstants()},
        "grid_type": "simplex",
        "time_manager": pp.TimeManager(
            dt_init=1,
            schedule=[0, 1],
            constant_dt=True,
        ),
    }

    # Warn user that the finest grid will likely take significant time.
    if args['grid_refinement'] >= 2:
        warnings.warn(
            f"{args['grid_refinement']=} will likely take significant time to run."
        )

    # Set cell_size/refinement_level model parameter based on choice of geometry and
    # grid refinement.
    if args['geometry'] in [0, 1, 2]:
        if args['grid_refinement'] == 0:
            cell_size = 0.1
        elif args['grid_refinement'] == 1:
            cell_size = 0.01
        elif args['grid_refinement'] == 2:
            cell_size = 0.005
        else:
            raise ValueError(f"{args['grid_refinement']=}")
        model_params["meshing_arguments"] = {"cell_size": cell_size}
    elif args['geometry'] == 3:
        model_params["refinement_level"] = args['grid_refinement']
    elif args.geometry == 4:
        if args['grid_refinement'] == 0:
            cell_size = 70
        elif args['grid_refinement'] == 1:
            cell_size = 35
        elif args['grid_refinement'] == 2:
            cell_size = 10
        else:
            raise ValueError(f"{args['grid_refinement']=}")
    else:
        raise ValueError(f"{args['grid_refinement']=}")

    # Select a model based on choice of physics and geometry.
    model: Optional[Type] = None
    if args['geometry'] == 0:
        if args['physics'] == "flow":
            model = FlowBenchmark2dCase1Model
        elif args['physics'] == "poromechanics":
            model = Case1Poromech2D
    elif args['geometry'] == 1:
        if args['physics'] == "flow":
            model = FlowBenchmark2dCase3aModel
        elif args['physics'] == "poromechanics":
            model = Case3aPoromech2D
    elif args['geometry'] == 2:
        if args['physics'] == "flow":
            model = FlowBenchmark2dCase4Model
        elif args['physics'] == "poromechanics":
            model = Case4Poromech2D
    elif args['geometry'] == 3:
        if args['physics'] == "flow":
            model = FlowBenchmark3dCase3Model
        elif args['physics'] == "poromechanics":
            model = Case3Poromech3D

    if model is None:
        raise ValueError(f"{args['geometry']=}, {args['physics']=}")

    return model(model_params)
