export const IATA_AIRLINE_MAP: { [key: string]: string } = {
  AC: 'Air Canada',
  AS: 'Alaska Airlines',
  B6: 'JetBlue',
  DL: 'Delta',
  UA: 'United',
  AA: 'American Airlines',
  NK: 'Spirit Airlines',
  F9: 'Frontier Airlines',
  HA: 'Hawaiian Airlines',
  WN: 'Southwest Airlines',
  AF: 'Air France',
  KL: 'KLM',
  VS: 'Virgin Atlantic',
  BA: 'British Airways',
  LH: 'Lufthansa',
  EK: 'Emirates',
  EY: 'Etihad Airways',
  QR: 'Qatar Airways',
  SQ: 'Singapore Airlines',
  AY: 'Finnair',
  IB: 'Iberia',
  TP: 'TAP Air Portugal',
  TK: 'Turkish Airlines',
  QF: 'Qantas',
  // Add more mappings as needed
};

export const getAirlineNameByCode = (code: string): string => {
  return IATA_AIRLINE_MAP[code] || code; // Return the code itself if not found
};
