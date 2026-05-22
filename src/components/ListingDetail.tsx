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

function money(value?: number): string {
  return typeof value === "number" && value > 0
    ? `$${Math.round(value).toLocaleString()}`
    : "";
}

function marketplaceModel(listing: ListingEntry): string {
  return [listing.vehicle.model, listing.vehicle.trim].filter(Boolean).join(" ");
}

function marketplaceTransmission(value: string): string {
  const text = value.toLowerCase();
  if (!value) return "";
  if (text.includes("manual")) return "Manual transmission";
  return "Automatic transmission";
}

function marketplaceFuelType(value: string): string {
  const text = value.toLowerCase();
  if (text.includes("hybrid")) return "Hybrid";
  if (text.includes("electric")) return "Electric";
  if (text.includes("diesel")) return "Diesel";
  if (text.includes("gas")) return "Gasoline";
  return value;
}

function marketplaceBodyStyle(listing: ListingEntry): string {
  const body = listing.vehicle.body_style;
  if (body) return body.replace(/^4D\s+/i, "").trim();

  const title = listing.marketplace.title.toLowerCase();
  if (title.includes("cr-v") || title.includes("hr-v") || title.includes("pilot")) {
    return "SUV";
  }
  if (title.includes("odyssey")) return "Minivan";
  if (title.includes("ridgeline")) return "Truck";
  if (title.includes("civic") || title.includes("accord")) return "Sedan";
  return "";
}

function buildFinanceText(listing: ListingEntry): string {
  const finance = listing.marketplace.financing ?? listing.vehicle.financing;
  if (!finance?.monthly_payment) return "";

  const monthly = money(finance.monthly_payment);
  const due = money(finance.due_at_signing);
  const amountFinanced = money(finance.amount_financed);
  const sellingPrice = money(finance.selling_price || listing.marketplace.price);
  const term = finance.term_months;
  const apr = finance.apr;
  const creditScore = finance.credit_score ?? 800;
  const provider = finance.provider || "Honda Financial Services";
  const vin = finance.vin || listing.vehicle.vin;

  const details = [
    `Estimated payment based on ${creditScore} credit score`,
    term ? `${term} month term` : "",
    apr ? `at ${apr}% APR` : "",
  ]
    .filter(Boolean)
    .join(", ");

  const priceDetails = [
    sellingPrice ? `Payment based on a selling price of ${sellingPrice}` : "",
    due ? `a ${due} down payment toward loan` : "",
    amountFinanced ? `for a final amount financed of ${amountFinanced}` : "",
  ]
    .filter(Boolean)
    .join(", ");

  return [
    "FINANCE",
    `${monthly}/month`,
    `${term ? `${term} Months` : ""}${due ? `/${due} Due at Signing` : ""}`,
    `${details}, financed through ${provider}. Not all buyers will qualify for these terms and a final credit report will be required to verify eligibility.`,
    `${priceDetails}. Excludes tax, title and licensing.${vin ? ` Based on VIN# ${vin}.` : ""}`,
  ]
    .filter(Boolean)
    .join("\n");
}

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
  const location = m.location.city || [m.location.city, m.location.state].filter(Boolean).join(", ");
  const priceValue = m.price ? String(m.price) : "";
  const monthlyValue = listing.marketplace.financing?.monthly_payment
    ? String(listing.marketplace.financing.monthly_payment)
    : "";
  const financeText = buildFinanceText(listing);

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
            <FieldCopy label="Vehicle type" value="Car/van" onCopy={copy} />
            <FieldCopy label="Location" value={location} onCopy={copy} />
            <FieldCopy label="Year" value={String(v.year || "")} onCopy={copy} />
            <FieldCopy label="Make" value={v.make} onCopy={copy} />
            <FieldCopy label="Model" value={marketplaceModel(listing)} onCopy={copy} />
            <FieldCopy label="Mileage" value={v.mileage ? String(v.mileage) : ""} onCopy={copy} />
            <FieldCopy label="Price" value={priceValue} onCopy={copy} />
            {monthlyValue && (
              <FieldCopy label="Monthly payment" value={monthlyValue} onCopy={copy} />
            )}
            <FieldCopy label="Body style" value={marketplaceBodyStyle(listing)} onCopy={copy} />
            <FieldCopy label="Exterior colour" value={v.exterior_color} onCopy={copy} />
            <FieldCopy label="Interior colour" value={v.interior_color} onCopy={copy} />
            <FieldCopy label="Clean title" value="Yes" onCopy={copy} />
            <FieldCopy label="No significant damage/problems" value="Yes" onCopy={copy} />
            <FieldCopy label="Vehicle condition" value="Very good" onCopy={copy} />
            <FieldCopy label="Fuel type" value={marketplaceFuelType(v.fuel_type)} onCopy={copy} />
            <FieldCopy
              label="Transmission"
              value={marketplaceTransmission(v.transmission)}
              onCopy={copy}
            />
            {financeText && (
              <FieldCopy
                label="Finance"
                value={financeText}
                onCopy={copy}
                multiline
              />
            )}
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
