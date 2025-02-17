import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import porepy as pp
import numpy as np
from time import time
import scipy.sparse as sps

from porepy.numerics.nonlinear import line_search

from base_model import TimedSolutionStrategy
from porepy.examples.flow_benchmark_2d_case_4 import (
    Geometry as FlowBenchmark2dCase4Geometry,
    solid_constants,
)


class PoromechBase(
    TimedSolutionStrategy,
    pp.models.solution_strategy.ContactIndicators,
):
    def check_convergence(
        self,
        nonlinear_increment: np.ndarray,
        residual,
        reference_residual: np.ndarray,
        nl_params,
    ):
        # In addition to the standard check, print the iteration number, increment and
        # residual.
        prm = super().check_convergence(
            nonlinear_increment, residual, reference_residual, nl_params
        )
        nl_incr = self.nonlinear_solver_statistics.nonlinear_increment_norms[-1]
        res_norm = self.nonlinear_solver_statistics.residual_norms[-1]
        s = f"Newton iter: {self.nonlinear_solver_statistics.num_iteration} "
        s += f"Increment: {nl_incr:.2e}, Residual: {res_norm:.2e}"
        print(s)
        return prm


class Poromechanics3dNoFracs(
    PoromechBase,
    pp.model_geometries.CubeDomainOrthogonalFractures,
    pp.model_boundary_conditions.BoundaryConditionsMassDirWestEast,
    pp.model_boundary_conditions.BoundaryConditionsMechanicsDirNorthSouth,
    pp.Poromechanics,
):
    pass


class Poromechanics2dManyFracs(
    PoromechBase,
    FlowBenchmark2dCase4Geometry,
    pp.model_boundary_conditions.BoundaryConditionsMassDirWestEast,
    pp.model_boundary_conditions.BoundaryConditionsMechanicsDirNorthSouth,
    pp.Poromechanics,
):
    pass


class ConstraintLineSearchNonlinearSolver(
    line_search.ConstraintLineSearch,  # The tailoring to contact constraints.
    line_search.SplineInterpolationLineSearch,  # Technical implementation of the actual search along given update direction
    line_search.LineSearchNewtonSolver,  # General line search.
):
    """Collect all the line search methods in one class."""

    pass


if __name__ == "__main__":
    T_end = 1
    if True:
        time_manager = pp.TimeManager(
            dt_init=0.1,
            schedule=[0, T_end],
            constant_dt=True,
        )
        no_frac_params = {
            "fracture_indices": [],
            "meshing_arguments": {"cell_size": 0.1},
            "time_manager": time_manager,
            "nonlinear_solver": ConstraintLineSearchNonlinearSolver,
        }

        # Run the 3d case
        no_frac = Poromechanics3dNoFracs(params=no_frac_params)
        pp.run_time_dependent_model(
            model=no_frac,
        )

    if True:
        print(" ")
        print(" -------------- Starting 2d case --------------------")
        T_end = 1e4
        time_manager = pp.TimeManager(
            dt_init=0.1 * T_end,
            schedule=[0, T_end],
            constant_dt=True,
        )
        many_frac_params = {
            "time_manager": time_manager,
            "material_constants": {"solid": solid_constants},
            "nonlinear_solver": ConstraintLineSearchNonlinearSolver,
        }

        # Run the 2d case
        many_fracs = Poromechanics2dManyFracs(params=many_frac_params)
        pp.run_time_dependent_model(
            model=many_fracs,
        )
