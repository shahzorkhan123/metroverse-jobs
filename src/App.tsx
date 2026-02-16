import React from "react";
import GlobalStyles from "./styling/GlobalStyles";
import Helmet from "react-helmet";
import { Route, Switch } from "react-router-dom";
import Landing from "./pages/landing";
import City from "./pages/cities/profiles";
import Informational from "./pages/informational";
import { Routes } from "./routing/routes";
import "./styling/fonts/fonts.css";
import AppContext, { useWindowWidth } from "./contextProviders/appContext";
import { OverlayPortal } from "./components/standardModal";
import useFluent from "./hooks/useFluent";

function App() {
  const windowDimensions = useWindowWidth();
  const getString = useFluent();
  const defaultMetaTitle = getString("meta-data-title-default");
  return (
    <>
      <Helmet>
        <title>{defaultMetaTitle}</title>
        <meta property="og:title" content={defaultMetaTitle} />
      </Helmet>
      <GlobalStyles />
      <AppContext.Provider value={{ windowDimensions }}>
        <Switch>
          <Route exact path={Routes.Landing} component={Landing} />
          <Route path={Routes.CityBase} component={City} />
          <Route path={Routes.AboutBase} component={Informational} />
          <Route path={Routes.ContactBase} component={Informational} />
          <Route path={Routes.FaqBase} component={Informational} />
          <Route component={Landing} />
        </Switch>
        <OverlayPortal />
      </AppContext.Provider>
    </>
  );
}

export default App;
