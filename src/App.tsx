import { useMemo, useState } from "react";
import { ListingCard } from "./components/ListingCard";
import { ListingDetail } from "./components/ListingDetail";
import { useInventory } from "./hooks/useInventory";
import { getPostedVins } from "./lib/storage";
import type { ListingEntry } from "./types";

export default function App() {
  const {
    inventory,
    config,
    error,
    loading,
    refreshVehicles,
    refreshingNow,
  } = useInventory();
  const [search, setSearch] = useState("");
  const [hidePosted, setHidePosted] = useState(false);
  const [selected, setSelected] = useState<ListingEntry | null>(null);
  const [postedVins, setPostedVins] = useState(() => getPostedVins());

  const listings = useMemo(() => {
    if (!inventory) return [];
    let list = inventory.listings;
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (l) =>
          l.marketplace.title.toLowerCase().includes(q) ||
          l.id.toLowerCase().includes(q) ||
          l.vehicle.exterior_color?.toLowerCase().includes(q)
      );
    }
    if (hidePosted) {
      list = list.filter((l) => !postedVins.has(l.id));
    }
    return list;
  }, [inventory, search, hidePosted, postedVins]);

  if (loading) {
    return (
      <div className="app loading-screen">
        <p>Loading inventory…</p>
      </div>
    );
  }

  if (error || !inventory) {
    return (
      <div className="app error-screen">
        <h1>Metro Honda Marketplace</h1>
        <p>{error ?? "No data"}</p>
        <pre className="cmd-hint">npm run dev</pre>
        <p className="muted">
          Keep the API running so it can build and refresh the live cache.
        </p>
      </div>
    );
  }

  const phone = config?.seller?.phone;
  const contactMethod = config?.seller?.contact_method ?? "facebook";
  const postedCount = inventory.listings.filter((l) =>
    postedVins.has(l.id)
  ).length;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Metro Honda Marketplace</h1>
          <p className="subtitle">
            Jersey City · {inventory.count} vehicles
            {inventory.refreshing && (
              <span className="live"> · refreshing live inventory…</span>
            )}
            {contactMethod === "phone" && phone ? (
              <> · Leads to <strong>{phone}</strong></>
            ) : (
              <span className="live"> · Leads through Facebook messages</span>
            )}
            {inventory.lastError && (
              <span className="warn"> · refresh error: {inventory.lastError}</span>
            )}
          </p>
        </div>
        <div className="stats">
          <button
            type="button"
            className="refresh-btn"
            onClick={refreshVehicles}
            disabled={refreshingNow || inventory.refreshing}
          >
            {refreshingNow || inventory.refreshing ? "Refreshing…" : "Refresh vehicles"}
          </button>
          <span>{postedCount} posted</span>
          <span>{inventory.count - postedCount} remaining</span>
        </div>
      </header>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search year, model, color, VIN…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label>
          <input
            type="checkbox"
            checked={hidePosted}
            onChange={(e) => setHidePosted(e.target.checked)}
          />
          Hide posted
        </label>
      </div>

      <main className="grid">
        {listings.map((listing) => (
          <ListingCard
            key={listing.id}
            listing={listing}
            posted={postedVins.has(listing.id)}
            onSelect={() => setSelected(listing)}
          />
        ))}
      </main>

      {listings.length === 0 && (
        <p className="empty">No vehicles match your filters.</p>
      )}

      {selected && (
        <ListingDetail
          listing={selected}
          isPosted={postedVins.has(selected.id)}
          onPostedChange={(posted) => {
            const next = new Set(postedVins);
            if (posted) next.add(selected.id);
            else next.delete(selected.id);
            setPostedVins(next);
          }}
          onClose={() => setSelected(null)}
        />
      )}

      <footer className="footer">
        Updated {new Date(inventory.generatedAt).toLocaleString()} ·{" "}
        use Refresh vehicles to update inventory
      </footer>
    </div>
  );
}
