import { useStaticData } from "../dataProvider";

const defaultTerminology: Record<string, string> = {
  occupationCode: "SOC Code",
  majorGroup: "Major Group",
  wage: "Annual Mean Wage",
  employment: "Employment",
};

/**
 * Returns metadata-driven terminology for the selected country.
 * Falls back to US SOC defaults if no country metadata is available.
 */
export default function useTerminology(): Record<string, string> {
  const { countryMetadata } = useStaticData();
  return countryMetadata?.terminology || defaultTerminology;
}
