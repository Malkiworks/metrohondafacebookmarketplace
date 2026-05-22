export interface SiteConfig {
  seller: {
    display_name?: string;
    contact_method?: "facebook" | "phone";
    phone?: string;
    location_city?: string;
    location_state?: string;
  };
  dealer: {
    name?: string;
    city?: string;
    state?: string;
  };
  facebook?: {
    footer?: string;
  };
}

export interface VehicleRecord {
  vin: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  title: string;
  price: number;
  mileage: number;
  exterior_color: string;
  transmission: string;
  dealer_url: string;
  image_urls: string[];
}

export interface MarketplaceListing {
  title: string;
  price: number;
  price_formatted: string;
  description: string;
  location: { city: string; state: string };
}

export interface ListingEntry {
  id: string;
  vehicle: VehicleRecord;
  marketplace: MarketplaceListing;
  photos: string[];
  photoUrls: string[];
}

export interface InventoryData {
  generatedAt: string;
  count: number;
  listings: ListingEntry[];
  refreshing?: boolean;
  lastError?: string | null;
  lastRefreshStartedAt?: string | null;
  lastRefreshFinishedAt?: string | null;
  refreshCompleted?: number;
  refreshTotal?: number;
  refreshStage?: string;
}
