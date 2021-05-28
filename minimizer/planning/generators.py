import copy
import random

from minimizer.planning import pddl_visitors
from minimizer.planning.downward_lib import timers
from minimizer.planning.downward_lib.sas_tasks import SASTask, SASMutexGroup, SASInit, SASGoal, SASOperator, SASAxiom


class SuccessorGenerator():
    def get_successors(self, state):
        pass


class RemoveActions(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        action_names = [action.name for action in task.actions]
        random.Random().shuffle(action_names)
        for name in action_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    pddl_visitors.TaskElementEraseActionVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceAtomsWithTruth(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    pddl_visitors.TaskElementErasePredicateTrueAtomVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceAtomsWithFalsity(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    pddl_visitors.TaskElementErasePredicateFalseAtomVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceLiteralsWithTruth(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    pddl_visitors.TaskElementErasePredicateTrueLiteralVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class RemoveObjects(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        object_names = [obj.name for obj in task.objects]
        random.Random().shuffle(object_names)
        for name in object_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    pddl_visitors.TaskElementEraseObjectVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class RemoveSASOperators(SuccessorGenerator):
    def get_successors(self, state):
        task = state["sas_task"]
        operator_names = [op.name for op in task.operators]
        random.Random().shuffle(operator_names)
        for name in operator_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["sas_task"]
            with timers.timing("Obtaining successor"):
                child_task = self.transform(pre_child_task, name)
            child_state["sas_task"] = child_task
            yield child_state

    def transform(self, task, op_name):
        new_operators = [op for op in task.operators if not op.name == op_name]

        return SASTask(task.variables, task.mutexes, task.init, task.goal, new_operators,
                       task.axioms, task.metric)


class RemoveSASVariables(SuccessorGenerator):
    def get_successors(self, state):
        task = state["sas_task"]
        variables = [var for var in range(len(task.variables.axiom_layers))]
        random.Random().shuffle(variables)
        for var in variables:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["sas_task"]
            with timers.timing("Obtaining successor"):
                child_task = self.transform(pre_child_task, var)
            child_state["sas_task"] = child_task
            yield child_state
    
    def transform(self, task, var):
        # remove var attributes from variables object
        new_variables = task.variables
        del new_variables.axiom_layers[var]
        del new_variables.ranges[var]
        del new_variables.value_names[var]
        # remove var from from mutex groups
        new_mutexes = []
        for group in task.mutexes:
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
        new_init = SASInit(task.init.values)
        del new_init.values[var]
        # remove var from goal pairs and decrement higher indices than var
        new_goal_pairs = []
        for pair in task.goal.pairs:
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
        for op in task.operators:
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
        for ax in task.axioms:
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

        return SASTask(new_variables, new_mutexes, new_init, new_goal, new_operators, new_axioms, task.metric)
        