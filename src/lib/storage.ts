const KEY = "metro-posted-vins";

export function getPostedVins(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as string[]);
  } catch {
    return new Set();
  }
}

export function setPosted(vin: string, posted: boolean): void {
  const set = getPostedVins();
  if (posted) set.add(vin);
  else set.delete(vin);
  localStorage.setItem(KEY, JSON.stringify([...set]));
}
