from minimizer.downward_lib import timers


def first_choice_hill_climbing(initial_state, successor_generators, evaluator):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    current_state = initial_state
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
