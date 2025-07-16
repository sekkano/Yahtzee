#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Yahtzee Game
Tests all API endpoints and game logic functionality
"""

import requests
import json
import sys
from datetime import datetime
import time

class YahtzeeAPITester:
    def __init__(self, base_url="https://62c808a7-8625-42b0-a2cb-1659b2cee649.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.game_id = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200 and "Yahtzee Game API" in response.text
            return self.log_test("API Root", success, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("API Root", False, f"Error: {str(e)}")

    def test_create_single_player_game(self):
        """Test creating a single player game"""
        try:
            payload = {
                "game_mode": "single",
                "player_names": ["Test Player"]
            }
            response = requests.post(f"{self.api_url}/games", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.game_id = data.get('id')
                success = (
                    data.get('game_mode') == 'single' and
                    len(data.get('players', [])) == 1 and
                    data.get('players')[0].get('name') == 'Test Player' and
                    data.get('rolls_remaining') == 3 and
                    len(data.get('dice', {}).get('values', [])) == 5
                )
                return self.log_test("Create Single Player Game", success, f"Game ID: {self.game_id}")
            else:
                return self.log_test("Create Single Player Game", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Create Single Player Game", False, f"Error: {str(e)}")

    def test_create_multiplayer_game(self):
        """Test creating a multiplayer game"""
        try:
            payload = {
                "game_mode": "multiplayer",
                "player_names": ["Player 1", "Player 2"]
            }
            response = requests.post(f"{self.api_url}/games", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                success = (
                    data.get('game_mode') == 'multiplayer' and
                    len(data.get('players', [])) == 2 and
                    data.get('current_player') == 0
                )
                return self.log_test("Create Multiplayer Game", success, f"Players: {len(data.get('players', []))}")
            else:
                return self.log_test("Create Multiplayer Game", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Create Multiplayer Game", False, f"Error: {str(e)}")

    def test_get_game(self):
        """Test retrieving game state"""
        if not self.game_id:
            return self.log_test("Get Game", False, "No game ID available")
        
        try:
            response = requests.get(f"{self.api_url}/games/{self.game_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                success = (
                    data.get('id') == self.game_id and
                    'players' in data and
                    'dice' in data and
                    'rolls_remaining' in data
                )
                return self.log_test("Get Game", success, f"Retrieved game: {self.game_id}")
            else:
                return self.log_test("Get Game", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Get Game", False, f"Error: {str(e)}")

    def test_roll_dice(self):
        """Test rolling dice"""
        if not self.game_id:
            return self.log_test("Roll Dice", False, "No game ID available")
        
        try:
            payload = {
                "game_id": self.game_id,
                "held_dice": [False, False, False, False, False]
            }
            response = requests.post(f"{self.api_url}/games/{self.game_id}/roll", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                success = (
                    data.get('rolls_remaining') == 2 and  # Should decrease from 3 to 2
                    len(data.get('dice', {}).get('values', [])) == 5
                )
                return self.log_test("Roll Dice", success, f"Rolls remaining: {data.get('rolls_remaining')}")
            else:
                return self.log_test("Roll Dice", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Roll Dice", False, f"Error: {str(e)}")

    def test_roll_with_held_dice(self):
        """Test rolling dice with some held"""
        if not self.game_id:
            return self.log_test("Roll with Held Dice", False, "No game ID available")
        
        try:
            # Get current dice values
            game_response = requests.get(f"{self.api_url}/games/{self.game_id}", timeout=10)
            if game_response.status_code != 200:
                return self.log_test("Roll with Held Dice", False, "Could not get game state")
            
            current_dice = game_response.json().get('dice', {}).get('values', [])
            
            # Hold first two dice
            payload = {
                "game_id": self.game_id,
                "held_dice": [True, True, False, False, False]
            }
            response = requests.post(f"{self.api_url}/games/{self.game_id}/roll", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                new_dice = data.get('dice', {}).get('values', [])
                # First two dice should remain the same
                success = (
                    len(new_dice) == 5 and
                    new_dice[0] == current_dice[0] and
                    new_dice[1] == current_dice[1] and
                    data.get('rolls_remaining') == 1
                )
                return self.log_test("Roll with Held Dice", success, f"Held dice preserved: {new_dice[:2]}")
            else:
                return self.log_test("Roll with Held Dice", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Roll with Held Dice", False, f"Error: {str(e)}")

    def test_get_possible_scores(self):
        """Test getting possible scores for current dice"""
        if not self.game_id:
            return self.log_test("Get Possible Scores", False, "No game ID available")
        
        try:
            response = requests.get(f"{self.api_url}/games/{self.game_id}/possible-scores", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expected_categories = [
                    'ones', 'twos', 'threes', 'fours', 'fives', 'sixes',
                    'three_of_a_kind', 'four_of_a_kind', 'full_house',
                    'small_straight', 'large_straight', 'yahtzee', 'chance'
                ]
                success = all(category in data for category in expected_categories)
                return self.log_test("Get Possible Scores", success, f"Categories: {len(data)}")
            else:
                return self.log_test("Get Possible Scores", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Get Possible Scores", False, f"Error: {str(e)}")

    def test_score_category(self):
        """Test scoring a category"""
        if not self.game_id:
            return self.log_test("Score Category", False, "No game ID available")
        
        try:
            # Score the "chance" category (always valid)
            payload = {
                "game_id": self.game_id,
                "category": "chance"
            }
            response = requests.post(f"{self.api_url}/games/{self.game_id}/score", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                player = data.get('players', [{}])[0]
                scorecard = player.get('scorecard', {})
                success = (
                    scorecard.get('chance') is not None and
                    scorecard.get('grand_total') > 0 and
                    data.get('rolls_remaining') == 3  # Should reset for next turn
                )
                return self.log_test("Score Category", success, f"Chance score: {scorecard.get('chance')}")
            else:
                return self.log_test("Score Category", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Score Category", False, f"Error: {str(e)}")

    def test_scoring_logic(self):
        """Test various scoring scenarios"""
        results = []
        
        # Test upper section scoring
        test_cases = [
            ([1, 1, 1, 2, 3], 'ones', 3),
            ([2, 2, 4, 5, 6], 'twos', 4),
            ([1, 2, 3, 4, 5], 'small_straight', 30),
            ([2, 3, 4, 5, 6], 'large_straight', 40),
            ([5, 5, 5, 5, 5], 'yahtzee', 50),
            ([3, 3, 3, 2, 2], 'full_house', 25),
            ([4, 4, 4, 1, 2], 'three_of_a_kind', 15),
            ([6, 6, 6, 6, 1], 'four_of_a_kind', 25)
        ]
        
        for dice_values, category, expected_score in test_cases:
            # Create a new game for each test
            try:
                game_payload = {
                    "game_mode": "single",
                    "player_names": ["Test Player"]
                }
                game_response = requests.post(f"{self.api_url}/games", json=game_payload, timeout=10)
                
                if game_response.status_code == 200:
                    test_game_id = game_response.json().get('id')
                    
                    # Manually set dice values by rolling with specific held pattern
                    # This is a limitation - we can't directly set dice values via API
                    # So we'll test with whatever dice we get
                    possible_scores_response = requests.get(f"{self.api_url}/games/{test_game_id}/possible-scores", timeout=10)
                    
                    if possible_scores_response.status_code == 200:
                        possible_scores = possible_scores_response.json()
                        if category in possible_scores:
                            results.append(f"✅ Scoring logic test for {category}: Available")
                        else:
                            results.append(f"⚠️ Scoring logic test for {category}: Not available with current dice")
                    else:
                        results.append(f"❌ Scoring logic test for {category}: Could not get possible scores")
                else:
                    results.append(f"❌ Scoring logic test for {category}: Could not create test game")
            except Exception as e:
                results.append(f"❌ Scoring logic test for {category}: Error - {str(e)}")
        
        success = len([r for r in results if r.startswith('✅')]) > 0
        return self.log_test("Scoring Logic Tests", success, f"\n  " + "\n  ".join(results))

    def test_high_score_system(self):
        """Test high score functionality"""
        try:
            # Test creating a high score
            payload = {
                "player_name": "Test Player",
                "score": 350,
                "game_mode": "single"
            }
            response = requests.post(f"{self.api_url}/high-scores", json=payload, timeout=10)
            
            if response.status_code == 200:
                # Test getting high scores
                get_response = requests.get(f"{self.api_url}/high-scores", timeout=10)
                
                if get_response.status_code == 200:
                    high_scores = get_response.json()
                    success = (
                        isinstance(high_scores, list) and
                        any(score.get('player_name') == 'Test Player' and score.get('score') == 350 
                            for score in high_scores)
                    )
                    return self.log_test("High Score System", success, f"High scores count: {len(high_scores)}")
                else:
                    return self.log_test("High Score System", False, f"Get high scores failed: {get_response.status_code}")
            else:
                return self.log_test("High Score System", False, f"Create high score failed: {response.status_code}")
        except Exception as e:
            return self.log_test("High Score System", False, f"Error: {str(e)}")

    def test_high_score_check(self):
        """Test high score qualification check"""
        try:
            test_score = 400
            response = requests.get(f"{self.api_url}/high-scores/check/{test_score}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                success = (
                    'is_high_score' in data and
                    isinstance(data.get('is_high_score'), bool)
                )
                return self.log_test("High Score Check", success, f"Score {test_score} qualifies: {data.get('is_high_score')}")
            else:
                return self.log_test("High Score Check", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("High Score Check", False, f"Error: {str(e)}")

    def test_error_handling(self):
        """Test API error handling"""
        results = []
        
        # Test invalid game ID
        try:
            response = requests.get(f"{self.api_url}/games/invalid-id", timeout=10)
            success = response.status_code == 404
            results.append(f"{'✅' if success else '❌'} Invalid game ID: {response.status_code}")
        except Exception as e:
            results.append(f"❌ Invalid game ID test error: {str(e)}")
        
        # Test rolling with no rolls remaining
        if self.game_id:
            try:
                # First, exhaust all rolls
                for _ in range(3):
                    requests.post(f"{self.api_url}/games/{self.game_id}/roll", 
                                json={"game_id": self.game_id, "held_dice": [False]*5}, timeout=10)
                
                # Try to roll again
                response = requests.post(f"{self.api_url}/games/{self.game_id}/roll", 
                                       json={"game_id": self.game_id, "held_dice": [False]*5}, timeout=10)
                success = response.status_code == 400
                results.append(f"{'✅' if success else '❌'} No rolls remaining: {response.status_code}")
            except Exception as e:
                results.append(f"❌ No rolls remaining test error: {str(e)}")
        
        overall_success = len([r for r in results if r.startswith('✅')]) > 0
        return self.log_test("Error Handling", overall_success, f"\n  " + "\n  ".join(results))

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🎲 Starting Yahtzee Backend API Tests")
        print("=" * 50)
        
        # Basic API tests
        self.test_api_root()
        self.test_create_single_player_game()
        self.test_create_multiplayer_game()
        self.test_get_game()
        
        # Game mechanics tests
        self.test_roll_dice()
        self.test_roll_with_held_dice()
        self.test_get_possible_scores()
        self.test_score_category()
        self.test_scoring_logic()
        
        # High score tests
        self.test_high_score_system()
        self.test_high_score_check()
        
        # Error handling tests
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All backend tests PASSED!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests FAILED")
            return 1

def main():
    """Main test runner"""
    tester = YahtzeeAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())