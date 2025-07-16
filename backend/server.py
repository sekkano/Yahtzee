from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import random
from collections import Counter

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Yahtzee Models
class Dice(BaseModel):
    values: List[int] = Field(default_factory=lambda: [1, 1, 1, 1, 1])
    held: List[bool] = Field(default_factory=lambda: [False, False, False, False, False])

class ScoreCard(BaseModel):
    # Upper section
    ones: Optional[int] = None
    twos: Optional[int] = None
    threes: Optional[int] = None
    fours: Optional[int] = None
    fives: Optional[int] = None
    sixes: Optional[int] = None
    
    # Lower section
    three_of_a_kind: Optional[int] = None
    four_of_a_kind: Optional[int] = None
    full_house: Optional[int] = None
    small_straight: Optional[int] = None
    large_straight: Optional[int] = None
    yahtzee: Optional[int] = None
    chance: Optional[int] = None
    
    # Calculated fields
    upper_subtotal: int = 0
    upper_bonus: int = 0
    upper_total: int = 0
    lower_total: int = 0
    grand_total: int = 0

class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Player"
    scorecard: ScoreCard = Field(default_factory=ScoreCard)
    is_active: bool = False

class GameState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    players: List[Player] = Field(default_factory=list)
    current_player: int = 0
    dice: Dice = Field(default_factory=Dice)
    rolls_remaining: int = 3
    rolls_used: int = 0  # Track rolls used this turn
    turn_number: int = 1
    game_mode: str = "single"  # "single" or "multiplayer"
    game_over: bool = False
    winner: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class HighScore(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_name: str
    score: int
    game_mode: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GameCreate(BaseModel):
    game_mode: str
    player_names: List[str]

class RollDiceRequest(BaseModel):
    game_id: str
    held_dice: List[bool]

class ScoreRequest(BaseModel):
    game_id: str
    category: str

class HighScoreCreate(BaseModel):
    player_name: str
    score: int
    game_mode: str

# Yahtzee Scoring Logic
class YahtzeeScoring:
    @staticmethod
    def calculate_upper_section(dice_values: List[int], target_number: int) -> int:
        """Calculate score for upper section (ones, twos, threes, etc.)"""
        return dice_values.count(target_number) * target_number
    
    @staticmethod
    def calculate_three_of_a_kind(dice_values: List[int]) -> int:
        """Calculate three of a kind score"""
        counts = Counter(dice_values)
        for count in counts.values():
            if count >= 3:
                return sum(dice_values)
        return 0
    
    @staticmethod
    def calculate_four_of_a_kind(dice_values: List[int]) -> int:
        """Calculate four of a kind score"""
        counts = Counter(dice_values)
        for count in counts.values():
            if count >= 4:
                return sum(dice_values)
        return 0
    
    @staticmethod
    def calculate_full_house(dice_values: List[int]) -> int:
        """Calculate full house score"""
        counts = Counter(dice_values)
        count_values = sorted(counts.values())
        if count_values == [2, 3]:
            return 25
        return 0
    
    @staticmethod
    def calculate_small_straight(dice_values: List[int]) -> int:
        """Calculate small straight score"""
        unique_dice = set(dice_values)
        straights = [
            {1, 2, 3, 4},
            {2, 3, 4, 5},
            {3, 4, 5, 6}
        ]
        for straight in straights:
            if straight.issubset(unique_dice):
                return 30
        return 0
    
    @staticmethod
    def calculate_large_straight(dice_values: List[int]) -> int:
        """Calculate large straight score"""
        unique_dice = set(dice_values)
        if unique_dice == {1, 2, 3, 4, 5} or unique_dice == {2, 3, 4, 5, 6}:
            return 40
        return 0
    
    @staticmethod
    def calculate_yahtzee(dice_values: List[int]) -> int:
        """Calculate yahtzee score"""
        if len(set(dice_values)) == 1:
            return 50
        return 0
    
    @staticmethod
    def calculate_chance(dice_values: List[int]) -> int:
        """Calculate chance score"""
        return sum(dice_values)
    
    @staticmethod
    def get_possible_score(dice_values: List[int], category: str) -> int:
        """Get possible score for a given category"""
        scoring_map = {
            'ones': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 1),
            'twos': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 2),
            'threes': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 3),
            'fours': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 4),
            'fives': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 5),
            'sixes': lambda: YahtzeeScoring.calculate_upper_section(dice_values, 6),
            'three_of_a_kind': lambda: YahtzeeScoring.calculate_three_of_a_kind(dice_values),
            'four_of_a_kind': lambda: YahtzeeScoring.calculate_four_of_a_kind(dice_values),
            'full_house': lambda: YahtzeeScoring.calculate_full_house(dice_values),
            'small_straight': lambda: YahtzeeScoring.calculate_small_straight(dice_values),
            'large_straight': lambda: YahtzeeScoring.calculate_large_straight(dice_values),
            'yahtzee': lambda: YahtzeeScoring.calculate_yahtzee(dice_values),
            'chance': lambda: YahtzeeScoring.calculate_chance(dice_values)
        }
        return scoring_map.get(category, lambda: 0)()
    
    @staticmethod
    def calculate_totals(scorecard: ScoreCard) -> ScoreCard:
        """Calculate all totals for the scorecard"""
        # Upper section total
        upper_scores = [
            scorecard.ones or 0,
            scorecard.twos or 0,
            scorecard.threes or 0,
            scorecard.fours or 0,
            scorecard.fives or 0,
            scorecard.sixes or 0
        ]
        scorecard.upper_subtotal = sum(upper_scores)
        scorecard.upper_bonus = 35 if scorecard.upper_subtotal >= 63 else 0
        scorecard.upper_total = scorecard.upper_subtotal + scorecard.upper_bonus
        
        # Lower section total
        lower_scores = [
            scorecard.three_of_a_kind or 0,
            scorecard.four_of_a_kind or 0,
            scorecard.full_house or 0,
            scorecard.small_straight or 0,
            scorecard.large_straight or 0,
            scorecard.yahtzee or 0,
            scorecard.chance or 0
        ]
        scorecard.lower_total = sum(lower_scores)
        
        # Grand total
        scorecard.grand_total = scorecard.upper_total + scorecard.lower_total
        
        return scorecard

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Yahtzee Game API"}

@api_router.post("/games", response_model=GameState)
async def create_game(game_create: GameCreate):
    """Create a new Yahtzee game"""
    players = []
    for i, name in enumerate(game_create.player_names):
        player = Player(name=name, is_active=(i == 0))
        players.append(player)
    
    game = GameState(
        players=players,
        game_mode=game_create.game_mode,
        current_player=0,
        rolls_remaining=3,
        rolls_used=0
    )
    
    # Start with initial dice roll
    game.dice.values = [random.randint(1, 6) for _ in range(5)]
    game.dice.held = [False] * 5
    game.rolls_remaining = 2  # Already used 1 roll for initial dice
    game.rolls_used = 1
    
    await db.games.insert_one(game.dict())
    return game

@api_router.get("/games/{game_id}", response_model=GameState)
async def get_game(game_id: str):
    """Get game state"""
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameState(**game)

@api_router.post("/games/{game_id}/roll")
async def roll_dice(game_id: str, roll_request: RollDiceRequest):
    """Roll dice for current turn"""
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_state = GameState(**game)
    
    if game_state.rolls_remaining <= 0:
        raise HTTPException(status_code=400, detail="No rolls remaining")
    
    # Roll non-held dice only
    for i in range(5):
        if not roll_request.held_dice[i]:
            game_state.dice.values[i] = random.randint(1, 6)
    
    # Update held dice state
    game_state.dice.held = roll_request.held_dice.copy()
    
    # Update roll counters
    game_state.rolls_remaining -= 1
    game_state.rolls_used += 1
    
    await db.games.replace_one({"id": game_id}, game_state.dict())
    return game_state

@api_router.post("/games/{game_id}/score")
async def score_category(game_id: str, score_request: ScoreRequest):
    """Score a category and end turn"""
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_state = GameState(**game)
    
    # Must have used at least one roll before scoring
    if game_state.rolls_used == 0:
        raise HTTPException(status_code=400, detail="Must roll dice before scoring")
    
    current_player = game_state.players[game_state.current_player]
    
    # Check if category is already scored
    if hasattr(current_player.scorecard, score_request.category):
        current_value = getattr(current_player.scorecard, score_request.category)
        if current_value is not None:
            raise HTTPException(status_code=400, detail="Category already scored")
    
    # Calculate score
    score = YahtzeeScoring.get_possible_score(game_state.dice.values, score_request.category)
    
    # Set score
    setattr(current_player.scorecard, score_request.category, score)
    
    # Calculate totals
    current_player.scorecard = YahtzeeScoring.calculate_totals(current_player.scorecard)
    
    # Check if game is over
    all_categories = ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes',
                     'three_of_a_kind', 'four_of_a_kind', 'full_house',
                     'small_straight', 'large_straight', 'yahtzee', 'chance']
    
    game_over = True
    for player in game_state.players:
        for category in all_categories:
            if getattr(player.scorecard, category) is None:
                game_over = False
                break
        if not game_over:
            break
    
    if game_over:
        game_state.game_over = True
        # Find winner
        max_score = max(player.scorecard.grand_total for player in game_state.players)
        winner = next(player for player in game_state.players if player.scorecard.grand_total == max_score)
        game_state.winner = winner.name
    else:
        # Next player's turn
        game_state.current_player = (game_state.current_player + 1) % len(game_state.players)
        if game_state.current_player == 0:
            game_state.turn_number += 1
        
        # Reset for next turn - start with initial roll
        game_state.dice.values = [random.randint(1, 6) for _ in range(5)]
        game_state.dice.held = [False] * 5
        game_state.rolls_remaining = 2  # Already used 1 roll for initial dice
        game_state.rolls_used = 1
    
    await db.games.replace_one({"id": game_id}, game_state.dict())
    return game_state

@api_router.get("/games/{game_id}/possible-scores")
async def get_possible_scores(game_id: str):
    """Get possible scores for current dice"""
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_state = GameState(**game)
    current_player = game_state.players[game_state.current_player]
    
    # Only return possible scores if at least one roll has been used
    if game_state.rolls_used == 0:
        return {}
    
    possible_scores = {}
    categories = ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes',
                 'three_of_a_kind', 'four_of_a_kind', 'full_house',
                 'small_straight', 'large_straight', 'yahtzee', 'chance']
    
    for category in categories:
        if getattr(current_player.scorecard, category) is None:
            possible_scores[category] = YahtzeeScoring.get_possible_score(game_state.dice.values, category)
    
    return possible_scores

@api_router.post("/high-scores", response_model=HighScore)
async def create_high_score(high_score: HighScoreCreate):
    """Create a new high score"""
    score_obj = HighScore(**high_score.dict())
    await db.high_scores.insert_one(score_obj.dict())
    return score_obj

@api_router.get("/high-scores", response_model=List[HighScore])
async def get_high_scores():
    """Get top 10 high scores"""
    high_scores = await db.high_scores.find().sort("score", -1).limit(10).to_list(10)
    return [HighScore(**score) for score in high_scores]

@api_router.get("/high-scores/check/{score}")
async def check_high_score(score: int):
    """Check if score qualifies for high score list"""
    count = await db.high_scores.count_documents({})
    if count < 10:
        return {"is_high_score": True, "rank": count + 1}
    
    lowest_high_score = await db.high_scores.find().sort("score", 1).limit(1).to_list(1)
    if lowest_high_score and score > lowest_high_score[0]["score"]:
        # Count how many scores are higher
        rank = await db.high_scores.count_documents({"score": {"$gt": score}}) + 1
        return {"is_high_score": True, "rank": rank}
    
    return {"is_high_score": False, "rank": None}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()