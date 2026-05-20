import type { ChangeEvent } from 'react';
import { useSudokuContext } from '../context/SudokuContext';

type DifficultyProps = {
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void,
  disabled?: boolean
};

/**
 * React component for the Difficulty Selector.
 */
export const Difficulty = (props: DifficultyProps) => {
  let { difficulty } = useSudokuContext();

  return (
    <div className="status__difficulty">
      <span className="status__difficulty-text">Difficulty:&nbsp;&nbsp;</span>
      <select name="status__difficulty-select" className="status__difficulty-select" value={difficulty} onChange={props.onChange} disabled={props.disabled}>
        <option value="Easy">Easy</option>
        <option value="Medium">Medium</option>
        <option value="Hard">Hard</option>
        <option value="Diabolical">Diabolical</option>
      </select>
    </div>
  )
}
