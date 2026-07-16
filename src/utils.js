export function last(arr, n = 1) {
  if (!arr || arr.length < n) return null;
  return arr[arr.length - n];
}

export function avg(arr) {
  if (!arr || !arr.length) return 0;
  return arr.reduce((a, b) => a + Number(b || 0), 0) / arr.length;
}

export function pct(current, past) {
  if (!past || Number(past) === 0) return 0;
  return ((Number(current) - Number(past)) / Number(past)) * 100;
}

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function highest(arr) {
  const valid = arr.filter(x => Number.isFinite(Number(x))).map(Number);
  return valid.length ? Math.max(...valid) : 0;
}

export function lowest(arr) {
  const valid = arr.filter(x => Number.isFinite(Number(x))).map(Number);
  return valid.length ? Math.min(...valid) : 0;
}

export function round(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null;
  }

  return Number(Number(value).toFixed(digits));
}

export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
