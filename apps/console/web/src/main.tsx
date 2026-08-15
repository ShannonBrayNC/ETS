import React from "react";
import ReactDOM from "react-dom/client";
import { ProductionApp } from "./ProductionApp";
import { installOverlayAccessibility } from "./overlayAccessibility";
import "./styles.css";
import "./dark-pro.css";
import "./responsive-accessibility.css";

installOverlayAccessibility();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ProductionApp />
  </React.StrictMode>,
);
