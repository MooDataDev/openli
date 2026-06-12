export type Poi = {
  id: string;
  osmId: string | null;
  osmType: string | null;
  name: string;
  country: string;
  city: string;
  amenity: string;
  cuisine: string | null;
  cuisineRaw: string | null;
  cuisineTokens: string[];
  cuisinePrimary: string | null;
  cuisinePrimaryType: string;
  cuisineCountry: string | null;
  hasWebsite: boolean;
  hasMenuUrl: boolean;
  lat: number;
  lon: number;
};

export type PoiApiResponse = {
  files: string[];
  snapshotDate: string | null;
  pois: Poi[];
  countries: string[];
  cities: string[];
  amenities: string[];
  cuisines: string[];
  metrics: {
    totalPois: number;
    countriesCovered: number;
    citiesCovered: number;
    websiteCoverage: number;
    menuCoverage: number;
  };
  error?: string;
  detail?: string;
};

export type Filters = {
  country: string;
  city: string;
  amenity: string;
  cuisine: string;
  hasWebsite: boolean;
  hasMenuUrl: boolean;
};
