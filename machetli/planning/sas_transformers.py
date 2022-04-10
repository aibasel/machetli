from collections import Generator
import copy
import random

from machetli.planning.downward_lib import timers
from machetli.planning.downward_lib.sas_tasks import SASTask, SASMutexGroup, SASGoal, SASOperator, SASInit, SASAxiom

SEED = 42


class SASTransformer:
    """Interface for SAS+ transformer classes."""

    def get_successors(self, sas_task):
        """Return task generator representing successors of input task."""
        raise NotImplementedError("This method should be implemented.")


class SASOperatorEraser(SASTransformer):
    """Performs SAS+ task transformations by erasing SASOperators"""

    def get_successors(self, sas_task: SASTask) -> Generator:
        """Creates and returns generator of successors of given SAS+ task by deleting SASOperators."""
        operator_names = [operator.name for operator in sas_task.operators]
        random.Random(SEED).shuffle(operator_names)
        for name in operator_names:
            pre_child = copy.deepcopy(sas_task)
            with timers.timing("Obtaining successor"):
                child = self.transform(pre_child, name)
            yield child, name

    def transform(self, sas_task, op_name):
        """Transforms sas_task by deleting the operator called op_name."""
        new_operators = [op for op in sas_task.operators if not op.name == op_name]

        return SASTask(sas_task.variables, sas_task.mutexes, sas_task.init, sas_task.goal, new_operators,
                       sas_task.axioms, sas_task.metric)


class SASVariableEraser(SASTransformer):
    """Performs SAS+ task transformations by erasing SASVariables."""

    def get_successors(self, sas_task) -> Generator:
        """Creates and returns generator of successors of given SAS+ task by deleting SASVariables."""
        variables = [var for var in range(len(sas_task.variables.axiom_layers))]
        random.Random(SEED).shuffle(variables)
        for var in variables:
            pre_child = copy.deepcopy(sas_task)
            with timers.timing("Obtaining successor"):
                child = self.transform(pre_child, var)
            yield child, var

    def transform(self, sas_task, var):
        """Transforms sas_task by deleting variable with index var."""
        # remove var attributes from variables object
        new_variables = sas_task.variables
        del new_variables.axiom_layers[var]
        del new_variables.ranges[var]
        del new_variables.value_names[var]
        # remove var from from mutex groups
        new_mutexes = []
        for group in sas_task.mutexes:
            new_facts = []
            for fact in group.facts:
                if fact[0] == var:
                    continue
                if fact[0] > var:
                    variable_index, value = fact
                    variable_index = variable_index - 1  # decrement variable indices above var
                    fact = (variable_index, value)
                new_facts.append(fact)
            new_mutexes.append(SASMutexGroup(new_facts))
        # remove var from init
        new_init = SASInit(sas_task.init.values)
        del new_init.values[var]
        # remove var from goal pairs and decrement higher indices than var
        new_goal_pairs = []
        for pair in sas_task.goal.pairs:
            if pair[0] == var:
                continue
            if pair[0] > var:
                variable_index, value = pair
                variable_index = variable_index - 1  # decrement variable indices above var
                pair = (variable_index, value)
            new_goal_pairs.append(pair)
        new_goal = SASGoal(new_goal_pairs)
        # remove var from operators
        new_operators = []
        for op in sas_task.operators:
            new_prevail = []
            for pre in op.prevail:
                if pre[0] == var:
                    continue
                if pre[0] > var:
                    variable_index, value = pre
                    variable_index = variable_index - 1  # decrement variable indices above var
                    pre = (variable_index, value)
                new_prevail.append(pre)
            new_effects = []
            for eff in op.pre_post:
                v, pre, post, cond = eff
                if v == var:
                    continue
                if v > var:
                    v = v - 1  # decrement variable indices above var
                new_cond = []
                for precondition in cond:
                    if precondition[0] == var:
                        continue
                    if precondition[0] > var:
                        variable_index, value = precondition
                        variable_index = variable_index - 1  # decrement variable indices above var
                        precondition = (variable_index, value)
                    new_cond.append(precondition)
                new_effects.append((v, pre, post, new_cond))
            if not new_effects:
                continue
            new_operators.append(SASOperator(op.name, new_prevail, new_effects, op.cost))
        # remove var from condition and effect of axioms
        new_axioms = []
        for ax in sas_task.axioms:
            if ax.effect[0] == var:
                continue
            if ax.effect[0] > var:
                variable_index, value = ax.effect
                variable_index = variable_index - 1  # decrement variable indices above var
                ax.effect = (variable_index, value)
            new_condition = []
            for cond in ax.condition:
                if cond[0] == var:
                    continue
                if cond[0] > var:
                    variable_index, value = cond
                    variable_index = variable_index - 1  # decrement variable indices above var
                    cond = (variable_index, value)
                new_condition.append(cond)
            # axiom condition may also be empty
            new_axioms.append(SASAxiom(new_condition, ax.effect))

        return SASTask(new_variables, new_mutexes, new_init, new_goal, new_operators, new_axioms, sas_task.metric)
