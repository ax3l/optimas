<p align="center">
    <img width="400" src="https://user-images.githubusercontent.com/20479420/219680583-34ac9525-7715-4e2a-b4fe-74848e9f59b2.png" alt="optimas logo"/>
</p>
<!-- <hr/> -->

# Optimization and exploration at scale, powered by [libEnsemble](https://libensemble.readthedocs.io/)

## Installing

Optimas can be installed with `pip` directly from GitHub:

```
pip install git+https://github.com/optimas-org/optimas.git
```
Then, make sure you have `mpi4py` installed. This can be done with
```
pip install mpi4py
```
which will link to the existing MPI on your system.

Alternatively, if installing in a local computer, `mpi4py` can also be installed from `conda`
```
conda install -c conda-forge mpi4py
```

## Optimization with PIC simulations

Additonal instructions to install FBPIC and WarpX on different systems.

### On Summit

In the instructions below, before the `git clone` command, `cd` into your `$MEMBERWORK` folder, and create a dedicated directory.

#### For FBPIC simulations

Install according to:
https://fbpic.github.io/install/install_summit.html

Then install other dependencies:
```
source activate $SCRATCH/fbpic_env
pip install libensemble
git clone https://github.com/optimas-org/optimas.git
cd 
pip install .
source deactivate
```

#### For WarpX simulations
```
conda create -n 
source activate 
conda install -c conda-forge mamba
mamba install -c conda-forge openpmd-viewer openpmd-api pandas botorch ax-platform
pip install libensemble
git clone https://github.com/optimas-org/optimas.git
cd 
pip install .
```

### On Lawrencium

Install according to:
https://fbpic.github.io/install/install_lawrencium.html

Then install other dependencies:
```
pip install libensemble
pip install -r requirements.txt
```

`cd` into your `$SCRATCH` folder, and create a dedicated directory. Then run:
```
git clone https://github.com/optimas-org/optimas.git
cd 
pip install .
```

## Usage

A typical use case for `optimas` is to perform an optimization where each
evaluation is a numerical simulation. In this case, a simulation
script templated with `jinja2` syntax needs to be provided. In addition,
an analysis function needs to be defined that reads the simulation
output to extract the objective function(s) and other metrics.

The following example assumes that the template script is called
`template_simulation_script.py`, which takes 2 input parameters `x0`, `x1` to
optimize a single objective `f` using Baysian optimization.
The analysis function `analyze_simulation`
can also be defined in a separate file.

```python
from libe_opt.core import VaryingParameter, Objective
from libe_opt.generators import AxSingleFidelityGenerator
from libe_opt.evaluators import TemplateEvaluator
from libe_opt.explorations import Exploration


def analyze_simulation(simulation_directory, output_params):
    """Analyzes simulation output fills in output parameters."""
    # Read simulation data to determine `result`
    ...
    # Fill in output parameters.
    output_params['f'] = result
    return output_params


# Create varying parameters and objectives.
var_1 = VaryingParameter('x0', 0., 15.)
var_2 = VaryingParameter('x1', 0., 15.)
obj = Objective('f', minimize=True)


# Create generator.
gen = AxSingleFidelityGenerator(
    varying_parameters=[var_1, var_2],
    objectives=[obj],
    n_init=4
)


# Create evaluator.
ev = TemplateEvaluator(
    sim_template='template_simulation_script.py',
    analysis_func=analyze_simulation
)


# Create exploration.
exp = Exploration(
    generator=gen,
    evaluator=ev,
    max_evals=10,
    sim_workers=4,
    run_async=True
)


# To safely perform exploration, run it in the block below (this is needed
# for some flavours of multiprocessing, namely spawn and forkserver)
if __name__ == '__main__':
    exp.run()
```

Check the [examples](https://github.com/optimas-org/optimas/tree/main/examples)
 folder for more details.


You can easily postprocess the optimization in a Jupyter notebook by using:
```python
from optimas.post_processing import PostProcOptimization
pp = PostProcOptimization('path/to/your/optimization')
```
