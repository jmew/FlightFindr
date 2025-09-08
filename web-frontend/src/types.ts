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

interface CabinDeal {
  points: number;
  fees: string;
  seats: number;
  bonus: {
    bank: string;
    percentage: number;
    end_date: string;
  } | null;
  exact_cash_price?: number | string;
  exact_cpp?: number | string;
}

export interface FlightDeal {
  id: string;
  program: string;
  route: string;
  date: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  direct: boolean;
  flight_numbers: string[];
  stops?: string[];
  airlines?: string[];
  overnight_layover?: boolean;
  layover_duration?: number;
  booking_url: string;
  transfer_info: {
    bank: string;
    actual_points: number;
    points: number;
    bonus_percentage: number;
    bonus_end_date: number | null;
    code: string;
  }[];
  cash_flight_details?: any;

  economy?: CabinDeal;
  premium?: CabinDeal;
  business?: CabinDeal;
  first?: CabinDeal;

  // For frontend state management
  displayCabin: 'economy' | 'premium' | 'business' | 'first';
  isBestDeal?: boolean;
}