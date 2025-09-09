export const IATA_AIRLINE_MAP: { [key: string]: string } = {
  // North America
  AC: 'Air Canada',
  AS: 'Alaska',
  AA: 'American',
  DL: 'Delta Air Lines',
  F9: 'Frontier',
  HA: 'Hawaiian',
  B6: 'JetBlue',
  NK: 'Spirit',
  WN: 'Southwest',
  UA: 'United',
  WS: 'WestJet',
  AM: 'Aeromexico',

  // Europe
  AF: 'Air France',
  KL: 'KLM Royal Dutch',
  VS: 'Virgin Atlantic',
  BA: 'British Airways',
  LH: 'Lufthansa',
  AY: 'Finnair',
  IB: 'Iberia',
  TP: 'TAP Air Portugal',
  TK: 'Turkish',
  LX: 'Swiss International Air Lines',
  OS: 'Austrian',
  SN: 'Brussels Airlines',
  SK: 'Scandinavian Airlines',
  EI: 'Aer Lingus',
  AZ: 'ITA Airways',
  FR: 'Ryanair',
  U2: 'easyJet',
  SU: 'Aeroflot',

  // Asia
  SQ: 'Singapore Airlines',
  NH: 'All Nippon Airways',
  JL: 'Japan Airlines',
  CX: 'Cathay Pacific',
  BR: 'EVA Air',
  CI: 'China Airlines',
  KE: 'Korean Air',
  OZ: 'Asiana',
  CA: 'Air China',
  MU: 'China Eastern',
  CZ: 'China Southern',
  HU: 'Hainan Airlines',
  TG: 'Thai Airways',
  MH: 'Malaysia Airlines',
  GA: 'Garuda Indonesia',
  VN: 'Vietnam Airlines',
  PR: 'Philippine Airlines',
  AI: 'Air India',

  // Middle East
  EK: 'Emirates',
  EY: 'Etihad Airways',
  QR: 'Qatar Airways',
  SV: 'Saudia',
  LY: 'El Al',

  // Oceania
  QF: 'Qantas',
  NZ: 'Air New Zealand',
  VA: 'Virgin Australia',

  // South America
  LA: 'LATAM',
  AV: 'Avianca',
  AR: 'Aerolineas Argentinas',
  G3: 'GOL Linhas Aéreas',

  // Africa
  ET: 'Ethiopian Airlines',
  SA: 'South African Airways',
  MS: 'EgyptAir',
  KQ: 'Kenya Airways',
  AT: 'Royal Air Maroc',
};

export const getAirlineNameByCode = (code: string): string => {
  return IATA_AIRLINE_MAP[code] || code; // Return the code itself if not found
};
