/**
 * Strategy pattern for occupation code hierarchy.
 * Abstracts SOC (US) and NCO (India) code structure differences.
 */

export interface OccupationHierarchyStrategy {
  /** Get the parent code for a given occupation code, or null if top level */
  getParent(code: string, knownCodes?: Set<string>): string | null;
  /** Get the hierarchy level (1-based) for a given occupation code */
  getLevel(code: string): number;
  /** Get the major group identifier (used for color mapping) */
  getMajorGroupId(code: string): string;
}

/**
 * SOC 2018 hierarchy (US BLS).
 * Format: XX-YYYY where XX is major group prefix.
 * Level 1: XX-0000 (major group, 22 groups)
 * Level 2: XX-X000 or XX-XX00 (minor group — XX-XX00 is SOC 2018 renumbered)
 * Level 3: XX-XXX0 (broad occupation)
 * Level 4: XX-XXXX (detailed occupation)
 */
class SOC2018Strategy implements OccupationHierarchyStrategy {
  getParent(code: string, knownCodes?: Set<string>): string | null {
    const prefix = code.substring(0, 3); // "XX-"
    const digits = code.substring(3);    // "YYYY"
    if (code.endsWith('-0000')) return null;  // level 1
    if (code.endsWith('00')) return prefix + '0000';  // level 2 → level 1
    if (code.endsWith('0')) {
      // level 3 → level 2: resolve ambiguous minor-group parent
      const renumbered = prefix + digits.substring(0, 2) + '00';
      const standard   = prefix + digits[0] + '000';
      if (renumbered === standard) return standard;
      if (knownCodes) {
        return knownCodes.has(renumbered) ? renumbered : standard;
      }
      return standard;
    }
    return prefix + digits.substring(0, 3) + '0';  // level 4 → level 3
  }

  getLevel(code: string): number {
    if (code.endsWith('-0000')) return 1;
    if (code.endsWith('00')) return 2;
    if (code.endsWith('0')) return 3;
    return 4;
  }

  getMajorGroupId(code: string): string {
    return code.substring(0, 2);
  }
}

/**
 * NCO 2015 hierarchy (India PLFS).
 * Format: plain digits, length determines level.
 * Level 1: X (division, 10 divisions: 0-9)
 * Level 2: XX (sub-division, ~30)
 * Level 3: XXX (group, ~116)
 * Level 4: XXXX (unit group, ~436) — national level only
 */
class NCO2015Strategy implements OccupationHierarchyStrategy {
  getParent(code: string): string | null {
    if (code.length <= 1) return null;
    return code.substring(0, code.length - 1);
  }

  getLevel(code: string): number {
    return code.length;
  }

  getMajorGroupId(code: string): string {
    return code[0];
  }
}

const strategies: { [name: string]: OccupationHierarchyStrategy } = {
  soc2018: new SOC2018Strategy(),
  nco2015: new NCO2015Strategy(),
};

export function getHierarchyStrategy(name: string): OccupationHierarchyStrategy {
  return strategies[name] || strategies.soc2018;
}
