import type { ChangeEvent } from 'react';
import { Difficulty } from '../Difficulty';
import { Timer } from '../Timer';
import { Numbers } from '../Numbers';
import { Action } from '../Action';
import type { SolverInfo } from '../../api/client';

type StatusSectionProps = {
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void,
  onClickNumber: (number: string) => void,
  onClickUndo: () => void,
  onClickErase: () => void,
  onClickSolve: () => void,
  disabled?: boolean
  solvers?: SolverInfo[];
  selectedSolver?: string;
  onChangeSolver?: (id: string) => void;
  solveDisabled?: boolean;
};

/**
 * React component for the Status Section.
 */
export const StatusSection = (props: StatusSectionProps) => {
  return (
    <section className="status">
      <Difficulty onChange={props.onChange} disabled={props.disabled} />
      <Timer />
      <Numbers onClickNumber={(number) => props.onClickNumber(number)} disabled={props.disabled} />
      <div className="status__actions">
        <Action action='undo' onClickAction={props.onClickUndo} disabled={props.disabled} />
        <Action action='erase' onClickAction={props.onClickErase} disabled={props.disabled} />
      </div>
      <button className="status__solve" type="button" onClick={props.onClickSolve} disabled={props.disabled || props.solveDisabled}>
        Solve
      </button>
      {props.solvers && (
        <div className="status__difficulty">
          <span className="status__difficulty-text">Solver:&nbsp;&nbsp;</span>
          <select
            name="status__difficulty-select"
            className="status__difficulty-select"
            value={props.selectedSolver}
            onChange={(e) => props.onChangeSolver?.(e.target.value)}
            disabled={props.disabled}
          >
            {props.solvers.map((s) => (
              <option key={s.id} value={s.id} disabled={s.status !== 'available'}>
                {s.name}{s.status === 'loading' ? ' (loading...)' : s.status !== 'available' ? ' (unavailable)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}
    </section>
  )
}
