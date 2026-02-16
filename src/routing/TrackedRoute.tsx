import React from "react";
import { Route } from "react-router-dom";

// Simplified route without Google Analytics tracking
const TrackedRoute = (props: any) => {
  return <Route {...props} />;
};

export default TrackedRoute;
