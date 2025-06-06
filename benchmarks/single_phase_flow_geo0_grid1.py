import porepy as pp
import numpy as np
from benchmarks.model_setups import make_benchmark_model


def make_model():
    return make_benchmark_model(
        {"geometry": 0, "grid_refinement": 1, "physics": "flow"}
    )


class PrepareSimulation:

    repeat = 5

    def setup(self):
        self.model = make_model()

    def time_prepare_simulation(self):
        self.model.prepare_simulation()


class PreSolve:

    repeat = 5

    def setup(self):
        self.model = make_model()
        self.model.prepare_simulation()

    def time_pre_solve(self):
        self.model.before_nonlinear_loop()
        self.model.before_nonlinear_iteration()
        self.model.assemble_linear_system()


class Solve:

    repeat = 5

    def setup(self):
        self.model = make_model()
        self.model.prepare_simulation()
        self.model.before_nonlinear_loop()
        self.model.before_nonlinear_iteration()
        self.model.assemble_linear_system()

    def time_solve(self):
        self.model.solve_linear_system()


# class RunSimulation:

#     repeat = 1

#     def setup(self):
#         self.model = make_model()
#         self.model.prepare_simulation()

#     def time_run_simulation(self):
#         pp.run_time_dependent_model(
#             self.model,
#             {
#                 "prepare_simulation": False,
#                 "nl_divergence_tol": 1e8,
#                 "max_iterations": 25,
#                 "nl_convergence_tol": 1e-2,
#                 "nl_convergence_tol_res": 1e-2,
#             },
#         )
