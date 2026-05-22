import { useState } from "react";
import type { ListingEntry } from "../types";
import { copyText } from "../lib/clipboard";
import { buildCopyBlock, downloadPhotosZip } from "../lib/downloads";
import { setPosted } from "../lib/storage";

interface Props {
  listing: ListingEntry;
  isPosted: boolean;
  onPostedChange: (posted: boolean) => void;
  onClose: () => void;
}

const FB_CREATE =
  "https://www.facebook.com/marketplace/create/vehicle";

interface FieldCopyProps {
  label: string;
  value: string;
  onCopy: (label: string, value: string) => void;
  multiline?: boolean;
}

function FieldCopy({ label, value, onCopy, multiline = false }: FieldCopyProps) {
  return (
    <div className={multiline ? "field-copy field-copy-wide" : "field-copy"}>
      <div>
        <span>{label}</span>
        <strong>{value || "—"}</strong>
      </div>
      <button
        type="button"
        className="btn compact"
        onClick={() => onCopy(label, value)}
        disabled={!value}
      >
        Copy
      </button>
    </div>
  );
}

export function ListingDetail({
  listing,
  isPosted,
  onPostedChange,
  onClose,
}: Props) {
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const m = listing.marketplace;
  const v = listing.vehicle;
  const photos = listing.photos.length ? listing.photos : listing.photoUrls;
  const location = [m.location.city, m.location.state].filter(Boolean).join(", ");
  const priceValue = m.price ? String(m.price) : "";

  const flash = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  };

  const copy = async (label: string, text: string) => {
    const ok = await copyText(text);
    flash(ok ? `Copied ${label}` : "Copy failed");
  };

  const handleZip = async () => {
    setBusy(true);
    try {
      await downloadPhotosZip(listing, (msg) => flash(msg));
      flash("ZIP downloaded");
    } catch (e) {
      flash(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="detail-overlay" onClick={onClose} role="presentation">
      <div
        className="detail-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <header className="detail-header">
          <div>
            <h2>{m.title}</h2>
            <p className="detail-price">{m.price_formatted}</p>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="detail-gallery">
          {photos.slice(0, 12).map((src, i) => (
            <img key={src + i} src={src} alt="" loading="lazy" />
          ))}
        </div>

        <section className="marketplace-fields">
          <div className="section-title">
            <h3>Marketplace form fields</h3>
            <p>Copy these into the Facebook vehicle listing form.</p>
          </div>
          <div className="field-grid">
            <FieldCopy label="Vehicle type" value="Car/truck" onCopy={copy} />
            <FieldCopy label="Location" value={location} onCopy={copy} />
            <FieldCopy label="Year" value={String(v.year || "")} onCopy={copy} />
            <FieldCopy label="Make" value={v.make} onCopy={copy} />
            <FieldCopy label="Model" value={v.model} onCopy={copy} />
            <FieldCopy label="Price" value={priceValue} onCopy={copy} />
            <FieldCopy
              label="Description"
              value={m.description}
              onCopy={copy}
              multiline
            />
          </div>
        </section>

        <div className="detail-actions">
          <button
            type="button"
            className="btn primary"
            onClick={() => copy("title", m.title)}
          >
            Copy title
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => copy("price", String(m.price))}
          >
            Copy price
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => copy("description", m.description)}
          >
            Copy description
          </button>
          <button
            type="button"
            className="btn accent"
            onClick={() => copy("full listing", buildCopyBlock(listing))}
          >
            Copy all
          </button>
          <button
            type="button"
            className="btn"
            onClick={handleZip}
            disabled={busy}
          >
            {busy ? "Downloading…" : "Download photos (ZIP)"}
          </button>
          <a
            className="btn fb"
            href={FB_CREATE}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Marketplace →
          </a>
        </div>

        <label className="posted-toggle">
          <input
            type="checkbox"
            checked={isPosted}
            onChange={(e) => {
              setPosted(listing.id, e.target.checked);
              onPostedChange(e.target.checked);
            }}
          />
          Mark as posted on Facebook
        </label>

        <section className="detail-description">
          <h3>Description preview</h3>
          <pre>{m.description}</pre>
        </section>

        <p className="detail-hint">
          Workflow: Open Marketplace → fill Vehicle type, Photos, Location, Year,
          Make, Model, Price, Description → publish.
        </p>

        {toast && <div className="toast">{toast}</div>}
      </div>
    </div>
  );
}
