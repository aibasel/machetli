import copy
import itertools
import random

from machetli.sas.constants import KEY_IN_STATE
from machetli.sas.sas_tasks import SASTask, SASMutexGroup, SASInit, SASGoal, \
    SASOperator, SASAxiom
from machetli.successors import Successor, SuccessorGenerator, RNG


class RemoveOperators(SuccessorGenerator):
    """
    For each operator, generate a successor where this operator is
    removed. The order of the successors is randomized.
    """
    def get_description(self):
        return "Tries to remove individual operators."

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        operator_names = [op.name for op in task.operators]
        RNG.shuffle(operator_names)
        for name in operator_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = self.transform(pre_child_task, name)
            yield Successor(child_state,
                            f"Removed operator '{name}'. Remaining operators: {len(operator_names) - 1}")

    def transform(self, task, op_name):
        new_operators = [op for op in task.operators if not op.name == op_name]

        return SASTask(task.variables, task.mutexes, task.init, task.goal,
                       new_operators, task.axioms, task.metric)


class RemoveVariables(SuccessorGenerator):
    """
    For each variable, generate a successor where this variable is
    compiled away by removing it from the initial state as well as every
    place where it is mentioned in the prevail condition, effect
    condition, effect fact, or goal. The order of the successors is
    randomized.
    """
    def get_description(self):
        return "Tries to project away individual variables."

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        variables = [var for var in range(len(task.variables.axiom_layers))]
        RNG.shuffle(variables)
        for var in variables:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = self.transform(pre_child_task, var)
            yield Successor(child_state,
                            f"Removed a variable. Remaining variables: {len(variables) - 1}")

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


class RemovePrePosts(SuccessorGenerator):
    """
    For each precondition/effect pair in each operator, generate a successor
    where this pair is removed. This essentially ignores the variable in the
    operator. The order in which operators are considered is randomized, as is
    the order of precondition/effect pairs of the same operator, but all
    successors stemming from the same operator follow consecutively.
    """
    def get_description(self):
        return ("Tries to remove individual precondition/effect pairs in "
                "operators. This ignores a variable in an operators.")

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        num_ops = len(task.operators)
        for op in RNG.sample(range(num_ops), num_ops):
            num_eff = len(task.operators[op].pre_post)
            for effect in RNG.sample(range(num_eff), num_eff):
                child_state = copy.deepcopy(state)
                del child_state[KEY_IN_STATE].operators[op].pre_post[effect]
                yield Successor(child_state, f"Removed an effect of operator '{task.operators[op].name}'.")


class SetUnspecifiedPreconditions(SuccessorGenerator):
    """
    For each operator and each variable on which this operator 
    has an effect but no precondition, and for each possible value of this
    variable, generate a successor with an additional precondition on the
    variable. This limits the situations where the operator can be applied,
    potentially limiting branching in the search. The order in which operators
    are considered is randomized, as is the order of effects of the same
    operator, but all successors stemming from the same operator follow
    consecutively.
    """
    def get_description(self):
        return ("Tries to add preconditions to an operator, which have an "
                "effect but no precondition on a variable.")

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        num_ops = len(task.operators)
        for op in RNG.sample(range(num_ops), num_ops):
            num_eff = len(task.operators[op].pre_post)
            for effect in RNG.sample(range(num_eff), num_eff):
                var, pre, post, cond = task.operators[op].pre_post[effect]
                if pre == -1:
                    num_val = task.variables.ranges[var]
                    for val in RNG.sample(range(num_val), num_val):
                        child_state = copy.deepcopy(state)
                        child_state[KEY_IN_STATE].operators[op].pre_post[
                            effect] = (var, val, post, cond)
                        yield Successor(
                            child_state,
                            f"Removed a prevail condition of operator '{task.operators[op].name}'.")


class MergeOperators(SuccessorGenerator):
    """
    For each pair of operators, generate a successor where these two
    operators are merged into one. Specifically, these operators
    are removed and instead a new operator is added that is equivalent to
    executing the two operators in sequence. Cases where this is not
    possible (e.g., with conflicting prevail conditions) are skipped.
    """
    def get_description(self):
        return ("Tries to replace a pair of operators with a single operator "
                "equivalent to applying both in sequence.")

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        for op1, op2 in itertools.permutations(task.operators, 2):
            child_state = copy.deepcopy(state)
            child_task = self.transform(child_state[KEY_IN_STATE], op1, op2)
            if child_task:
                child_state[KEY_IN_STATE] = child_task
                yield Successor(child_state,
                                f"Merged operators '{op1.name}' and '{op2.name}'. " +
                                f"Remaining operators: {len(task.operators) - 1}")

    def transform(self, task, op1, op2):
        def combined_pre_post(op):
            combined_pre, combined_post = {}, {}
            for var, value in op.prevail:
                combined_pre[var] = value
                combined_post[var] = value
            for var, pre, post, cond in op.pre_post:
                if cond:
                    raise NotImplementedError("Conditional effects not yet supported.")
                if pre != -1:
                    combined_pre[var] = pre
                combined_post[var] = post
            return combined_pre, combined_post

        pre1, post1 = combined_pre_post(op1)
        pre2, post2 = combined_pre_post(op2)

        # Check that op2 is applicable and update preconditions
        merged_pre = pre1
        for var, pre in pre2.items():
            if var not in post1:
                merged_pre[var] = pre
            elif post1[var] != pre:
                # Operators not compatible
                return None

        # update effects
        merged_post = post1
        merged_post.update(post2)

        merged_prevail = []
        merged_pre_post = []
        for var, post in merged_post.items():
            pre = merged_pre.get(var, -1)
            if pre == post:
                merged_prevail.append((var, pre))
            else:
                merged_pre_post.append((var, pre, post, []))

        merged_name = op1.name + " and then " + op2.name
        merged_cost = op1.cost + op2.cost
        merged_op = SASOperator(merged_name, merged_prevail, merged_pre_post, merged_cost)

        new_operators = [op for op in task.operators if op.name not in [op1.name, op2.name]] + [merged_op]

        return SASTask(task.variables, task.mutexes, task.init, task.goal, new_operators,
                       task.axioms, task.metric)


class RemoveGoals(SuccessorGenerator):
    """
    For each goal condition, generate a successor where this goal condition
    is removed. The order of the successors is randomized
    """
    def get_description(self):
        return "Tries to remove goal conditions."

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        num_goals = len(task.goal.pairs)
        for goal_id in RNG.sample(range(num_goals), num_goals):
            child_state = copy.deepcopy(state)
            del child_state[KEY_IN_STATE].goal.pairs[goal_id]
            yield Successor(child_state, f"Removed a goal. Remaining goals: {num_goals - 1}")