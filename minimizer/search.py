import random

from minimizer.planning.downward_lib import timers

# TODO: do we want results to be deterministic? Otherwise remove the
#  random seed.
random.seed(1234)


def get_successors(state, successor_generator, enforce_order):
    # TODO: should *enforce_order* rather be a property of the
    #  *successor_generator*?
    successors = list(successor_generator.get_successors(state))
    if not enforce_order:
        random.shuffle(successors)
    return successors


def new_search(initial_state, successor_generator, evaluator, environment):
    current_state = initial_state
    batch_size = environment.batch_size
    batch_num = 0
    enforce_order = environment.enforce_order

    successors = get_successors(
        current_state, successor_generator, environment.enforce_order)

    while len(successors) > 0:
        batch = successors[:batch_size]
        del successors[:batch_size]

        # TODO: we could also split this into *submit*, *poll*, and
        #  *evaluate*. The *batch_size* of *LocalEnvironment* should
        #  then rather be *1* than *None*, but *pull* doesn't make too
        #  much sense in that case.
        best_successor = environment.get_improving_successor(
            evaluator, batch, batch_num)

        if best_successor:
            current_state = best_successor
            successors = get_successors(
                current_state, successor_generator, enforce_order)
        batch_num += 1
    return current_state


def first_choice_hill_climbing(initial_state, successor_generators, evaluator):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    current_state = initial_state
    last_state = None
    print()
    with timers.timing("Starting first-choice hill-climbing search"):
        for succ_gen in successor_generators:
            print()
            with timers.timing("Generating successors with class {}".format(
                    succ_gen.__name__)):
                num_children = 0
                num_successors = 0
                print()
                while True:
                    if num_children > 0:
                        print(
                            "Child found ({}), evaluated {} successor{}.\n"
                            .format(num_children, num_successors, "s" if num_successors > 1 else ""))
                    num_successors = 0
                    num_children += 1
                    last_state = current_state
                    for successor_state in succ_gen().get_successors(current_state):
                        num_successors += 1
                        if evaluator().evaluate(successor_state):
                            current_state = successor_state
                            break
                    else:
                        print(
                            "\nNo successor found by evaluator, end of first-choice hill-climbing."
                        )
                        break
        return last_state
