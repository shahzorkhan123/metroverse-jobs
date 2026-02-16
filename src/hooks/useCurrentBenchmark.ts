/**
 * Stub for Phase 1 - benchmark comparison is not yet implemented.
 * Returns a null-like benchmark so downstream components can render without errors.
 */

const useCurrentBenchmark = () => {
  return {
    benchmarkName: '',
    benchmarkNameShort: '',
    benchmark: '' as string,
  };
};

export default useCurrentBenchmark;
