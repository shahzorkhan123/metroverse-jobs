import React from "react";
import ReactDOM from "react-dom";
import gsap from "gsap";
import App from "./App";
import {
  appLocalizationAndBundle as fluentValue,
  AppLocalizationAndBundleContext as FluentText,
} from "./contextProviders/getFluentLocalizationContext";
import { HashRouter } from "react-router-dom";
import * as serviceWorker from "./serviceWorker";
import { StaticDataProvider } from "./dataProvider";

// react-canvas-treemap uses GSAP 2 API (timeline.stop()) but GSAP 3 renamed it to pause().
// Patch the Timeline prototype so stop() exists as an alias for pause().
const _testTl = gsap.timeline();
const _tlProto = Object.getPrototypeOf(_testTl);
if (!_tlProto.stop) {
  _tlProto.stop = _tlProto.pause;
}
_testTl.kill();

ReactDOM.render(
  <StaticDataProvider>
    <FluentText.Provider value={fluentValue}>
      <HashRouter>
        <App />
      </HashRouter>
    </FluentText.Provider>
  </StaticDataProvider>,
  document.getElementById("root"),
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.register();
