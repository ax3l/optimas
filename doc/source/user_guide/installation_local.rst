Installation on a local computer
--------------------------------

The recommended approach is to install optimas in a ``conda`` environment.

Install ``mpi4py``
~~~~~~~~~~~~~~~~~~
If your system has already an MPI implementation installed, install ``mpi4py``
using ``pip``:

.. code::

    pip install mpi4py

This will make sure that optimas uses the existing MPI. The recommended
MPI implementation is MPICH.

If you don't have an existing MPI installation, the recommended approach is to
install ``mpi4py`` from ``conda``, including the MPI implementation corresponding
to your operating system.

On Linux and macOS:

.. code::

    conda install -c conda-forge mpi4py mpich

On Windows:

.. code::

    conda install -c conda-forge mpi4py msmpi

Install optimas
~~~~~~~~~~~~~~~
Install the latest release from PyPI

.. code::

    pip install optimas
