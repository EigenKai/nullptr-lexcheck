import React from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/nunito-sans";
import "./brand-fonts.css";
import "./brand.css";
import "./prototype.css";
import "./style.css";
import "./lex-identity.css";
import "./lex-review.css";
import "./lex-workspace.css";
import App from "./App.jsx";
import { LanguageProvider } from "./i18n.jsx";
createRoot(document.getElementById("root")).render(
  <LanguageProvider>
    <App />
  </LanguageProvider>,
);
