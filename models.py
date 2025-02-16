class Player:
    """Player model for storing golf player data in memory."""
    players = []  # Class variable to store all players
    next_id = 1   # Class variable for ID generation

    def __init__(self, name: str, handicap: float = 0):
        """Initialize a new player.
        
        Args:
            name: Player's name
            handicap: Player's handicap (default: 0)
        """
        self.id = Player.next_id
        Player.next_id += 1
        self.name = name
        self.handicap = handicap
        Player.players.append(self)

    @classmethod
    def get_all(cls):
        """Return all players."""
        return cls.players

    @classmethod
    def get_by_id(cls, player_id):
        """Find player by ID.
        
        Args:
            player_id: The ID of the player to find
            
        Returns:
            Player object if found, None otherwise
        """
        return next((p for p in cls.players if p.id == player_id), None)

    def delete(self):
        """Remove player from storage."""
        if self in Player.players:
            Player.players.remove(self)
