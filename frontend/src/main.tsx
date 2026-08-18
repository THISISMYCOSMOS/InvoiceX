import "./browserPolyfills";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { SignupAuthProvider } from "./auth/SignupAuthContext";
import "./styles.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SignupAuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </SignupAuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
