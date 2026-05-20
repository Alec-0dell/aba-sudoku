type NumbersProps = {
  onClickNumber: (number: string) => void
};

/**
 * React component for the Number Selector in the Status Section.
 */
export const Numbers = ({ onClickNumber } : NumbersProps) => {
  return (
    <div className="status__numbers">
      {
        [1,2,3,4,5,6,7,8,9].map((number) => {
          return (
            <button className="status__number" type="button" key={number} onClick={() => onClickNumber(number.toString())}>{number}</button>
          )
        })
      }
    </div>
  )
}
