import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import Landing from "./screens/Landing";
import ClientHome from "./screens/ClientHome";
import MeetingView from "./screens/MeetingView";
import NewMeeting from "./screens/NewMeeting";

const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/c/:id", element: <ClientHome /> },
  { path: "/c/:id/new", element: <NewMeeting /> },
  { path: "/c/:id/m/:mid", element: <MeetingView /> },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
