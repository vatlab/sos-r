[![PyPI version](https://badge.fury.io/py/sos-r.svg)](https://badge.fury.io/py/sos-r)
[![Build Status](https://travis-ci.org/vatlab/sos-r.svg?branch=master)](https://travis-ci.org/vatlab/sos-r)
[![Build status](https://ci.appveyor.com/api/projects/status/aa4cha4d57q7lhbq/branch/master?svg=true)](https://ci.appveyor.com/project/BoPeng/sos-r/branch/master)

# SoS language module for R

[SoS Notebook](https://github.com/vatlab/sos-notebook) is a [Jupyter](https://jupyter.org/) kernel that allows the use of multiple kernels in one Jupyter notebook. Although SoS Notebook can [work with any kernels using magics `%expand`, `%capture` and `%render`](https://vatlab.github.io/sos-docs/doc/user_guide/expand_capture_render.html), a language module allows the [exchange of variables among supported languages using magics `%get`, `%put`, `%use`, and `%with`](https://vatlab.github.io/sos-docs/doc/user_guide/exchange_variable.html). This module provides a language module for the R programming language.

## Installation

### Conda installation

If you are using a conda environment, 


```
conda install sos-r -c conda-forge
```

installs all required component of `sos-r`, including [`sos-notebook`](https://github.com/vatlab/sos-notebook), `R`, `irkernel`, and required packages.

### Pip installation

If you are not using a conda environment, or if you would like to use a standalone `R` installation (instead of conda's R), you should install `sos-notebook`, `sos-r` etc separately. Please refer to [Running SoS](https://vatlab.github.io/sos-docs/running.html#r) for details. 

## Documentation

After proper installation of `sos-r`, you should see language `R` in the language selection dropdown box of a SoS Notebook. Please refer to [SoS Homepage](http://vatlab.github.io/SoS/) and [SoS Notebook Documentation](https://vatlab.github.io/sos-docs/notebook.html#content) for details.
