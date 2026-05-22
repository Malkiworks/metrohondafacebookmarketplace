import JSZip from "jszip";
import type { ListingEntry } from "../types";

async function blobFromUrl(url: string): Promise<Blob | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.blob();
  } catch {
    return null;
  }
}

export async function downloadPhotosZip(
  listing: ListingEntry,
  onProgress?: (msg: string) => void
): Promise<void> {
  const zip = new JSZip();
  const folder = zip.folder(listing.id) ?? zip;
  let added = 0;

  const local = listing.photos ?? [];
  if (local.length > 0) {
    onProgress?.("Packing local photos…");
    for (let i = 0; i < local.length; i++) {
      const blob = await blobFromUrl(local[i]);
      if (!blob) continue;
      const ext = local[i].match(/\.(jpe?g|png|webp)$/i)?.[0] ?? ".jpg";
      folder.file(`${String(i + 1).padStart(2, "0")}${ext}`, blob);
      added++;
    }
  }

  if (added === 0 && listing.photoUrls?.length) {
    onProgress?.("Fetching from CDN (may be slow)…");
    for (let i = 0; i < listing.photoUrls.length; i++) {
      const blob = await blobFromUrl(listing.photoUrls[i]);
      if (!blob) continue;
      folder.file(`${String(i + 1).padStart(2, "0")}.jpg`, blob);
      added++;
    }
  }

  if (added === 0) {
    throw new Error(
      "No photos could be downloaded. Run npm run data to cache photos locally."
    );
  }

  onProgress?.("Creating ZIP…");
  const content = await zip.generateAsync({ type: "blob" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(content);
  a.download = `${listing.id}-photos.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function buildCopyBlock(listing: ListingEntry): string {
  const m = listing.marketplace;
  return `TITLE:
${m.title}

PRICE:
${m.price_formatted}

LOCATION:
${m.location.city}, ${m.location.state}

DESCRIPTION:
${m.description}`;
}
