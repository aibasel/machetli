import io
from contextlib import redirect_stdout

from machetli.pddl.downward.pddl import Task, TypedObject, Predicate, Action, \
    Axiom, Function, Truth, Conjunction, Disjunction, Falsity, \
    UniversalCondition, ExistentialCondition, Atom, NegatedAtom, Effect, Assign
from machetli.pddl.downward.pddl.conditions import ConstantCondition


class TaskElementVisitor:
    """Interface for visitor classes to visit PDDL task elements."""

    def visit_task(self, task) -> Task:
        raise NotImplementedError

    def visit_object(self, obj) -> TypedObject:
        raise NotImplementedError

    def visit_predicate(self, predicate) -> Predicate:
        raise NotImplementedError

    def visit_function(self, function) -> Function:
        raise NotImplementedError

    def visit_condition(self, condition):
        if isinstance(condition, Falsity):
            return self.visit_condition_falsity(condition)
        elif isinstance(condition, Truth):
            return self.visit_condition_truth(condition)
        elif isinstance(condition, Conjunction):
            return self.visit_condition_conjunction(condition)
        elif isinstance(condition, Disjunction):
            return self.visit_condition_disjunction(condition)
        elif isinstance(condition, UniversalCondition):
            return self.visit_condition_universal(condition)
        elif isinstance(condition, ExistentialCondition):
            return self.visit_condition_existential(condition)
        elif isinstance(condition, Atom):
            return self.visit_condition_atom(condition)
        elif isinstance(condition, NegatedAtom):
            return self.visit_condition_negated_atom(condition)
        else:
            raise NotImplementedError(
                "No visiting function implemented for this type of condition.")

    def visit_condition_falsity(self, falsity) -> Falsity:
        raise NotImplementedError

    def visit_condition_truth(self, truth) -> Truth:
        raise NotImplementedError

    def visit_condition_conjunction(self, conjunction) -> Conjunction:
        raise NotImplementedError

    def visit_condition_disjunction(self, disjunction) -> Disjunction:
        raise NotImplementedError

    def visit_condition_universal(self, universal_condition) -> UniversalCondition:
        raise NotImplementedError

    def visit_condition_existential(self, existential_condition) -> ExistentialCondition:
        raise NotImplementedError

    def visit_condition_atom(self, atom) -> Atom:
        raise NotImplementedError

    def visit_condition_negated_atom(self, negated_atom) -> NegatedAtom:
        raise NotImplementedError

    def visit_action(self, action) -> Action:
        raise NotImplementedError

    def visit_action_effect(self, effect) -> Effect:
        raise NotImplementedError

    def visit_axiom(self, axiom) -> Axiom:
        raise NotImplementedError


def contains(dumpable_object, item_name) -> bool:
    """Returns true if item_name is present in dump string of dumpable_object."""
    str_io = io.StringIO()
    with redirect_stdout(str_io):
        dumpable_object.dump()
    return item_name in str_io.getvalue()


class TaskElementErasePredicateVisitor(TaskElementVisitor):
    """Partial implementation of TaskElementVisitor interface for predicate deletion."""

    def __init__(self, predicate_name):
        self.predicate_name = predicate_name

    def visit_task(self, task):
        new_predicates = [
            predicate for predicate in task.predicates if predicate.name != self.predicate_name]

        new_init = [atom for atom in task.init if isinstance(atom, Assign)
                    or atom.predicate != self.predicate_name]

        new_goal = task.goal.accept(self)

        new_actions = []
        for action in task.actions:
            new_actions.append(action.accept(self))
        new_actions = [action for action in new_actions if
                       action.effects and not isinstance(action.precondition, Falsity)]

        new_axioms = []
        for axiom in task.axioms:
            new_axioms.append(axiom.accept(self))

        # axioms whose (head became empty OR condition became falsity) were returned as None and must be filtered out
        new_axioms = [axiom for axiom in new_axioms if axiom is not None]
        is_dummy_trigger_added = False
        trigger_id = "dummy_axiom_trigger"
        for ax in new_axioms:
            if isinstance(ax.condition, Truth):  # dummy axiom trigger needs to be created
                if not is_dummy_trigger_added:
                    dummy_axiom_trigger = Predicate(trigger_id, [])
                    new_predicates.append(dummy_axiom_trigger)
                    new_init.append(Atom(trigger_id, []))
                    is_dummy_trigger_added = True
                ax.condition = Atom(trigger_id, [])

        return Task(task.domain_name, task.task_name, task.requirements, task.types, task.objects, new_predicates,
                    task.functions, new_init, new_goal, new_actions, new_axioms, task.use_min_cost_metric)

    def visit_condition_falsity(self, falsity):
        return Falsity()

    def visit_condition_truth(self, truth):
        return Truth()

    def visit_condition_conjunction(self, conjunction):
        new_parts = []
        for part in conjunction.parts:
            new_parts.append(self.visit_condition(part))
        return Conjunction(new_parts).simplified()

    def visit_condition_disjunction(self, disjunction):
        new_parts = []
        for part in disjunction.parts:
            new_parts.append(self.visit_condition(part))
        return Disjunction(new_parts).simplified()

    def visit_condition_universal(self, universal_condition):
        new_parts = []
        for part in universal_condition.parts:
            new_parts.append(self.visit_condition(part))
        return UniversalCondition(universal_condition.parameters, new_parts).simplified()

    def visit_condition_existential(self, existential_condition):
        new_parts = []
        for part in existential_condition.parts:
            new_parts.append(self.visit_condition(part))
        return ExistentialCondition(existential_condition.parameters, new_parts).simplified()

    def visit_action(self, action):
        new_precondition = action.precondition.accept(self)

        # maybe parameters will have to be updated after predicate is deleted
        new_parameters = action.parameters
        new_num_external_parameters = action.num_external_parameters
        new_effects = []
        for effect in action.effects:
            new_effects.append(effect.accept(self))
        new_effects = [eff for eff in new_effects if
                       eff is not None and not isinstance(eff.literal, ConstantCondition) and not isinstance(
                           eff.condition, Falsity)]

        # name stays the same
        # cost stays the same
        return Action(action.name, new_parameters, new_num_external_parameters, new_precondition, new_effects,
                      action.cost)

    def visit_action_effect(self, effect):
        new_condition = effect.condition.accept(self)
        # parameters stay the same
        new_literal = effect.literal.accept(self)
        return Effect(effect.parameters, new_condition, new_literal)

    def visit_axiom(self, axiom):
        if axiom.name == self.predicate_name:  # axiom head is about to be deleted
            return None
        new_condition = axiom.condition.accept(self)
        if isinstance(new_condition, Falsity):  # axiom will never fire
            return None
        #  truth conditions are handled in visit_task
        return Axiom(axiom.name, axiom.parameters, axiom.num_external_parameters, new_condition)


class TaskElementErasePredicateTrueAtomVisitor(TaskElementErasePredicateVisitor):
    """Deletes predicates from PDDL tasks by replacing the affected atom with the truth value."""

    def visit_condition_atom(self, atom):
        if atom.predicate == self.predicate_name:
            return Truth()
        else:
            return atom

    def visit_condition_negated_atom(self, negated_atom):
        if negated_atom.predicate == self.predicate_name:
            return Falsity()
        else:
            return negated_atom


class TaskElementErasePredicateFalseAtomVisitor(TaskElementErasePredicateVisitor):
    """Deletes predicates from PDDL tasks by replacing the affected atom with the falsity value."""

    def visit_condition_atom(self, atom):
        if atom.predicate == self.predicate_name:
            return Falsity()
        else:
            return atom

    def visit_condition_negated_atom(self, negated_atom):
        if negated_atom.predicate == self.predicate_name:
            return Truth()
        else:
            return negated_atom


class TaskElementErasePredicateTrueLiteralVisitor(TaskElementErasePredicateVisitor):
    """Deletes predicates from PDDL tasks by replacing the affected literal with the truth value."""

    def visit_condition_atom(self, atom):
        if atom.predicate == self.predicate_name:
            return Truth()
        else:
            return atom

    def visit_condition_negated_atom(self, negated_atom):
        if negated_atom.predicate == self.predicate_name:
            return Truth()
        else:
            return negated_atom


class TaskElementEraseActionVisitor(TaskElementVisitor):
    """Deletes actions from PDDL tasks."""

    def __init__(self, action_name):
        self.action_name = action_name

    def visit_task(self, task):
        # filter out actions with name == self.action_name
        new_actions = [action for action in task.actions if not (
            action.name == self.action_name)]

        return Task(task.domain_name, task.task_name, task.requirements, task.types, task.objects, task.predicates,
                    task.functions, task.init, task.goal, new_actions, task.axioms, task.use_min_cost_metric)


class TaskElementEraseObjectVisitor(TaskElementVisitor):
    """Deletes objects from PDDL tasks."""

    def __init__(self, object_name):
        self.object_name = object_name

    def visit_task(self, task):
        new_objects = [
            obj for obj in task.objects if obj.name != self.object_name]
        new_init = [literal for literal in task.init if not contains(
            literal, self.object_name)]
        new_actions = [action for action in task.actions if not contains(
            action, self.object_name)]
        new_goal = task.goal.accept(self)

        return Task(task.domain_name, task.task_name, task.requirements, task.types, new_objects, task.predicates,
                    task.functions, new_init, new_goal, new_actions, task.axioms, task.use_min_cost_metric)

    def visit_condition_falsity(self, falsity) -> Falsity:
        return Falsity()

    def visit_condition_truth(self, truth) -> Truth:
        return Truth()

    def visit_condition_conjunction(self, conjunction) -> Conjunction:
        new_parts = []
        for part in conjunction.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return Conjunction(new_parts).simplified()

    def visit_condition_disjunction(self, disjunction) -> Disjunction:
        new_parts = []
        for part in disjunction.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return Disjunction(new_parts).simplified()

    def visit_condition_universal(self, universal_condition) -> UniversalCondition:
        new_parts = []
        for part in universal_condition.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return UniversalCondition(universal_condition.parameters, new_parts).simplified()

    def visit_condition_existential(self, existential_condition) -> ExistentialCondition:
        new_parts = []
        for part in existential_condition.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return ExistentialCondition(existential_condition.parameters, new_parts).simplified()

    def visit_condition_atom(self, atom) -> Atom:
        return Truth() if contains(atom, self.object_name) else atom

    def visit_condition_negated_atom(self, negated_atom) -> NegatedAtom:
        return Falsity() if contains(negated_atom, self.object_name) else negated_atom


class TaskElementEraseInitFactVisitor(TaskElementVisitor):
    """Partial implementation of TaskElementVisitor interface for deletion of fact from init."""

    def __init__(self, fact):
        self.the_fact = fact

    def visit_task(self, task):
        new_init = [atom for atom in task.init if isinstance(atom, Assign) or atom != self.the_fact]

        return Task(task.domain_name, task.task_name, task.requirements, task.types, task.objects, task.predicates,
                    task.functions, new_init, task.goal, task.actions, task.axioms, task.use_min_cost_metric)


class TaskElementEraseGoalLiteralVisitor(TaskElementVisitor):
    """Partial implementation of TaskElementVisitor interface for deleting a literal from the goal."""

    def __init__(self, literal):
        self.the_literal = literal

    def visit_task(self, task):
        new_goal = task.goal.accept(self)

        return Task(task.domain_name, task.task_name, task.requirements, task.types, task.objects, task.predicates,
                    task.functions, task.init, new_goal, task.actions, task.axioms, task.use_min_cost_metric)

    def visit_condition_falsity(self, falsity) -> Falsity:
        return Falsity()

    def visit_condition_truth(self, truth) -> Truth:
        return Truth()

    def visit_condition_conjunction(self, conjunction) -> Conjunction:
        new_parts = []
        for part in conjunction.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return Conjunction(new_parts).simplified()

    def visit_condition_disjunction(self, disjunction) -> Disjunction:
        new_parts = []
        for part in disjunction.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return Disjunction(new_parts).simplified()

    def visit_condition_universal(self, universal_condition) -> UniversalCondition:
        new_parts = []
        for part in universal_condition.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return UniversalCondition(universal_condition.parameters, new_parts).simplified()

    def visit_condition_existential(self, existential_condition) -> ExistentialCondition:
        new_parts = []
        for part in existential_condition.parts:
            new_parts.append(part.accept(self))
        new_parts = [part for part in new_parts if part is not None]
        return ExistentialCondition(existential_condition.parameters, new_parts).simplified()

    def visit_condition_atom(self, atom) -> Atom:
        return Truth() if atom == self.the_literal else atom

    def visit_condition_negated_atom(self, negated_atom) -> NegatedAtom:
        return Truth() if atom == self.the_literal else negated_atom 


class GetLiteralsVisitor:
    """A visitor that returns the literals contains in a formula"""

    def visit_condition(self, condition) -> list[Literal]:
        if isinstance(condition, Falsity):
            return self.visit_condition_falsity(condition)
        elif isinstance(condition, Truth):
            return self.visit_condition_truth(condition)
        elif isinstance(condition, Conjunction):
            return self.visit_condition_conjunction(condition)
        elif isinstance(condition, Disjunction):
            return self.visit_condition_disjunction(condition)
        elif isinstance(condition, UniversalCondition):
            return self.visit_condition_universal(condition)
        elif isinstance(condition, ExistentialCondition):
            return self.visit_condition_existential(condition)
        elif isinstance(condition, Atom):
            return self.visit_condition_atom(condition)
        elif isinstance(condition, NegatedAtom):
            return self.visit_condition_negated_atom(condition)
        else:
            raise NotImplementedError(
                "No visiting function implemented for this type of condition.")

    def visit_condition_falsity(self, falsity) -> list[Literal]:
        return []

    def visit_condition_truth(self, truth) -> list[Literal]:
        return []

    def visit_condition_conjunction(self, conjunction) -> list[Literal]:
        literals = []
        for part in conjunction.parts:
            literals.extend(self.visit_condition(part))
        return literals

    def visit_condition_disjunction(self, disjunction) -> list[Literal]:
        literals = []
        for part in disjunction.parts:
            literals.extend(self.visit_condition(part))
        return literals

    def visit_condition_universal(self, universal_condition) -> list[Literal]:
        literals = []
        for part in universal_condition.parts:
            literals.extend(self.visit_condition(part))
        return literals

    def visit_condition_existential(self, existential_condition) -> list[Literal]:
        literals = []
        for part in existential_condition.parts:
            literals.extend(self.visit_condition(part))
        return literals

    def visit_condition_atom(self, atom) -> list[Literal]:
        return [atom]

    def visit_condition_negated_atom(self, negated_atom) -> list[Literal]:
        raise [negated_atom]




