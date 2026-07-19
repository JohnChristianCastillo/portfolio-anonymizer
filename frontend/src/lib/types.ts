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

