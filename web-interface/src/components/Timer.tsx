import { useState, useEffect } from 'react';
import { useSudokuContext } from '../context/SudokuContext';

/**
 * React component for the Timer in Status Section.
 * Uses the 'useEffect' hook to update the timer every second.
 */
export const Timer = () => {
  const [currentTime, setCurrentTime] = useState(Date.now());
  let { timeGameStarted, won } = useSudokuContext();

  useEffect(() => {
    if (won) {
      return;
    }

    const timerId = window.setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => window.clearInterval(timerId);
  }, [won]);

  function getTimer() {
    const secondsTotal = Math.floor((currentTime - timeGameStarted) / 1000);
    if (secondsTotal <= 0) {
      return '00:00';
    }

    const hours = Math.floor(secondsTotal / 3600);
    const minutes = Math.floor((secondsTotal % 3600) / 60);
    const seconds = secondsTotal % 60;
    let stringTimer = '';

    stringTimer += hours ? `${hours}:` : '';
    stringTimer += minutes ? `${minutes < 10 ? '0' : ''}${minutes}:` : '00:';
    stringTimer += seconds < 10 ? `0${seconds}` : seconds;

    return stringTimer;
  }

  return (
    <div className="status__time">{getTimer()}
    </div>
  )
}
