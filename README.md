# Planning Task Minimizer
The source code of the minimizer can be found in the ```src/``` directory.

## Manual
The task minimizer can be used to shrink a planning task in the PDDL or SAS+ input language causing unexpected behavior in a planning system. Tasks are made smaller by deletion of randomly chosen task elements of a specified type (action, object, etc.).
The program has the following arguments:  

```python3 minimizer.py --problem PROBLEM [PROBLEM] --characteristic CHARACTERISTIC [CHARACTERISTIC] --delete OPTION [OPTION ...] [--truth] [--falsity] [--write-summary]```

- ```PROBLEM```: The command string that replicates the bug on the planning system.
    A second ```PROBLEM``` argument is interpreted as a reference planner execution command and requires a second ```CHARACTERISTIC``` argument. An example for the ```PROBLEM``` argument would be ```"/path/to/downward/builds/release/bin/downward --search 'astar(operatorcounting(constraint_generators=[state_equation_constraints()]))' --internal-plan-file sas_plan < /path/to/task-file.sas"```

- ```CHARACTERISTIC```: A characteristic string that should appear in the output after the execution of ```PROBLEM``` or, alternatively, the path to a Python file implementing the provided parser interface ```parserbase.py```. An example of a characteristic string would be ```"Segmentation fault."```. When a second ```PROBLEM``` argument is provided, a second ```CHARACTERISTIC``` argument is required.

- ```OPTION```: The specification of the task element type to be deleted in the planning task. For PDDL tasks, ```OPTION``` has to be either ```action```, ```object``` or ```predicate```. For SAS+ tasks, ```OPTION``` has to be either ```operator``` or ```variable```. Multiple ```OPTION``` arguments are accepted, e.g., ```object predicate action```.

When one of the ```OPTION``` arguments is ```predicate```, one of the additional options ```--truth``` or ```--falsity``` can be used. ```--truth``` has the effect that atoms containing the predicate to be deleted are replaced with the _truth_ value and ```--falsity``` has the effect that such atoms are replaced with _falsity_. By default, literals containing the predicate to be deleted are replaced with _truth_. When the option ```--write-summary``` is used, a text file with all deleted elements in order is created.

## Interpreter Requirements
Python 3.7+

