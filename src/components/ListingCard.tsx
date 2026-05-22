import type { ListingEntry } from "../types";

interface Props {
  listing: ListingEntry;
  posted: boolean;
  onSelect: () => void;
}

export function ListingCard({ listing, posted, onSelect }: Props) {
  const v = listing.vehicle;
  const thumb = listing.photos[0] ?? listing.photoUrls[0];

  return (
    <button type="button" className="card" onClick={onSelect}>
      <div className="card-image">
        {thumb ? (
          <img src={thumb} alt="" loading="lazy" />
        ) : (
          <span className="no-photo">No photo</span>
        )}
        {posted && <span className="badge posted">Posted</span>}
      </div>
      <div className="card-body">
        <h3>{listing.marketplace.title}</h3>
        <p className="price">{listing.marketplace.price_formatted}</p>
        <p className="meta">
          {v.mileage.toLocaleString()} mi · {v.exterior_color || "—"}
        </p>
      </div>
    </button>
  );
}
