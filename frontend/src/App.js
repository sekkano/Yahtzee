import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Sound effects
const playDiceRollSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // Create multiple oscillators for richer sound
    const oscillators = [];
    const gainNodes = [];
    
    for (let i = 0; i < 3; i++) {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Different frequencies for each oscillator
      const baseFreq = 150 + (i * 100);
      oscillator.frequency.setValueAtTime(baseFreq, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(baseFreq * 1.5, audioContext.currentTime + 0.1);
      oscillator.frequency.exponentialRampToValueAtTime(baseFreq * 0.8, audioContext.currentTime + 0.3);
      
      gainNode.gain.setValueAtTime(0.03, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.4);
      
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.4);
      
      oscillators.push(oscillator);
      gainNodes.push(gainNode);
    }
  } catch (error) {
    console.log('Audio not supported or blocked');
  }
};

const playScoreSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(523, audioContext.currentTime); // C5
    oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.1); // E5
    oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.2); // G5
    
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.3);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.3);
  } catch (error) {
    console.log('Audio not supported or blocked');
  }
};

// Title Screen Component
const TitleScreen = ({ onGameStart }) => {
  return (
    <div className="title-screen">
      <div className="title-container">
        <h1 className="game-title">YAHTZEE</h1>
        <div className="game-menu">
          <button 
            className="menu-button"
            onClick={() => onGameStart('single', ['Player 1'])}
          >
            1 Player Game
          </button>
          <button 
            className="menu-button"
            onClick={() => onGameStart('multiplayer', ['Player 1', 'Player 2'])}
          >
            2 Player Game
          </button>
          <button 
            className="menu-button secondary"
            onClick={() => onGameStart('highscores', [])}
          >
            High Scores
          </button>
        </div>
      </div>
    </div>
  );
};

// Dice Component
const Dice = ({ value, held, onClick, canClick, isRolling }) => {
  const getDotPositions = (num) => {
    const positions = {
      1: [[2, 2]],
      2: [[1, 1], [3, 3]],
      3: [[1, 1], [2, 2], [3, 3]],
      4: [[1, 1], [1, 3], [3, 1], [3, 3]],
      5: [[1, 1], [1, 3], [2, 2], [3, 1], [3, 3]],
      6: [[1, 1], [1, 3], [2, 1], [2, 3], [3, 1], [3, 3]]
    };
    return positions[num] || [];
  };

  return (
    <div 
      className={`dice ${held ? 'held' : ''} ${canClick ? 'clickable' : ''} ${isRolling ? 'rolling' : ''}`}
      onClick={canClick ? onClick : null}
    >
      <div className="dice-face">
        {getDotPositions(value).map((pos, index) => (
          <div 
            key={index} 
            className="dot" 
            style={{
              gridColumnStart: pos[0],
              gridRowStart: pos[1]
            }}
          />
        ))}
      </div>
      {held && <div className="held-indicator">HELD</div>}
    </div>
  );
};

// Scorecard Component
const Scorecard = ({ players, currentPlayer, onCategorySelect, possibleScores, gameOver, canScore }) => {
  const categories = [
    { key: 'ones', label: 'Ones', section: 'upper' },
    { key: 'twos', label: 'Twos', section: 'upper' },
    { key: 'threes', label: 'Threes', section: 'upper' },
    { key: 'fours', label: 'Fours', section: 'upper' },
    { key: 'fives', label: 'Fives', section: 'upper' },
    { key: 'sixes', label: 'Sixes', section: 'upper' },
    { key: 'three_of_a_kind', label: '3 of a Kind', section: 'lower' },
    { key: 'four_of_a_kind', label: '4 of a Kind', section: 'lower' },
    { key: 'full_house', label: 'Full House', section: 'lower' },
    { key: 'small_straight', label: 'Small Straight', section: 'lower' },
    { key: 'large_straight', label: 'Large Straight', section: 'lower' },
    { key: 'yahtzee', label: 'YAHTZEE', section: 'lower' },
    { key: 'chance', label: 'Chance', section: 'lower' }
  ];

  const upperCategories = categories.filter(cat => cat.section === 'upper');
  const lowerCategories = categories.filter(cat => cat.section === 'lower');

  const renderScoreRow = (category, player, isActive) => {
    const score = player.scorecard[category.key];
    const possibleScore = possibleScores[category.key];
    const canSelect = isActive && score === null && possibleScore !== undefined && !gameOver && canScore;

    return (
      <tr key={category.key} className={`${canSelect ? 'selectable' : ''} ${score !== null ? 'scored' : ''}`}>
        <td className="category-label">{category.label}</td>
        <td 
          className={`score-cell ${canSelect ? 'clickable' : ''}`}
          onClick={canSelect ? () => onCategorySelect(category.key) : null}
        >
          {score !== null && score !== undefined ? score : 
           (canSelect ? `(${possibleScore})` : '—')}
        </td>
      </tr>
    );
  };

  return (
    <div className="scorecard-container">
      {players.map((player, index) => (
        <div key={player.id} className={`scorecard ${index === currentPlayer ? 'active' : ''}`}>
          <div className="player-header">
            <h3>{player.name}</h3>
            <div className="grand-total">{player.scorecard.grand_total}</div>
          </div>
          
          <table className="score-table">
            <thead>
              <tr>
                <th colSpan="2">UPPER SECTION</th>
              </tr>
            </thead>
            <tbody>
              {upperCategories.map(category => 
                renderScoreRow(category, player, index === currentPlayer)
              )}
              <tr className="subtotal-row">
                <td>Subtotal</td>
                <td>{player.scorecard.upper_subtotal}</td>
              </tr>
              <tr className="bonus-row">
                <td>Bonus (63+)</td>
                <td>{player.scorecard.upper_bonus}</td>
              </tr>
              <tr className="total-row">
                <td>Upper Total</td>
                <td>{player.scorecard.upper_total}</td>
              </tr>
            </tbody>
          </table>

          <table className="score-table">
            <thead>
              <tr>
                <th colSpan="2">LOWER SECTION</th>
              </tr>
            </thead>
            <tbody>
              {lowerCategories.map(category => 
                renderScoreRow(category, player, index === currentPlayer)
              )}
              <tr className="total-row">
                <td>Lower Total</td>
                <td>{player.scorecard.lower_total}</td>
              </tr>
              <tr className="grand-total-row">
                <td>GRAND TOTAL</td>
                <td>{player.scorecard.grand_total}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

// Game Screen Component
const GameScreen = ({ gameState, onRoll, onScore, onBackToTitle, possibleScores }) => {
  const [heldDice, setHeldDice] = useState([false, false, false, false, false]);
  const [isRolling, setIsRolling] = useState(false);
  const [lastScoredCategory, setLastScoredCategory] = useState(null);

  // Update held dice when game state changes
  useEffect(() => {
    if (gameState?.dice?.held) {
      setHeldDice(gameState.dice.held);
    }
  }, [gameState?.dice?.held]);

  const toggleDie = (index) => {
    if (gameState.rolls_remaining > 0) {
      const newHeld = [...heldDice];
      newHeld[index] = !newHeld[index];
      setHeldDice(newHeld);
    }
  };

  const handleRoll = async () => {
    if (gameState.rolls_remaining <= 0) return;
    
    setIsRolling(true);
    playDiceRollSound();
    
    // Delay to show animation
    setTimeout(async () => {
      await onRoll(heldDice);
      setIsRolling(false);
    }, 500);
  };

  const handleScore = async (category) => {
    setLastScoredCategory(category);
    playScoreSound();
    
    // Add scoring animation
    setTimeout(async () => {
      await onScore(category);
      setHeldDice([false, false, false, false, false]);
      setLastScoredCategory(null);
    }, 200);
  };

  const currentPlayer = gameState.players[gameState.current_player];
  const canScore = gameState.rolls_used > 0;
  const rollsUsed = gameState.rolls_used || 0;

  return (
    <div className="game-screen">
      <div className="game-header">
        <button className="back-button" onClick={onBackToTitle}>
          ← Back to Title
        </button>
        <h1>YAHTZEE</h1>
        <div className="turn-info">
          Turn {gameState.turn_number} - {currentPlayer.name}'s Turn
        </div>
      </div>

      <div className="game-content">
        <div className="dice-section">
          <div className="dice-container">
            {gameState.dice.values.map((value, index) => (
              <Dice
                key={index}
                value={value}
                held={heldDice[index]}
                onClick={() => toggleDie(index)}
                canClick={gameState.rolls_remaining > 0}
                isRolling={isRolling && !heldDice[index]}
              />
            ))}
          </div>
          
          <div className="roll-controls">
            <div className="roll-info">
              <div className="rolls-remaining">
                Rolls Remaining: {gameState.rolls_remaining}
              </div>
              <div className="rolls-used">
                Rolls Used: {rollsUsed}/3
              </div>
            </div>
            <button 
              className="roll-button"
              onClick={handleRoll}
              disabled={gameState.rolls_remaining === 0 || isRolling}
            >
              {isRolling ? 'Rolling...' : 'Roll Dice'}
            </button>
            <div className="instruction">
              {gameState.rolls_remaining > 0 ? 
                "Click dice to hold them, then roll again" : 
                (canScore ? "Select a category to score" : "No rolls remaining")}
            </div>
            {!canScore && (
              <div className="warning">
                You must roll at least once before scoring!
              </div>
            )}
          </div>
        </div>

        <Scorecard
          players={gameState.players}
          currentPlayer={gameState.current_player}
          onCategorySelect={handleScore}
          possibleScores={possibleScores}
          gameOver={gameState.game_over}
          canScore={canScore}
        />
      </div>

      {gameState.game_over && (
        <div className="game-over-modal">
          <div className="modal-content">
            <h2>🎉 Game Over! 🎉</h2>
            <p><strong>Winner:</strong> {gameState.winner}</p>
            <p><strong>Final Score:</strong> {gameState.players.find(p => p.name === gameState.winner)?.scorecard.grand_total}</p>
            <button className="menu-button" onClick={onBackToTitle}>
              Back to Title
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// High Scores Component
const HighScoresScreen = ({ onBackToTitle }) => {
  const [highScores, setHighScores] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHighScores = async () => {
      try {
        const response = await axios.get(`${API}/high-scores`);
        setHighScores(response.data);
      } catch (error) {
        console.error('Error fetching high scores:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchHighScores();
  }, []);

  return (
    <div className="high-scores-screen">
      <div className="high-scores-container">
        <h1>HIGH SCORES</h1>
        <button className="back-button" onClick={onBackToTitle}>
          ← Back to Title
        </button>
        
        <div className="high-scores-table">
          {loading ? (
            <div className="loading">Loading high scores...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Name</th>
                  <th>Score</th>
                  <th>Mode</th>
                </tr>
              </thead>
              <tbody>
                {highScores.length > 0 ? (
                  highScores.map((score, index) => (
                    <tr key={score.id}>
                      <td>{index + 1}</td>
                      <td>{score.player_name}</td>
                      <td>{score.score}</td>
                      <td>{score.game_mode === 'single' ? '1P' : '2P'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="no-scores">No high scores yet!</td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

// Name Entry Modal Component
const NameEntryModal = ({ isOpen, onSubmit, onCancel, score }) => {
  const [name, setName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (name.trim()) {
      onSubmit(name.trim());
      setName('');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>🏆 New High Score! 🏆</h2>
        <p>You scored <strong>{score}</strong> points!</p>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter your name"
            maxLength={20}
            autoFocus
          />
          <div className="modal-buttons">
            <button type="submit" className="menu-button">
              Submit
            </button>
            <button type="button" className="menu-button secondary" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [currentScreen, setCurrentScreen] = useState('title');
  const [gameState, setGameState] = useState(null);
  const [possibleScores, setPossibleScores] = useState({});
  const [showNameEntry, setShowNameEntry] = useState(false);
  const [highScoreData, setHighScoreData] = useState(null);
  const [loading, setLoading] = useState(false);

  const startGame = async (mode, playerNames) => {
    if (mode === 'highscores') {
      setCurrentScreen('highscores');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/games`, {
        game_mode: mode,
        player_names: playerNames
      });
      setGameState(response.data);
      setCurrentScreen('game');
      fetchPossibleScores(response.data.id);
    } catch (error) {
      console.error('Error starting game:', error);
      alert('Error starting game. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchPossibleScores = async (gameId) => {
    try {
      const response = await axios.get(`${API}/games/${gameId}/possible-scores`);
      setPossibleScores(response.data);
    } catch (error) {
      console.error('Error fetching possible scores:', error);
    }
  };

  const rollDice = async (heldDice) => {
    try {
      const response = await axios.post(`${API}/games/${gameState.id}/roll`, {
        game_id: gameState.id,
        held_dice: heldDice
      });
      setGameState(response.data);
      fetchPossibleScores(gameState.id);
    } catch (error) {
      console.error('Error rolling dice:', error);
      alert('Error rolling dice. Please try again.');
    }
  };

  const scoreCategory = async (category) => {
    try {
      const response = await axios.post(`${API}/games/${gameState.id}/score`, {
        game_id: gameState.id,
        category: category
      });
      setGameState(response.data);
      
      // Check for high score if game is over
      if (response.data.game_over) {
        const winnerScore = response.data.players.find(p => p.name === response.data.winner)?.scorecard.grand_total;
        checkHighScore(winnerScore, response.data.game_mode, response.data.winner);
      } else {
        fetchPossibleScores(gameState.id);
      }
    } catch (error) {
      console.error('Error scoring category:', error);
      alert('Error scoring category. Please try again.');
    }
  };

  const checkHighScore = async (score, gameMode, playerName) => {
    try {
      const response = await axios.get(`${API}/high-scores/check/${score}`);
      if (response.data.is_high_score) {
        setHighScoreData({ score, gameMode, playerName });
        setShowNameEntry(true);
      }
    } catch (error) {
      console.error('Error checking high score:', error);
    }
  };

  const submitHighScore = async (name) => {
    try {
      await axios.post(`${API}/high-scores`, {
        player_name: name,
        score: highScoreData.score,
        game_mode: highScoreData.gameMode
      });
      setShowNameEntry(false);
      setHighScoreData(null);
    } catch (error) {
      console.error('Error submitting high score:', error);
      alert('Error submitting high score. Please try again.');
    }
  };

  const backToTitle = () => {
    setCurrentScreen('title');
    setGameState(null);
    setPossibleScores({});
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading game...</p>
      </div>
    );
  }

  return (
    <div className="App">
      {currentScreen === 'title' && (
        <TitleScreen onGameStart={startGame} />
      )}
      
      {currentScreen === 'game' && gameState && (
        <GameScreen
          gameState={gameState}
          onRoll={rollDice}
          onScore={scoreCategory}
          onBackToTitle={backToTitle}
          possibleScores={possibleScores}
        />
      )}
      
      {currentScreen === 'highscores' && (
        <HighScoresScreen onBackToTitle={backToTitle} />
      )}

      <NameEntryModal
        isOpen={showNameEntry}
        onSubmit={submitHighScore}
        onCancel={() => setShowNameEntry(false)}
        score={highScoreData?.score}
      />
    </div>
  );
}

export default App;