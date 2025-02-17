import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import porepy as pp
import numpy as np
from time import time
import scipy.sparse as sps


from base_model import TimedSolutionStrategy
from porepy.examples.flow_benchmark_2d_case_4 import (
    FlowBenchmark2dCase4Model,
    solid_constants,
)


class FlowModel3dNoFracs(
    TimedSolutionStrategy,
    pp.model_geometries.CubeDomainOrthogonalFractures,
    pp.model_boundary_conditions.BoundaryConditionsMassDirWestEast,
    pp.SinglePhaseFlow,
):
    pass


class FlowModel2dManyFracs(TimedSolutionStrategy, FlowBenchmark2dCase4Model):
    pass


if __name__ == "__main__":
    T_end = 10
    if True:
        time_manager = pp.TimeManager(
            dt_init=1,
            schedule=[0, T_end],
            constant_dt=True,
        )
        no_frac_params = {
            "fracture_indices": [],
            "meshing_arguments": {"cell_size": 0.1},
            "time_manager": time_manager,
        }

        # Run the 3d case
        no_frac = FlowModel3dNoFracs(params=no_frac_params)
        pp.run_time_dependent_model(
            model=no_frac,
        )

    if True:
        print(" ")
        print(" -------------- Starting 2d case --------------------")

        time_manager = pp.TimeManager(
            dt_init=1,
            schedule=[0, T_end],
            constant_dt=True,
        )
        many_frac_params = {
            "time_manager": time_manager,
            "material_constants": {"solid": solid_constants},
        }

        # Run the 2d case
        many_fracs = FlowModel2dManyFracs(params=many_frac_params)
        pp.run_time_dependent_model(
            model=many_fracs,
        )
