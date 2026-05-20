type HeaderProps = {
  onClick: () => void
};

/**
 * React component for the Header Section.
 */
export const Header = (props: HeaderProps) => {
  return (
    <header className="header">
      <h1>
        Su<span className="header__group-one">do</span><span className="header__group-two">ku</span>
      </h1>
      <button className="header__new-game" type="button" onClick={props.onClick}>
        New Game
      </button>
    </header>
  )
}
