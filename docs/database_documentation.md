# Database Documentation

## Overview
The application uses SQLite with SQLAlchemy ORM.

## Models

### Player
Represents a golf player in the system.

**Fields:**
- id: Primary key
- name: Player's name (unique)
- handicap: Current handicap
- scores: Relationship to scores

**Relationships:**
- One-to-many with Score model

### Score
Represents a single golf score entry.

**Fields:**
- id: Primary key
- value: Score value
- date: UTC timestamp
- player_id: Foreign key to Player

**Relationships:**
- Many-to-one with Player model