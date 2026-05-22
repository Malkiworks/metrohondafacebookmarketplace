import { useEffect, useState } from "react";
import type { InventoryData, SiteConfig } from "../types";

const base = import.meta.env.BASE_URL;

export function useInventory() {
  const [inventory, setInventory] = useState<InventoryData | null>(null);
  const [config, setConfig] = useState<SiteConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshingNow, setRefreshingNow] = useState(false);

  async function loadFromApi(): Promise<boolean> {
    const api = await fetch("/api/inventory");
    if (!api.ok) return false;
    const inv = (await api.json()) as InventoryData;
    const cfg = await fetch("/api/config")
      .then((r) => (r.ok ? (r.json() as Promise<SiteConfig>) : null))
      .catch(() => null);
    setInventory(inv);
    setConfig(cfg ?? { seller: {}, dealer: {} });
    return true;
  }

  async function refreshVehicles() {
    setRefreshingNow(true);
    try {
      const response = await fetch("/api/refresh", { method: "POST" });
      if (!response.ok) throw new Error("Refresh failed");
      const inv = (await response.json()) as InventoryData;
      setInventory(inv);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshingNow(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        if (await loadFromApi()) {
          return;
        }
      } catch {
        // Static fallback for GitHub Pages / dist previews.
      }

      const [inv, cfg] = await Promise.all([
        fetch(`${base}data/inventory.json`).then((r) => {
          if (!r.ok) {
            throw new Error("No inventory cache yet. Keep npm run dev open; the API will build it.");
          }
          return r.json() as Promise<InventoryData>;
        }),
        fetch(`${base}site-config.json`).then((r) =>
          r.ok ? (r.json() as Promise<SiteConfig>) : ({} as SiteConfig)
        ),
      ]);
      if (!cancelled) {
        setInventory(inv);
        setConfig(cfg);
      }
    }

    load()
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    const interval = window.setInterval(() => {
      fetch("/api/inventory")
        .then((r) => (r.ok ? (r.json() as Promise<InventoryData>) : null))
        .then((inv) => {
          if (inv && !cancelled) setInventory(inv);
        })
        .catch(() => undefined);
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return { inventory, config, error, loading, refreshVehicles, refreshingNow };
}
