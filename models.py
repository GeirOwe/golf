from datetime import datetime
from data_store import load_players, save_players, load_scores, save_scores

class Player:
    def __init__(self, name, handicap=0, player_id=None):
        self.id = player_id or self._next_id()
        self.name = name
        self.handicap = handicap
        self.scores = []

    @staticmethod
    def _next_id():
        players = load_players()
        return max([p.get('id', 0) for p in players], default=0) + 1

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'handicap': self.handicap
        }

    @classmethod
    def get_all(cls):
        return [cls(p['name'], p['handicap'], p['id']) for p in load_players()]

    @classmethod
    def get_by_id(cls, player_id):
        for p in load_players():
            if p['id'] == player_id:
                return cls(p['name'], p['handicap'], p['id'])
        return None

    def save(self):
        players = load_players()
        player_dict = self.to_dict()
        
        # Update existing or add new
        for i, p in enumerate(players):
            if p['id'] == self.id:
                players[i] = player_dict
                break
        else:
            players.append(player_dict)
        
        save_players(players)

    def delete(self):
        players = load_players()
        players = [p for p in players if p['id'] != self.id]
        save_players(players)

class Score:
    def __init__(self, value, player_id, score_id=None, date=None):
        self.id = score_id or self._next_id()
        self.value = value
        self.player_id = player_id
        self.date = date or datetime.now().isoformat()
        self._player = None  # Cache for player object

    @property
    def player(self):
        """Get the player associated with this score."""
        if self._player is None:
            self._player = Player.get_by_id(self.player_id)
        return self._player

    @staticmethod
    def _next_id():
        scores = load_scores()
        return max([s.get('id', 0) for s in scores], default=0) + 1

    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value,
            'player_id': self.player_id,
            'date': self.date
        }

    def formatted_date(self):
        dt = datetime.fromisoformat(self.date)
        return dt.strftime('%d.%m.%y')

    @classmethod
    def get_all(cls):
        return [cls(s['value'], s['player_id'], s['id'], s['date']) 
                for s in load_scores()]

    @classmethod
    def get_by_id(cls, score_id):
        for s in load_scores():
            if s['id'] == score_id:
                return cls(s['value'], s['player_id'], s['id'], s['date'])
        return None

    def save(self):
        scores = load_scores()
        score_dict = self.to_dict()
        
        # Update existing or add new
        for i, s in enumerate(scores):
            if s['id'] == self.id:
                scores[i] = score_dict
                break
        else:
            scores.append(score_dict)
        
        save_scores(scores)

    def delete(self):
        scores = load_scores()
        scores = [s for s in scores if s['id'] != self.id]
        save_scores(scores)
