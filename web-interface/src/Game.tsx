import { useState, useEffect, type ChangeEvent } from 'react';
import { fetchRandomPuzzle, validatePuzzle, type Difficulty } from './api/client';
import { Header } from './components/layout/Header';
import { GameSection } from './components/layout/GameSection';
import { StatusSection } from './components/layout/StatusSection';
import { useSudokuContext } from './context/SudokuContext';

/**
 * Game is the main React component.
 */
export const Game = () => {
  /**
   * All the variables for holding state:
   * gameArray: Holds the current state of the game.
   * initArray: Holds the initial state of the game.
   * difficulty: Difficulty level - 'Easy', 'Medium' or 'Hard'
   * timeGameStarted: Time the current game was started.
   * cellSelected: If a game cell is selected by the user, holds the index.
   * history: history of the current game, for 'Undo' purposes.
   * overlay: Is the 'Game Solved' overlay enabled?
   * won: Is the game 'won'?
   */
  let { gameArray, setGameArray,
        difficulty, setDifficulty,
        setTimeGameStarted,
        cellSelected, setCellSelected,
        initArray, setInitArray,
        setWon } = useSudokuContext();
  let [ history, setHistory ] = useState<string[][]>([]);
  let [ overlay, setOverlay ] = useState<boolean>(false);
  let [ loading, setLoading ] = useState<boolean>(true);
  let [ statusMessage, setStatusMessage ] = useState<string>('');

  /**
   * Creates a new game and initializes the state variables.
   */
  async function _createNewGame(nextDifficulty: Difficulty = difficulty) {
    setLoading(true);
    setStatusMessage('Loading puzzle...');

    try {
      const response = await fetchRandomPuzzle(nextDifficulty);
      const puzzleArray = response.puzzle.split('');

      setDifficulty(response.difficulty);
      setInitArray(puzzleArray);
      setGameArray(puzzleArray);
      setTimeGameStarted(Date.now());
      setCellSelected(-1);
      setHistory([]);
      setWon(false);
      setOverlay(false);
      setStatusMessage('');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load puzzle.';
      setStatusMessage(`Backend unavailable: ${message}`);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Checks if the game is solved.
   */
  async function _isSolved(board: string[]) {
    if (board.some((cell) => cell === '0')) {
      return false;
    }

    const validation = await validatePuzzle(board.join(''));
    return validation.valid_solution;
  }

  /**
   * Fills the cell with the given 'value'
   * Used to Fill / Erase as required.
   */
  async function _fillCell(index: number, value: string) {
    if (!loading && initArray[index] === '0') {
      // Direct copy results in interesting set of problems, investigate more!
      let tempArray = gameArray.slice();
      let tempHistory = history.slice();

      // Can't use tempArray here, due to Side effect below!!
      tempHistory.push(gameArray.slice());
      setHistory(tempHistory);

      tempArray[index] = value;
      setGameArray(tempArray);

      try {
        if (await _isSolved(tempArray)) {
          setOverlay(true);
          setWon(true);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to validate puzzle.';
        setStatusMessage(`Backend unavailable: ${message}`);
      }
    }
  }

  /**
   * On Click of 'New Game' link,
   * create a new game.
   */
  function onClickNewGame() {
    _createNewGame();
  }

  /**
   * On Click of a Game cell.
   */
  function onClickCell(indexOfArray: number) {
    setCellSelected(indexOfArray);
  }

  /**
   * On Change Difficulty,
   * 1. Update 'Difficulty' level
   * 2. Create New Game
   */
  function onChangeDifficulty(e: ChangeEvent<HTMLSelectElement>) {
    _createNewGame(e.target.value as Difficulty);
  }

  /**
   * On Click of Number in Status section,
   * fill the selected cell.
   */
  function onClickNumber(number: string) {
    if (cellSelected !== -1) {
      _fillCell(cellSelected, number);
    }
  }

  /**
   * On Click Undo,
   * try to Undo the latest change.
   */
  function onClickUndo() {
    if(history.length) {
      let tempHistory = history.slice();
      let tempArray = tempHistory.pop();
      setHistory(tempHistory);
      if (tempArray !== undefined)
        setGameArray(tempArray);
    }
  }

  /**
   * On Click Erase,
   * try to delete the cell.
   */
  function onClickErase() {
    if(cellSelected !== -1 && gameArray[cellSelected] !== '0') {
      _fillCell(cellSelected, '0');
    }
  }

  function shouldIgnoreKeyboardShortcut(target: EventTarget | null) {
    if (!(target instanceof HTMLElement)) {
      return false;
    }

    return target.isContentEditable ||
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.tagName === 'SELECT';
  }

  /**
   * Close the overlay on Click.
   */
  function onClickOverlay() {
    _createNewGame();
  }

  /**
   * On load, create a New Game.
   */
  useEffect(() => {
    _createNewGame();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (shouldIgnoreKeyboardShortcut(event.target)) {
        return;
      }

      const isUndo = event.key.toLowerCase() === 'z' && (event.metaKey || event.ctrlKey);
      if (isUndo) {
        event.preventDefault();
        onClickUndo();
        return;
      }

      if (cellSelected === -1 || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }

      if (/^[1-9]$/.test(event.key)) {
        event.preventDefault();
        onClickNumber(event.key);
        return;
      }

      if (event.key === 'Backspace' || event.key === 'Delete') {
        event.preventDefault();
        onClickErase();
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [cellSelected, gameArray, history, loading]);

  return (
    <>
      <div className={overlay?"container blur":"container"}>
        <Header onClick={onClickNewGame} disabled={loading}/>
        <div className="innercontainer">
          <GameSection
            onClick={(indexOfArray: number) => onClickCell(indexOfArray)}
          />
          <StatusSection
            onClickNumber={(number: string) => onClickNumber(number)}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => onChangeDifficulty(e)}
            onClickUndo={onClickUndo}
            onClickErase={onClickErase}
            disabled={loading}
          />
        </div>
        {
          statusMessage
            ? <p className="status-message" role="status">{statusMessage}</p>
            : null
        }
      </div>
      <div className= { overlay
                        ? "overlay overlay--visible"
                        : "overlay"
                      }
           onClick={onClickOverlay}
      >
        <h2 className="overlay__text">
          You <span className="overlay__textspan1">solved</span> <span className="overlay__textspan2">it!</span>
        </h2>
      </div>
    </>
  );
}
