import useFluent from "./useFluent";
import { sectorColorMap } from "../styling/styleUtils";
import { useStaticData } from "../dataProvider";

export default () => {
  const getString = useFluent();
  const { countryMetadata } = useStaticData();

  // Use country-specific major groups from metadata if available
  if (countryMetadata?.majorGroups) {
    return countryMetadata.majorGroups.map(({ id, name, color }) => ({
      id,
      color,
      name,
    }));
  }

  // Fallback to SOC sector map with fluent strings
  return sectorColorMap.map(({ id, color }) => ({
    id,
    color,
    name: getString("global-naics-sector-name-" + id),
  }));
};
