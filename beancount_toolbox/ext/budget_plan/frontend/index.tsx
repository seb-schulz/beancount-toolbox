import * as React from "react";
import * as ReactDOM from "react-dom/client";

interface PositionChildren {
  [account: string]: Position;
}

interface Position {
  name: string;
  positions: {
    [currency: string]: number;
  };
  defaultShowChildren?: boolean;
  children?: PositionChildren;
}

function Position({
  name,
  positions,
  defaultShowChildren,
  children,
}: Position) {
  const [showChildren, setShowChildren] = React.useState(defaultShowChildren);
  const positionList = showChildren &&
    children &&
    Object.keys(children).length > 0 && (
      <div>
        <PositionList
          children={children}
          defaultShowChildren={!!defaultShowChildren}
        />
      </div>
    );

  let childrenToggle: React.JSX.Element | null = null;
  let numClassName = "num";
  if (children && Object.keys(children).length > 0) {
    childrenToggle = (
      <span
        onClick={() => setShowChildren(!showChildren)}
        style={{ cursor: "pointer" }}
      >
        {showChildren ? "▾" : "▸ "}
      </span>
    );

    if (showChildren) numClassName += " dimmed";
  }

  return (
    <>
      <ul>
        <li>
          {childrenToggle} {name}
        </li>
        {Object.keys(positions).map((currency) => (
          <li key={currency} className={numClassName}>
            {positions[currency]}
          </li>
        ))}
      </ul>
      {positionList}
    </>
  );
}

function PositionList({
  defaultShowChildren,
  children,
}: {
  defaultShowChildren: boolean;
  children?: PositionChildren;
}) {
  return (
    children &&
    Object.keys(children).map((account) => (
      <Position
        key={children[account].name}
        name={account}
        positions={children[account].positions}
        children={children[account].children}
        defaultShowChildren={defaultShowChildren}
      />
    ))
  );
}

function BudgetPlan({ name, positions, children }: Position) {
  console.log("Children", children);
  return (
    <>
      <ul>
        <li>Account</li>
        {Object.keys(positions).map((currency) => (
          <li key={currency}>{currency}</li>
        ))}
      </ul>
      <PositionList children={children} defaultShowChildren={false} />
      <Position name={name} positions={positions} />
    </>
  );
}

const index = {
  init() {
    console.log("initialising extension");
  },
  onPageLoad() {
    console.log("a Fava report page has loaded", window.location.pathname);
  },
  onExtensionPageLoad() {
    console.log(
      "the page for the PortfolioList extension has loaded",
      window.location.pathname
    );

    const element = document.getElementById("budget-plan") as HTMLElement;
    const root = ReactDOM.createRoot(element);
    const budget = JSON.parse(element.dataset.budget || "null");

    const budgetPlan = budget ? (
      <BudgetPlan
        name={budget.name}
        positions={budget.positions}
        children={budget.children}
      />
    ) : (
      <div>No budget data. Maybe time period undefined.</div>
    );

    root.render(<React.StrictMode>{budgetPlan}</React.StrictMode>);
  },
};

export default index;
