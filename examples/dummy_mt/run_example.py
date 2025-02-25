"""Basic example of parallel multitask Bayesian optimization with Ax"""

from optimas.core import VaryingParameter, Objective, Task
from optimas.generators import AxMultitaskGenerator
from optimas.evaluators import TemplateEvaluator, MultitaskEvaluator
from optimas.explorations import Exploration


def analyze_simulation(simulation_directory, output_params):
    """Analyze the simulation output.

    This method analyzes the output generated by the simulation to
    obtain the value of the optimization objective and other analyzed
    parameters, if specified. The value of these parameters has to be
    given to the `output_params` dictionary.

    Parameters
    ----------
    simulation_directory : str
        Path to the simulation folder where the output was generated.
    output_params : dict
        Dictionary where the value of the objectives and analyzed parameters
        will be stored. There is one entry per parameter, where the key
        is the name of the parameter given by the user.

    Returns
    -------
    dict
        The `output_params` dictionary with the results from the analysis.
    """
    # Read back result from file
    with open('result.txt') as f:
        result = float(f.read())
    # Fill in output parameters.
    output_params['f'] = result
    return output_params


# Create varying parameters and objectives.
var_1 = VaryingParameter('x0', 0., 15.)
var_2 = VaryingParameter('x1', 0., 15.)
obj = Objective('f', minimize=True)


# Create tasks.
lofi_task = Task('cheap_model', n_init=10, n_opt=3)
hifi_task = Task('expensive_model', n_init=2, n_opt=1)


# Create generator.
gen = AxMultitaskGenerator(
    varying_parameters=[var_1, var_2],
    objectives=[obj],
    lofi_task=lofi_task,
    hifi_task=hifi_task
)


# Create one evaluator for each task. In this example, both tasks use the same
# template, but in principle they can have different template, executor,
# analysis function, resources, etc.
ev_lofi = TemplateEvaluator(
    sim_template='template_simulation_script.py',
    analysis_func=analyze_simulation
)
ev_hifi = TemplateEvaluator(
    sim_template='template_simulation_script.py',
    analysis_func=analyze_simulation
)


# Create a multitask evaluator. This associates each task to each task
# evaluator.
ev = MultitaskEvaluator(
    tasks=[lofi_task, hifi_task],
    task_evaluators=[ev_lofi, ev_hifi]
)


# Create exploration.
exp = Exploration(
    generator=gen,
    evaluator=ev,
    max_evals=30,
    sim_workers=4,
    run_async=True
)


# To safely perform exploration, run it in the block below (this is needed
# for some flavours of multiprocessing, namely spawn and forkserver)
if __name__ == '__main__':
    exp.run()
