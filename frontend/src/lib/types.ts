export type Entity = {
  start: number;
  end: number;
  label: string;
  text: string;
};

export type AnonymizeResult = {
  config: string;
  anonymized: string;
  entities: Entity[];
  entity_counts: Record<string, number>;
  original: string | null;
};

export type DetectorConfig = {
  key: string;
  label: string;
  detectors: string[];
  default: boolean;
};

export type GatewayQuota = {
  app_slug: string;
  tier: string;
  limit: number | null;
  used: number;
  remaining: number | null;
  banned: boolean;
  location: {
    city: string | null;
    postal_code: string | null;
    region: string | null;
    country: string | null;
  } | null;
};

export type GatewayStatus = {
  maintenance: boolean;
  active: {
    anonymous: number;
    invited: number;
    total: number;
  };
  capacity: {
    anonymous: number;
    invited: number;
    invite_link_max_concurrent: number;
  };
  queue: {
    anonymous: number;
    invited: number;
  };
  demo_quota: GatewayQuota | null;
};
