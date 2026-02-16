import { Datum as SearchDatum } from "react-panel-search";

export interface ExtendedSearchDatum extends SearchDatum {
  population: number;
  gdp: number;
}
