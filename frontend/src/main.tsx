import React from "react";
import ReactDOM from "react-dom/client";
import {
    QueryClient,
    QueryClientProvider,
} from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import "./styles.css";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Treat fetched data as fresh for 60 seconds.
            // Moving between pages during this period will normally use
            // the cache instead of making another API request.
            staleTime: 60_000,

            // Keep inactive data in memory for 10 minutes so returning
            // to a recently visited page feels immediate.
            gcTime: 10 * 60_000,

            // Keep active workspace views synchronized with changes made
            // by other members. This only refetches server state; it never
            // deletes, replaces, or copies records between workspaces.
            refetchInterval: 30_000,
            refetchIntervalInBackground: true,

            // Re-check immediately when a view is opened again, when the
            // browser regains focus, or when connectivity returns.
            refetchOnMount: "always",
            refetchOnWindowFocus: "always",
            refetchOnReconnect: "always",

            // Avoid repeatedly retrying slow or failed Render requests.
            retry: 1,
        },
    },
});

ReactDOM.createRoot(
    document.getElementById("root")!,
).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <App />
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>,
);