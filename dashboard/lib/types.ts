export type Poi = {
  id: string;
  osmId: string | null;
  osmType: string | null;
  name: string;
  continent: string;
  country: string;
  city: string;
  amenity: string;
  cuisine: string | null;
  cuisineRaw: string | null;
  cuisineTokens: string[];
  cuisinePrimary: string | null;
  cuisinePrimaryType: string;
  cuisineCountry: string | null;
  cuisineGroup: string | null;
  cuisineGroupKey: string | null;
  cuisineGroupType: string;
  hasWebsite: boolean;
  hasMenuUrl: boolean;
  websiteUrl: string | null;
  menuUrl: string | null;
  lat: number;
  lon: number;
};

export type PoiApiResponse = {
  files: string[];
  snapshotDate: string | null;
  pois: Poi[];
  continents: string[];
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
  continent: string;
  country: string;
  city: string;
  amenity: string;
  cuisine: string;
  hasWebsite: boolean;
  hasMenuUrl: boolean;
};
