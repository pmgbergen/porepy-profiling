import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"


import porepy as pp
import numpy as np
import time
from porepy.numerics.nonlinear import line_search

from base_model import TimedSolutionStrategy
from porepy.examples.flow_benchmark_2d_case_3 import (
    Geometry as FlowBenchmark2dCase3Geometry,
)

from porepy.examples.flow_benchmark_2d_case_4 import (
    Geometry as FlowBenchmark2dCase4Geometry,
)


class BoundaryConditions:
    def bc_values_stress(self, boundary_grid: pp.BoundaryGrid) -> np.ndarray:
        sides = self.domain_boundary_sides(boundary_grid)
        bc_values = np.zeros((self.nd, boundary_grid.num_cells))
        # rho * g * h
        # 2683 * 10 * 3000
        val = self.units.convert_units(8e7, units="Pa")
        bc_values[1, sides.north] = -val * boundary_grid.cell_volumes[sides.north]
        #  make the gradient
        bc_values[0, sides.west] = val * boundary_grid.cell_volumes[sides.west] * 1.2
        bc_values[0, sides.east] = -val * boundary_grid.cell_volumes[sides.east] * 1.2

        return bc_values.ravel("F")


class InitialCondition:
    def initial_condition(self) -> None:
        # Set initial condition for pressure, default values for other variables.
        super().initial_condition()
        num_cells = sum([sd.num_cells for sd in self.mdg.subdomains()])
        val = self.reference_variable_values.pressure * np.ones(num_cells)

        for time_step_index in self.time_step_indices:
            self.equation_system.set_variable_values(
                val,
                variables=[self.pressure_variable],
                time_step_index=time_step_index,
            )

        for iterate_index in self.iterate_indices:
            self.equation_system.set_variable_values(
                val,
                variables=[self.pressure_variable],
                iterate_index=iterate_index,
            )


class Source:
    def locate_source(self, subdomains):
        source_loc_x = self.domain.bounding_box["xmax"] * 0.5
        source_loc_y = self.domain.bounding_box["ymax"] * 0.5
        ambient = [sd for sd in subdomains if sd.dim == self.nd]
        fractures = [sd for sd in subdomains if sd.dim == self.nd - 1]
        lower = [sd for sd in subdomains if sd.dim <= self.nd - 2]

        x, y, z = np.concatenate([sd.cell_centers for sd in fractures], axis=1)
        source_loc = np.argmin((x - source_loc_x) ** 2 + (y - source_loc_y) ** 2)
        src_frac = np.zeros(x.size)
        src_frac[source_loc] = 1

        zeros_ambient = np.zeros(sum(sd.num_cells for sd in ambient))
        zeros_lower = np.zeros(sum(sd.num_cells for sd in lower))
        return np.concatenate([zeros_ambient, src_frac, zeros_lower])

    def fluid_source_mass_rate(self):
        if self.params["setup"]["steady_state"]:
            return 0
        else:
            return self.units.convert_units(1e1, "kg * s^-1")
            # maybe inject and then stop injecting?

    def fluid_source(self, subdomains: list[pp.Grid]) -> pp.ad.Operator:
        src = self.locate_source(subdomains)
        src *= self.fluid_source_mass_rate()
        return super().fluid_source(subdomains) + pp.ad.DenseArray(src)

    def energy_source(self, subdomains: list[pp.Grid]) -> pp.ad.Operator:
        src = self.locate_source(subdomains)
        src *= self.fluid_source_mass_rate()
        cv = self.fluid.components[0].specific_heat_capacity
        t_inj = (
            self.units.convert_units(273 + 40, "K")
            - self.reference_variable_values.temperature
        )
        src *= cv * t_inj
        return super().energy_source(subdomains) + pp.ad.DenseArray(src)


class SolutionStrategyLocalTHM:
    def after_simulation(self):
        super().after_simulation()
        vals = self.equation_system.get_variable_values(time_step_index=0)
        name = f"thm_endstate_{int(time.time() * 1000)}.npy"
        print("Saving", name)
        self.params["setup"]["end_state_filename"] = name
        np.save(name, vals)


class ConstraintLineSearchNonlinearSolver(
    line_search.ConstraintLineSearch,  # The tailoring to contact constraints.
    line_search.SplineInterpolationLineSearch,  # Technical implementation of the actual search along given update direction
    line_search.LineSearchNewtonSolver,  # General line search.
):
    """Collect all the line search methods in one class."""


class THMModelBase(
    TimedSolutionStrategy,
    Source,
    InitialCondition,
    BoundaryConditions,
    SolutionStrategyLocalTHM,
    pp.models.solution_strategy.ContactIndicators,
    pp.Thermoporomechanics,
):
    pass


class THMModel3dNoFracs(
    pp.model_geometries.CubeDomainOrthogonalFractures,
    THMModelBase,
):
    pass


class THMModel2dManyFracs(
    FlowBenchmark2dCase4Geometry,
    THMModelBase,
):
    pass


class THMModel2dTenFracs(
    FlowBenchmark2dCase3Geometry,
    THMModelBase,
):
    pass


def create_params(setup: dict):
    DAY = 24 * 60 * 60

    shear = 1.2e10
    lame = 1.2e10
    if setup["steady_state"]:
        biot = 0
        dt_init = 1e0
        end_time = 1e1
    else:
        biot = 0.47
        dt_init = 1e-3
        if setup["grid_refinement"] >= 33:
            dt_init = 1e-4
        end_time = 5e2
    porosity = 1.3e-2  # probably on the low side

    params = {
        "setup": setup,
        "folder_name": "visualization_2d_test",
        "material_constants": {
            "solid": pp.SolidConstants(
                # IMPORTANT
                permeability=1e-13,  # [m^2]
                residual_aperture=1e-3,  # [m]
                # LESS IMPORTANT
                shear_modulus=shear,  # [Pa]
                lame_lambda=lame,  # [Pa]
                dilation_angle=5 * np.pi / 180,  # [rad]
                normal_permeability=1e-4,
                # granite
                biot_coefficient=biot,  # [-]
                density=2683.0,  # [kg * m^-3]
                porosity=porosity,  # [-]
                friction_coefficient=0.577,  # [-]
                # Thermal
                specific_heat_capacity=720.7,
                thermal_conductivity=0.1,  # Diffusion coefficient
                thermal_expansion=9.66e-6,
            ),
            "fluid": pp.FluidComponent(
                compressibility=4.559 * 1e-10,  # [Pa^-1], fluid compressibility
                density=998.2,  # [kg m^-3]
                viscosity=1.002e-3,  # [Pa s], absolute viscosity
                # Thermal
                specific_heat_capacity=4182.0,  # Вместимость
                thermal_conductivity=0.5975,  # Diffusion coefficient
                thermal_expansion=2.068e-4,  # Density(T)
            ),
            "numerical": pp.NumericalConstants(
                characteristic_displacement=2e0,  # [m]
            ),
        },
        "reference_variable_values": pp.ReferenceVariableValues(
            pressure=3.5e7,  # [Pa]
            temperature=273 + 120,
        ),
        "grid_type": "simplex",
        "time_manager": pp.TimeManager(
            dt_init=dt_init * DAY,
            schedule=[0, end_time * DAY],
            iter_max=30,
            constant_dt=False,
        ),
        "units": pp.Units(kg=1e10),
        "meshing_arguments": {
            "cell_size": setup["cell_size"],
        },
        # experimental
        "adaptive_indicator_scaling": 1,  # Scale the indicator adaptively to increase robustness
    }
    return params


def run_model(setup: dict, model_class):
    params = create_params(setup)
    model = model_class(params)
    model.prepare_simulation()
    # print(model.simulation_name())

    print("Model geometry:")
    print(model.mdg)

    pp.run_time_dependent_model(
        model,
        {
            "prepare_simulation": False,
            "progressbars": False,
            "nl_convergence_tol": float("inf"),
            "nl_convergence_tol_res": 1e-10,
            "nl_divergence_tol": 1e8,
            "max_iterations": 30,
            # experimental
            "nonlinear_solver": ConstraintLineSearchNonlinearSolver,
            "Global_line_search": 0,  # Set to 1 to use turn on a residual-based line search
            "Local_line_search": 1,  # Set to 0 to use turn off the tailored line search
        },
    )

    # write_dofs_info(model)
    # print(model.simulation_name())


if __name__ == "__main__":
    if True:
        model_class = THMModel2dTenFracs
        cell_size = 0.02

    common_params = {
        "solver": "CPR",
        "cell_size": cell_size,
    }
    for g in [
        5,
        # 2,
        # 5,
        # 25,
        # 33,
        # 40,
    ]:
        print("Running steady state")
        tic = time.time()
        params = {
            "grid_refinement": g,
            "steady_state": True,
        } | common_params
        run_model(params, model_class)
        end_state_filename = params["end_state_filename"]

        print("Time for steady state", time.time() - tic)

        # EK: Comment out the injection part

        # print("Running injection")
        # params = {
        #     "grid_refinement": g,
        #     "steady_state": False,
        #     "initial_state": end_state_filename,
        #     "save_matrix": False,
        # } | common_params
        # run_model(params, model_class)
