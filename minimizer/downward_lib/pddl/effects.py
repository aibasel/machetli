from . import conditions
from . import TaskElement


def closing_brackets(num):
    brackets = ""
    for i in range(num):
        brackets += ")"
    return brackets


def cartesian_product(*sequences):
    # TODO: Also exists in tools.py outside the pddl package (defined slightly
    #       differently). Not good. Need proper import paths.
    if not sequences:
        yield ()
    else:
        for tup in cartesian_product(*sequences[1:]):
            for item in sequences[0]:
                yield (item,) + tup


class Effect(TaskElement):
    def accept(self, visitor):
        return visitor.visit_action_effect(self)

        # self.condition = self.condition.accept(visitor)
        # for index, param in enumerate(self.parameters):
        #     self.parameters[index] = param.accept(visitor)
        # self.parameters = [param for param in self.parameters if param is not None]
        # if self.condition is not None:
        #     self.parameters = update_parameters(self.parameters, self.condition.parts)
        # self.literal = self.literal.accept(visitor)
        # return self

    def __init__(self, parameters, condition, literal):
        self.parameters = parameters
        self.condition = condition
        self.literal = literal

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.parameters == other.parameters and
                self.condition == other.condition and
                self.literal == other.literal)

    def dump(self):
        indent = "  "
        if self.parameters:
            print("%sforall %s" % (indent, ", ".join(map(str, self.parameters))))
            indent += "  "
        if self.condition != conditions.Truth():
            print("%sif" % indent)
            self.condition.dump(indent + "  ")
            print("%sthen" % indent)
            indent += "  "
        print("%s%s" % (indent, self.literal))

    def dump_pddl(self, output, indent="  "):
        num_closing_brackets = 0
        if self.parameters:
            output.write("%s(forall (" % indent)
            for par in self.parameters:
                output.write("%s - %s " % (par.name, par.type_name))
            output.write(")\n")
            num_closing_brackets += 1
        if self.condition != conditions.Truth():
            output.write("%s(when\n" % indent)
            num_closing_brackets += 1
            self.condition.dump_pddl(output, indent + indent)

        self.literal.dump_pddl(output, indent + "  ")
        if num_closing_brackets:
            output.write("%s%s\n" % (indent, closing_brackets(num_closing_brackets)))

    def copy(self):
        return Effect(self.parameters, self.condition, self.literal)

    def uniquify_variables(self, type_map):
        renamings = {}
        self.parameters = [par.uniquify_name(type_map, renamings)
                           for par in self.parameters]
        self.condition = self.condition.uniquify_variables(type_map, renamings)
        self.literal = self.literal.rename_variables(renamings)

    def instantiate(self, var_mapping, init_facts, fluent_facts,
                    objects_by_type, result):
        if self.parameters:
            var_mapping = var_mapping.copy()  # Will modify this.
            object_lists = [objects_by_type.get(par.type_name, [])
                            for par in self.parameters]
            for object_tuple in cartesian_product(*object_lists):
                for (par, obj) in zip(self.parameters, object_tuple):
                    var_mapping[par.name] = obj
                self._instantiate(var_mapping, init_facts, fluent_facts, result)
        else:
            self._instantiate(var_mapping, init_facts, fluent_facts, result)

    def _instantiate(self, var_mapping, init_facts, fluent_facts, result):
        condition = []
        try:
            self.condition.instantiate(var_mapping, init_facts, fluent_facts, condition)
        except conditions.Impossible:
            return
        effects = []
        self.literal.instantiate(var_mapping, init_facts, fluent_facts, effects)
        assert len(effects) <= 1
        if effects:
            result.append((condition, effects[0]))

    def relaxed(self):
        if self.literal.negated:
            return None
        else:
            return Effect(self.parameters, self.condition.relaxed(), self.literal)

    def simplified(self):
        return Effect(self.parameters, self.condition.simplified(), self.literal)


class ConditionalEffect:
    def __init__(self, condition, effect):
        if isinstance(effect, ConditionalEffect):
            self.condition = conditions.Conjunction([condition, effect.condition])
            self.effect = effect.effect
        else:
            self.condition = condition
            self.effect = effect

    def dump(self, indent="  "):
        print("%sif" % (indent))
        self.condition.dump(indent + "  ")
        print("%sthen" % (indent))
        self.effect.dump(indent + "  ")

    # def dump_pddl(self, output, indent="  "):
    #     output.write("{}({} ( ".format(indent, self._pddl()))
    #     self.condition.dump_pddl()
    #     self.effect.dump_pddl()
    #     output.write(")\n")

    def _pddl(self):
        return "when"

    def normalize(self):
        norm_effect = self.effect.normalize()
        if isinstance(norm_effect, ConjunctiveEffect):
            new_effects = []
            for effect in norm_effect.effects:
                assert isinstance(effect, SimpleEffect) or isinstance(effect, ConditionalEffect)
                new_effects.append(ConditionalEffect(self.condition, effect))
            return ConjunctiveEffect(new_effects)
        elif isinstance(norm_effect, UniversalEffect):
            child = norm_effect.effect
            cond_effect = ConditionalEffect(self.condition, child)
            return UniversalEffect(norm_effect.parameters, cond_effect)
        else:
            return ConditionalEffect(self.condition, norm_effect)

    def extract_cost(self):
        return None, self


class UniversalEffect:
    def __init__(self, parameters, effect):
        if isinstance(effect, UniversalEffect):
            self.parameters = parameters + effect.parameters
            self.effect = effect.effect
        else:
            self.parameters = parameters
            self.effect = effect

    def dump(self, indent="  "):
        print("%sforall %s" % (indent, ", ".join(map(str, self.parameters))))
        self.effect.dump(indent + "  ")

    # def dump_pddl(self, output, indent="  "):
    #     output.write("%s(forall (" % indent)
    #     for par in self.parameters:
    #         par.dump_pddl(output, "")
    #     output.write(")\n%s)\n" % indent)

    def normalize(self):
        norm_effect = self.effect.normalize()
        if isinstance(norm_effect, ConjunctiveEffect):
            new_effects = []
            for effect in norm_effect.effects:
                assert isinstance(effect, SimpleEffect) or isinstance(effect, ConditionalEffect) \
                       or isinstance(effect, UniversalEffect)
                new_effects.append(UniversalEffect(self.parameters, effect))
            return ConjunctiveEffect(new_effects)
        else:
            return UniversalEffect(self.parameters, norm_effect)

    def extract_cost(self):
        return None, self


class ConjunctiveEffect:
    def __init__(self, effects):
        flattened_effects = []
        for effect in effects:
            if isinstance(effect, ConjunctiveEffect):
                flattened_effects += effect.effects
            else:
                flattened_effects.append(effect)
        self.effects = flattened_effects

    def dump(self, indent="  "):
        print("%sand" % (indent))
        for eff in self.effects:
            eff.dump(indent + "  ")

    # def dump_pddl(self, output, indent="  "):
    #     output.write("%s(and\n" % indent)
    #     for eff in self.effects:
    #         eff.dump_pddl(output, indent + indent)
    #     output.write("%s)\n" % indent)

    def normalize(self):
        new_effects = []
        for effect in self.effects:
            new_effects.append(effect.normalize())
        return ConjunctiveEffect(new_effects)

    def extract_cost(self):
        new_effects = []
        cost_effect = None
        for effect in self.effects:
            if isinstance(effect, CostEffect):
                cost_effect = effect
            else:
                new_effects.append(effect)
        return cost_effect, ConjunctiveEffect(new_effects)


class SimpleEffect:
    def __init__(self, effect):
        self.effect = effect

    def dump(self, indent="  "):
        print("%s%s" % (indent, self.effect))

    def normalize(self):
        return self

    def extract_cost(self):
        return None, self


class CostEffect:
    def __init__(self, effect):
        self.effect = effect

    def dump(self, indent="  "):
        print("%s%s" % (indent, self.effect))

    def normalize(self):
        return self

    def extract_cost(self):
        # This only happens if an action has no effect apart from the cost effect.
        return self, None
