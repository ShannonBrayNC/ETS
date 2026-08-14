import React from "react";
import ReactDOM from "react-dom/client";
import { ProductionApp } from "./ProductionApp";
import "./styles.css";
import "./dark-pro.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ProductionApp />
  </React.StrictMode>,
);
