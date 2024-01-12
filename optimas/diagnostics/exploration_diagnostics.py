"""Contains the definition of the ExplorationDiagnostics class."""
import os
from warnings import warn
import pathlib
import json
from typing import Optional, List, Tuple, Union

import numpy as np
import numpy.typing as npt
import pandas as pd
import matplotlib.pyplot as plt

from optimas.core import VaryingParameter, Objective, Parameter
from optimas.generators.base import Generator
from optimas.evaluators.base import Evaluator
from optimas.explorations import Exploration


class ExplorationDiagnostics:
    """Utilities for analyzing the output of an exploration.

    Parameters
    ----------
    source : str
        Path to the exploration directory or to an
        individual `.npy` history file, or an ``Exploration`` instance.
    """

    def __init__(self, source: Union[str, Exploration]) -> None:
        if isinstance(source, str):
            path = source
            # Find the `npy` file that contains the results
            if os.path.isdir(path):
                # Get history files sorted by creation date.
                output_files = [
                    filename
                    for filename in os.listdir(path)
                    if "_history_" in filename and filename.endswith(".npy")
                ]
                output_files.sort(
                    key=lambda f: os.path.getmtime(os.path.join(path, f))
                )
                if len(output_files) == 0:
                    raise RuntimeError(
                        "The specified path does not contain any history file."
                    )
                elif len(output_files) > 1:
                    warn(
                        "The specified path contains multiple history files. "
                        "The most recent one will be used."
                    )
                output_file = os.path.join(path, output_files[-1])
                params_file = os.path.join(path, "exploration_parameters.json")
            elif path.endswith(".npy"):
                output_file = path
                params_file = os.path.join(
                    pathlib.Path(path).parent, "exploration_parameters.json"
                )
            else:
                raise RuntimeError(
                    "The path should either point to a folder or a `.npy` file."
                )
            exploration = self._create_exploration(params_file, output_file)
        elif isinstance(source, Exploration):
            exploration = source
        else:
            ValueError(
                "The source of the exploration diagnostics should be a `path` "
                f"or an `Exploration`, not of type {type(source)}."
            )
        self._exploration = exploration

    def _create_exploration(
        self, params_file: str, history_path: str
    ) -> Exploration:
        """Create exploration from saved files."""
        # Create exploration parameters.
        varying_parameters = []
        analyzed_parameters = []
        objectives = []
        with open(params_file) as f:
            d = json.load(f)
        for _, param in d.items():
            if param["type"] == "VaryingParameter":
                p = VaryingParameter.model_validate_json(param["value"])
                varying_parameters.append(p)
            elif param["type"] == "Objective":
                p = Objective.model_validate_json(param["value"])
                objectives.append(p)
            elif param["type"] == "Parameter":
                p = Parameter.model_validate_json(param["value"])
                analyzed_parameters.append(p)

        # Create exploration using dummy generator and evaluator.
        return Exploration(
            generator=Generator(
                varying_parameters=varying_parameters,
                objectives=objectives,
                analyzed_parameters=analyzed_parameters,
            ),
            evaluator=Evaluator(sim_function=None),
            history=history_path,
        )

    @property
    def history(self) -> pd.DataFrame:
        """Return a pandas DataFrame with the exploration history."""
        return self._exploration.history

    @property
    def varying_parameters(self) -> List[VaryingParameter]:
        """Get the varying parameters of the exploration."""
        return self._exploration.generator.varying_parameters

    @property
    def analyzed_parameters(self) -> List[Parameter]:
        """Get the analyzed parameters of the exploration."""
        return self._exploration.generator.analyzed_parameters

    @property
    def objectives(self) -> List[Objective]:
        """Get the objectives of the exploration."""
        return self._exploration.generator.objectives

    def plot_objective(
        self,
        objective: Optional[Union[str, Objective]] = None,
        fidelity_parameter: Optional[str] = None,
        show_trace: Optional[bool] = False,
        use_time_axis: Optional[bool] = False,
        relative_start_time: Optional[bool] = True,
    ) -> None:
        """Plot the values that where reached during the optimization.

        Parameters
        ----------
        objective : str, optional
            Objective, or name of the objective to plot. If `None`, the first
            objective of the exploration is shown.
        fidelity_parameter: str, optional
            Name of the fidelity parameter. If given, the different fidelity
            will be plotted in different colors.
        show_trace : bool, optional
            Whether to show the cumulative maximum or minimum of the objective.
        use_time_axis : bool, optional
            Whether the x axis should be the time at which the evaluations
            were completed, instead of the evaluation index.
        relative_start_time : bool, optional
            Whether the time axis should be relative to the start time
            of the exploration. By default, True.

        """
        if fidelity_parameter is not None:
            fidelity = self.history[fidelity_parameter]
        else:
            fidelity = None
        if objective is None:
            objective = self.objectives[0]
        elif isinstance(objective, str):
            objective_names = [obj.name for obj in self.objectives]
            if objective in objective_names:
                objective = self.objectives[objective_names.index(objective)]
            else:
                raise ValueError(
                    f"Objective {objective} not found. Available objectives "
                    f"are {objective_names}."
                )
        history = self.history
        history = history[history.sim_ended]
        if use_time_axis:
            x = history.sim_ended_time
            xlabel = "Time (s)"
            if relative_start_time:
                x = x - history["gen_started_time"].min()
        else:
            x = history.trial_index
            xlabel = "Number of evaluations"
        _, ax = plt.subplots()
        ax.scatter(x, history[objective.name], c=fidelity)
        ax.set_ylabel(objective.name)
        ax.set_xlabel(xlabel)

        if show_trace:
            t_trace, obj_trace = self.get_objective_trace(
                objective,
                fidelity_parameter,
                use_time_axis=use_time_axis,
                relative_start_time=relative_start_time,
            )
            ax.step(t_trace, obj_trace, where="post")

    def plot_pareto_frontier(
        self,
        objectives: Optional[List[Union[str, Objective]]] = None,
        show_best_evaluation_indices: Optional[bool] = False,
    ) -> None:
        """Plot Pareto frontier of two optimization objectives.

        Parameters
        ----------
        objectives : list of str or Objective, optional
            A list with two objectives to plot. Only needed when the
            optimization had more than two objectives. By default ``None``.
        show_best_evaluation_indices : bool, optional
            Whether to show the indices of the best evaluations. By default
            ``False``.
        """
        if len(self.objectives) < 2:
            raise ValueError(
                "Cannot get Pareto frontier because only a single objective "
                "is available."
            )
        if objectives is None:
            if len(self.objectives) == 2:
                objectives = self.objectives
            else:
                raise ValueError(
                    f"There are {len(self.objectives)} available. "
                    "Please specify 2 objectives from which to plot the "
                    "Pareto frontier."
                )
        else:
            if len(objectives) != 2:
                raise ValueError(
                    f"This plot requires 2 objectives ({len(objectives)} "
                    "given)."
                )
            for i, objective in enumerate(objectives):
                if isinstance(objective, str):
                    objective_names = [obj.name for obj in self.objectives]
                    if objective in objective_names:
                        objectives[i] = self.objectives[
                            objective_names.index(objective)
                        ]
                    else:
                        raise ValueError(
                            f"Objective {objective} not found. "
                            f"Available objectives are {objective_names}."
                        )

        # Get pareto front
        x_data = self.history[objectives[0].name].to_numpy()
        y_data = self.history[objectives[1].name].to_numpy()
        x_minimize = objectives[0].minimize
        y_minimize = objectives[1].minimize
        i_sort = np.argsort(x_data)
        if not x_minimize:
            i_sort = i_sort[::-1]  # Sort in descending order
        if y_minimize:
            y_cum = np.minimum.accumulate(y_data[i_sort])
        else:
            y_cum = np.maximum.accumulate(y_data[i_sort])

        # Create figure
        _, axes = plt.subplots()

        # Plot all evaluations
        axes.scatter(
            x_data, y_data, s=5, lw=0.0, alpha=0.5, label="All evaluations"
        )
        axes.set(xlabel=objectives[0].name, ylabel=objectives[1].name)

        # Plot best evaluations
        y_pareto, i_pareto = np.unique(y_cum, return_index=True)
        x_pareto = x_data[i_sort][i_pareto]
        axes.scatter(
            x_pareto,
            y_pareto,
            s=15,
            ec="k",
            fc="tab:blue",
            lw=0.5,
            zorder=2,
            label="Best evaluations",
        )

        # Plot pareto front
        axes.step(
            x_data[i_sort],
            y_cum,
            c="k",
            lw=1,
            where="post",
            zorder=1,
            label="Pareto frontier",
        )
        axes.legend(frameon=False)

        # Add evaluation indices to plot.
        if show_best_evaluation_indices:
            sim_id_pareto = self.history["sim_id"].to_numpy()[i_sort][i_pareto]
            for i, id in enumerate(sim_id_pareto):
                axes.annotate(
                    str(id),
                    (x_pareto[i], y_pareto[i]),
                    (2, -2),
                    fontsize=6,
                    va="top",
                    textcoords="offset points",
                )

    def get_objective_trace(
        self,
        objective: Optional[Union[str, Objective]] = None,
        fidelity_parameter: Optional[str] = None,
        min_fidelity: Optional[float] = None,
        use_time_axis: Optional[bool] = False,
        t_array: Optional[npt.NDArray] = None,
        relative_start_time: Optional[bool] = True,
    ) -> Tuple[npt.NDArray, npt.NDArray]:
        """Get the cumulative maximum or minimum of the objective.

        Parameters
        ----------
        objective : str, optional
            Objective, or name of the objective to plot. If `None`, the first
            objective of the exploration is shown.
        fidelity_parameter: str, optional
            Name of the fidelity parameter. If `fidelity_parameter`
            and `min_fidelity` are set, only the runs with fidelity
            above `min_fidelity` are considered.
        fidelity_min: float, optional
            Minimum fidelity above which points are considered
        use_time_axis : bool, optional
            Whether the x axis should be the time at which the evaluations
            were completed, instead of the evaluation index.
        t_array: 1D numpy array, optional
            Array with time values. If provided, the trace is interpolated
            to the times in the array. Requires ``use_time_axis=True``.
        relative_start_time : bool, optional
            Whether the time axis should be relative to the start time
            of the exploration. By default, True.

        Returns
        -------
        time : 1D numpy array
        objective_trace : 1D numpy array
        """
        if objective is None:
            objective = self.objectives[0]
        elif isinstance(objective, str):
            objective_names = [obj.name for obj in self.objectives]
            if objective in objective_names:
                objective = self.objectives[objective_names.index(objective)]
            else:
                raise ValueError(
                    f"Objective {objective} not found. Available objectives "
                    f"are {objective_names}."
                )
        if fidelity_parameter is not None:
            assert min_fidelity is not None
            df = self.history[self.history[fidelity_parameter] >= min_fidelity]
        else:
            df = self.history.copy()
        df = df[df.sim_ended]

        if use_time_axis:
            df = df.sort_values("sim_ended_time")
            x = df.sim_ended_time
            if relative_start_time:
                x = x - df["gen_started_time"].min()
            x = x.values
        else:
            x = df.trial_index.values

        if objective.minimize:
            obj_trace = df[objective.name].cummin().values
        else:
            obj_trace = df[objective.name].cummax().values

        if t_array is not None:
            # Interpolate the trace curve on t_array
            N_interp = len(t_array)
            N_ref = len(x)
            obj_trace_array = np.zeros_like(t_array)
            i_ref = 0
            for i_interp in range(N_interp):
                while i_ref < N_ref - 1 and x[i_ref + 1] < t_array[i_interp]:
                    i_ref += 1
                obj_trace_array[i_interp] = obj_trace[i_ref]
            x = t_array
            obj_trace = obj_trace_array

        return x, obj_trace

    def plot_worker_timeline(
        self,
        fidelity_parameter: Optional[str] = None,
        relative_start_time: Optional[bool] = True,
    ) -> None:
        """Plot the timeline of worker utilization.

        Parameters
        ----------
        fidelity_parameter: string or None
            Name of the fidelity parameter. If given, the different fidelity
            will be plotted in different colors.
        relative_start_time : bool, optional
            Whether the time axis should be relative to the start time
            of the exploration. By default, True.
        """
        df = self.history
        if fidelity_parameter is not None:
            min_fidelity = df[fidelity_parameter].min()
            max_fidelity = df[fidelity_parameter].max()

        sim_started_time = df["sim_started_time"]
        sim_ended_time = df["sim_ended_time"]
        if relative_start_time:
            sim_started_time = sim_started_time - df["gen_started_time"].min()
            sim_ended_time = sim_ended_time - df["gen_started_time"].min()
        _, ax = plt.subplots()
        for i in range(len(df)):
            start = sim_started_time.iloc[i]
            duration = sim_ended_time.iloc[i] - start
            if fidelity_parameter is not None:
                fidelity = df[fidelity_parameter].iloc[i]
                color = plt.cm.viridis(
                    (fidelity - min_fidelity) / (max_fidelity - min_fidelity)
                )
            else:
                color = "tab:blue"
            ax.barh(
                [str(df["sim_worker"].iloc[i])],
                [duration],
                left=[start],
                color=color,
                edgecolor="k",
                linewidth=1,
            )

        ax.set_ylabel("Worker")
        ax.set_xlabel("Time (s)")
