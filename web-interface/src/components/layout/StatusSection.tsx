import type { ChangeEvent } from 'react';
import { Difficulty } from '../Difficulty';
import { Timer } from '../Timer';
import { Numbers } from '../Numbers';
import { Action } from '../Action';

type StatusSectionProps = {
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void,
  onClickNumber: (number: string) => void,
  onClickUndo: () => void,
  onClickErase: () => void,
  disabled?: boolean
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
    </section>
  )
}
