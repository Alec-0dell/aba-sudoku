import React, { createContext, useContext, useState } from 'react';

type SudokuContextProps = {
  gameArray: string[],
  setGameArray: React.Dispatch<React.SetStateAction<string[]>>,
  difficulty: string,
  setDifficulty: React.Dispatch<React.SetStateAction<string>>,
  timeGameStarted: number,
  setTimeGameStarted: React.Dispatch<React.SetStateAction<number>>,
  cellSelected: number,
  setCellSelected: React.Dispatch<React.SetStateAction<number>>,
  initArray: string[],
  setInitArray: React.Dispatch<React.SetStateAction<string[]>>,
  won: boolean,
  setWon: React.Dispatch<React.SetStateAction<boolean>>
};


const SudokuContext = createContext<SudokuContextProps>({ gameArray: [], setGameArray: () => {},
                                                          difficulty: 'Easy', setDifficulty: () => {},
                                                          timeGameStarted: Date.now(), setTimeGameStarted: () => {},
                                                          cellSelected: -1, setCellSelected: () => {},
                                                          initArray: [], setInitArray: () => {},
                                                          won: false, setWon: () => {} });

type SudokuProviderProps = {
  children: React.ReactNode
};

export const SudokuProvider = ({ children }: SudokuProviderProps) => {
  let [ gameArray, setGameArray ] = useState<string[]>([]);
  let [ difficulty,setDifficulty ] = useState<string>('Easy');
  let [ timeGameStarted, setTimeGameStarted ] = useState<number>(Date.now());
  let [ cellSelected, setCellSelected ] = useState<number>(-1);
  let [ initArray, setInitArray ] = useState<string[]>([]);
  let [ won, setWon ] = useState<boolean>(false);

  return (
    <SudokuContext.Provider value={
      {
        gameArray, setGameArray,
        difficulty,setDifficulty,
        timeGameStarted, setTimeGameStarted,
        cellSelected, setCellSelected,
        initArray, setInitArray,
        won, setWon
      }
    }>
      {children}
    </SudokuContext.Provider>
  );
};

export const useSudokuContext = (): SudokuContextProps => useContext(SudokuContext);
