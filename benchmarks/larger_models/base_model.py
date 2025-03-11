import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import porepy as pp
import numpy as np
from time import time
import scipy.sparse as sps

from dataclasses import dataclass, field

from porepy.numerics.ad import _ad_utils


@dataclass
class TimeMeasurements:
    """Class for storing time measurements."""

    full_assembly: list[float] = field(default_factory=list)
    granular_discretization: dict = field(default_factory=dict)
    granular_assembly: dict = field(default_factory=dict)

    full_discretization: float = 0
    rediscretization: float = 0
    set_equations: float = 0
    set_geometry: float = 0
    linear_solve: float = 0
    visualization: float = 0

    discretization_parameters: float = 0
    before_nonlinear_iteration: float = 0
    after_nonlinear_iteration: float = 0
    check_nonlinear_convergence: float = 0


class TimedSolutionStrategy(pp.SolutionStrategy):
    """A solution strategy that measures the time taken by the different components."""

    def __init__(self, params: dict):
        super().__init__(params)

        self._timings = TimeMeasurements()

    def set_geometry(self):
        tic = time()
        super().set_geometry()
        self._timings.set_geometry = time() - tic
        print("Grid information: ")
        print(self.mdg.__repr__())

    def set_equations(self):
        tic = time()
        super().set_equations()
        self._timings.set_equations = time() - tic

    def set_discretization_parameters(self):
        tic = time()
        super().set_discretization_parameters()
        self._timings.discretization_parameters += time() - tic

    def discretize(self):
        full_time = time()

        # This is copied from EquationSystem.discretize
        equation_names = [key for key in self.equation_system.equations]
        discr = []
        for name in equation_names:
            # this raises a key error if a given equation name is unknown
            eqn = self.equation_system._equations[name]
            # This will expand the list discr with new discretizations.
            # The list may contain duplicates.
            discr += self.equation_system._recursive_discretization_search(eqn, list())

        # Uniquify to save computational time, then discretize.
        unique_discr = _ad_utils.uniquify_discretization_list(discr)

        self._discretize_from_list(unique_discr)
        self._timings.full_discretization += time() - full_time

    def rediscretize(self):
        tic = time()
        # Uniquify to save computational time, then discretize.
        unique_discr = pp.ad._ad_utils.uniquify_discretization_list(
            self.nonlinear_discretizations
        )
        self._discretize_from_list(unique_discr)
        self._timings.rediscretization += time() - tic

    def solve_linear_system(self):
        tic = time()
        ret = super().solve_linear_system()
        self._timings.linear_solve += time() - tic
        return ret

    def _discretize_from_list(self, unique_discr):
        mdg = self.mdg

        tm = self._timings.granular_discretization

        ### This is copied from _ad_utils.discretize
        for discr in unique_discr:
            # discr is a discretization (on node or interface in the
            # MixedDimensionalGrid sense)

            # Loop over all subdomains (or MixedDimensionalGrid edges), do
            # discretization.

            for g in unique_discr[discr]:
                tic = time()
                if isinstance(g, pp.MortarGrid):
                    data = mdg.interface_data(g)  # type:ignore
                    g_primary, g_secondary = mdg.interface_to_subdomain_pair(g)
                    d_primary = mdg.subdomain_data(g_primary)
                    d_secondary = mdg.subdomain_data(g_secondary)
                    discr.discretize(
                        g_primary, g_secondary, g, d_primary, d_secondary, data
                    )
                else:
                    data = mdg.subdomain_data(g)
                    try:
                        discr.discretize(g, data)
                    except NotImplementedError:
                        # This will likely be GradP and other Biot discretizations
                        pass
                toc = time() - tic

                name = discr.__class__.__name__
                dim = g.dim
                s = f"{name}_ dim={dim}"
                if s in tm:
                    tm[s] += toc
                else:
                    tm[s] = toc

    def before_nonlinear_loop(self):
        print(f"Time: {self.time_manager.time:.2f} of {self.time_manager.time_final}")
        super().before_nonlinear_loop()

    def before_nonlinear_iteration(self):
        tic = time()
        super().before_nonlinear_iteration()
        self._timings.before_nonlinear_iteration += time() - tic

    def after_nonlinear_iteration(self, nonlinear_increment):
        tic = time()
        super().after_nonlinear_iteration(nonlinear_increment)
        self._timings.after_nonlinear_iteration += time() - tic

    def check_convergence(
        self,
        nonlinear_increment: np.ndarray,
        residual,
        reference_residual: np.ndarray,
        nl_params,
    ):
        tic = time()
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

        self._timings.check_nonlinear_convergence += time() - tic
        return prm

    def assemble_linear_system(self):
        # This is copied from EquationSystem!
        # Be aware that the equation system is assemled twice, once by a standard
        # assembly (all equations) and once by a granular assembly (equation by
        # equation). The granular assembly is used to measure the time spent on each
        # equation.

        equation_system = self.equation_system

        variables = equation_system.variables

        # equ_blocks is a dictionary with equation names as keys and the corresponding
        # row indices of the equations. If the user has requested that equations are
        # restricted to a subset of grids, the row indices are restricted accordingly.
        # If no such request has been made, the value is None.
        equ_blocks: dict[str, np.ndarray | None] = equation_system._parse_equations()

        # Data structures for building matrix and residual vector
        mat: list[sps.spmatrix] = []
        rhs: list[np.ndarray] = []

        # Keep track of DOFs for each equation/block
        ind_start = 0

        # Store the indices of the assembled equations only if the Jacobian is
        # requested.

        equation_system.assembled_equation_indices = dict()

        eqs: list[pp.ad.Operator] = [
            equation_system._equations[name] for name in equ_blocks
        ]
        rows = list(equ_blocks.values())

        tic = time()
        ad_list: list[pp.ad.AdArray] = equation_system.evaluate(eqs, True, None)

        for row, equ_name, ad in zip(rows, equ_blocks, ad_list):
            if row is not None:
                # If restriction to grid-related row blocks was made, perform row
                # slicing based on information we have obtained from parsing.
                mat.append(ad.jac.tocsr()[row])
                rhs.append(ad.val[row])
                block_length = len(rhs[-1])
            else:
                # If no grid-related row restriction was made, append the whole
                # thing.
                mat.append(ad.jac)
                rhs.append(ad.val)
                block_length = len(ad.val)

            # Create indices range and shift to correct position.
            block_indices = np.arange(block_length) + ind_start
            # Extract last index and add 1 to get the starting point for next block
            # of indices.
            equation_system.assembled_equation_indices.update({equ_name: block_indices})
            if block_length > 0:
                ind_start = block_indices[-1] + 1

        # Concatenate results equation-wise.
        if len(rhs) > 0:
            A = sps.vstack(mat, format="csr")
            rhs_cat = np.concatenate(rhs)

        # Slice out the columns belonging to the requested subsets of variables and
        # grid-related column blocks by using the transposed projection to respective
        # subspace.
        # Multiply rhs by -1 to move to the rhs.
        column_projection = equation_system.projection_to(variables).transpose()
        self.linear_system = (A * column_projection, -rhs_cat)

        self._timings.full_assembly.append(time() - tic)

        # Granular timings
        tm = self._timings.granular_assembly
        for name, eq in equation_system.equations.items():
            tic = time()
            equation_system.evaluate(eq, True, None)
            if name in tm:
                tm[name].append(time() - tic)
            else:
                tm[name] = [time() - tic]

    def save_data_time_step(self) -> None:
        """Export the model state at a given time step and log time.

        The options for exporting times are:
            * `None`: All time steps are exported
            * `list`: Export if time is in the list. If the list is empty, then no
            times are exported.

        In addition, save the solver statistics to file if the option is set.

        """
        tic = time()
        super().save_data_time_step()
        self._timings.visualization += time() - tic

    def initialize_data_saving(self) -> None:
        """Initialize data saving.

        This method is called by :meth:`prepare_simulation` to initialize the
        exporter and any other data saving functionality (e.g., empty data
        containers to be appended in :meth:`save_data_time_step`).

        In addition, set path for storing solver statistics data to file for each
        time step.

        """

        tic = time()
        super().initialize_data_saving()
        self._timings.visualization += time() - tic

    def after_simulation(self):
        super().after_simulation()

        print("-----")
        print("Timings:")
        print(f"Set geometry time: {self._timings.set_geometry:.2e}")
        print("")

        print(f"Set equations time: {self._timings.set_equations:.2e}")
        print("")

        print(
            f"Discretization parameters time: {self._timings.discretization_parameters:.2e}"
        )
        print("")

        print(
            f"Before nonlinear iteration time: {self._timings.before_nonlinear_iteration:.2e}"
        )
        print("")

        print(f"Linear solve time: {self._timings.linear_solve:.2e}")
        print("")

        print(f"Visualization time: {self._timings.visualization:.2e}")
        print("")

        print(
            f"After nonlinear iteration time: {self._timings.after_nonlinear_iteration:.2e}"
        )
        print("")

        print(
            f"Check nonlinear convergence time: {self._timings.check_nonlinear_convergence:.2e}"
        )
        print("")

        num_assemblies = len(self._timings.full_assembly)

        print("Total number of assemblies: ", num_assemblies)

        assembly_sorted = sorted(
            self._timings.granular_assembly.keys(),
            key=lambda k: sum(self._timings.granular_assembly[k]),
            reverse=True,
        )

        if num_assemblies == 1:
            # Print the only assembly time, remove the list
            print(f"Assembly time: {self._timings.full_assembly[0]:.2e}")
            # Do the same for the granular assembly times
            for key in assembly_sorted:
                value = self._timings.granular_assembly[key]
                print(f"Assembly time for {key}: {value[0]:.2e}s")
        elif num_assemblies < 4:
            # Print the average assembly time, total and granular
            print(
                "Average assembly time: ",
                f"{sum(self._timings.full_assembly) / num_assemblies:.2e}",
            )
            for key in assembly_sorted:
                value = self._timings.granular_assembly[key]
                print(
                    f"Average assembly time for {key}: {sum(value) / num_assemblies:.2e}s"
                )
        else:  # Should be more than 3
            # Print both the average and the standard deviation on the same line
            print(
                "Average assembly time: ",
                f"{sum(self._timings.full_assembly) / num_assemblies:.2e}",
                " +/- ",
                f"{np.std(self._timings.full_assembly):.2e}",
            )
            for key in assembly_sorted:
                value = self._timings.granular_assembly[key]
                print(
                    f"Average assembly time for {key}: {sum(value) / num_assemblies:.2e}s",
                    " +/- ",
                    f"{np.std(value):.2e}",
                )

        print("")
        print(f"Full discretization time: {self._timings.full_discretization:.2e}")
        print(f"Rediscretization time: {self._timings.rediscretization:.2e}")
        print("")

        discretization_sorted = sorted(
            self._timings.granular_discretization.keys(),
            key=lambda k: self._timings.granular_discretization[k],
            reverse=True,
        )

        for key in discretization_sorted:
            value = self._timings.granular_discretization[key]
            print(f"Discretization time for {key}: {value:.2e}s")
