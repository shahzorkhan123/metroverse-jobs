/**
 * Get state abbreviation from country metadata
 * Falls back to taking first 2-3 letters if not found
 */
import { CountryMetadata } from '../dataProvider/types';

export function getStateAbbreviation(
  stateName: string,
  countryMetadata: CountryMetadata | null
): string {
  if (!countryMetadata || !countryMetadata.stateAbbreviations) {
    // Fallback: take first 2-3 letters
    return stateName.slice(0, 2).toUpperCase();
  }

  return countryMetadata.stateAbbreviations[stateName] || stateName.slice(0, 2).toUpperCase();
}
