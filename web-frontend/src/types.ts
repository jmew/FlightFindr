export interface Tool {
  callId: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  error?: string;
}

export interface Message {
  sender: 'user' | 'bot';
  text: string;
  tools?: Tool[];
  flightData?: FlightDeal[];
}

interface AirportInfo {
  name: string;
  city: string;
  country: string;
  lat: number;
  lon: number;
}

interface CabinDeal {
  points: number;
  fees: string;
  booking_url: string;
  seats: number;
  transfer_info: {
    bank: string;
    bonus_percentage: number;
    bonus_end_date: string;
  }[];
  bonus: {
    bank: string;
    percentage: number;
    end_date: string;
  } | null;
  cheapest_cash_price?: number;
  cheapest_cpp?: number;
  exact_cash_price?: number | string;
  exact_cpp?: number | string;
}

export interface FlightDeal {
  id: string; // A unique identifier for the deal
  program: string;
  route: string;
  date: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  direct: boolean;
  flight_numbers: string[];
  origin_airport_info: AirportInfo;
  destination_airport_info: AirportInfo;
  source: string;
  stops?: string[];
  airlines?: string[];
  overnight_layover?: boolean;
  layover_duration?: number;

  economy?: CabinDeal;
  premium?: CabinDeal;
  business?: CabinDeal;
  first?: CabinDeal;

  // For frontend state management
  displayCabin: 'economy' | 'premium' | 'business' | 'first';
  isBestDeal?: boolean;
}
