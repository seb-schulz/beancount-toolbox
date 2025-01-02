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
  children?: PositionChildren;
}

function Position({ name, positions, children }: Position) {
  const [showChildren, setShowChildren] = React.useState(true);
  const positionList = showChildren &&
    children &&
    Object.keys(children).length > 0 && (
      <div>
        <PositionList children={children} />
      </div>
    );

  let childrenToggle: React.JSX.Element | null = null;
  if (children && Object.keys(children).length > 0) {
    childrenToggle = (
      <span
        onClick={() => setShowChildren(!showChildren)}
        style={{ cursor: "pointer" }}
      >
        {showChildren ? "▾" : "▸ "}
      </span>
    );
  }

  return (
    <>
      <ul>
        <li>
          {childrenToggle} {name}
        </li>
        {Object.keys(positions).map((currency) => (
          <li key={currency} className="num">
            {positions[currency]}
          </li>
        ))}
      </ul>
      {positionList}
    </>
  );
}

function PositionList({ children }: { children?: PositionChildren }) {
  return (
    children &&
    Object.keys(children).map((account) => (
      <Position
        key={children[account].name}
        name={account}
        positions={children[account].positions}
        children={children[account].children}
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
      <PositionList children={children} />
      <Position name={name} positions={positions} />
    </>
  );
  //   return (
  //     <div className="row">
  //       <ol className="flex-table tree-table-new">
  //         <li className="head">
  //           <p>
  //             <span className="account-header"></span>
  //             <span className="num" title="US Dollar">
  //               USD
  //             </span>
  //             <span className="num other">Other</span>
  //           </p>
  //         </li>
  //         <li>
  //           <p>
  //             <span
  //               className="droptarget account-header"
  //               data-account-name="Assets"
  //             >
  //               <button type="button" className="unset">
  //                 ▾
  //               </button>
  //               <a
  //                 href="/example-beancount-file/account/Assets/?time=2024"
  //                 className="account"
  //               >
  //                 Assets
  //               </a>
  //             </span>
  //             <span className="num dimmed">112325.77 </span>
  //             <span className="num other dimmed">
  //               <span title="Employer Vacation Hours">−136 VACHR</span> <br />
  //             </span>
  //           </p>
  //         </li>
  //         <li>
  //           <p>
  //             <span
  //               className="droptarget account-intent"
  //               data-account-name="Assets:US"
  //             >
  //               <button type="button" className="unset">
  //                 ▾
  //               </button>
  //               <a
  //                 href="/example-beancount-file/account/Assets:US/?time=2024"
  //                 className="account"
  //               >
  //                 US
  //               </a>
  //             </span>
  //             <span className="num dimmed">112325.77 </span>
  //             <span className="num other dimmed">
  //               <span title="Employer Vacation Hours">−136 VACHR</span> <br />
  //             </span>
  //           </p>
  //         </li>
  //       </ol>
  //     </div>
  //   );
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

    const budget = JSON.parse(element.dataset.budget || "");
    root.render(
      <React.StrictMode>
        <BudgetPlan
          name={budget.name}
          positions={budget.positions}
          children={budget.children}
        />
      </React.StrictMode>
    );
  },
};

export default index;
