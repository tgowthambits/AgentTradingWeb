import random
import numpy as np


class GAPatternOptimizer:

    def __init__(self, population_size=20, generations=30, max_length=5):
        self.population_size = population_size
        self.generations = generations
        self.max_length = max_length
    
    def random_pattern(self):
        L = random.randint(1, self.max_length)
        return [random.choice([0,1]) for _ in range(L)]

    def initialize_population(self):
        return [self.random_pattern() for _ in range(self.population_size)]

    def fitness(self, pattern, evaluator):
        """Evaluator must return directional accuracy."""
        return evaluator(pattern)

    def evolve(self, evaluator):
        pop = self.initialize_population()

        for gen in range(self.generations):
            scored = [(self.fitness(p, evaluator), p) for p in pop]
            scored.sort(reverse=True)

            survivors = [p for _, p in scored[:self.population_size//2]]

            new_pop = survivors[:]
            while len(new_pop) < self.population_size:
                p1, p2 = random.sample(survivors, 2)
                cut = random.randint(1, min(len(p1), len(p2))-1)
                child = p1[:cut] + p2[cut:]
                if random.random() < 0.2:  # mutation
                    idx = random.randint(0, len(child)-1)
                    child[idx] = 1 - child[idx]
                new_pop.append(child)

            pop = new_pop

        best = max(pop, key=lambda p: evaluator(p))
        return best
