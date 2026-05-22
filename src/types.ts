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
  body_style: string;
  exterior_color: string;
  interior_color: string;
  transmission: string;
  fuel_type: string;
  dealer_url: string;
  image_urls: string[];
  financing?: {
    monthly_payment?: number;
    term_months?: number;
    due_at_signing?: number;
    apr?: number;
    amount_financed?: number;
    selling_price?: number;
    provider?: string;
    credit_score?: number;
    vin?: string;
  };
}

export interface MarketplaceListing {
  title: string;
  price: number;
  price_formatted: string;
  description: string;
  location: { city: string; state: string };
  financing?: VehicleRecord["financing"];
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
