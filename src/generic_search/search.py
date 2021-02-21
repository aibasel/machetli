def first_choice_hill_climbing(initial_state, successor_generators, evaluator):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    
        