"""Defines the analysis function that runs after the simulation."""

import numpy as np


def analyze_simulation(simulation_directory, output_params):
    """Read the simulation result and give it back to optimas."""
    a_x_abs = np.loadtxt("a_x_abs.txt")
    output_params["f"] = a_x_abs

    return output_params
