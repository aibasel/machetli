import random

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


def search(initial_state, successor_generator, evaluator, environment):
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
