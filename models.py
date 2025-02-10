class Player:
    def __init__(self, name, handicap=0):
        self.name = name
        self.handicap = handicap
        self.scores = []

    def add_score(self, score):
        self.scores.append(score)

    def get_total_score(self):
        return sum(self.scores) if self.scores else 0

    def get_average_score(self):
        return sum(self.scores) / len(self.scores) if self.scores else 0