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
  flightData?: CompactFlightDeal[];
}

export interface CabinDeal {
  points: number;
  fees: string;
  bonus?: {
    bank: string;
    percentage: number;
    end_date: string;
  } | null;
  exact_cash_price?: number | string;
  exact_cpp?: number | string;
}

export interface BookingOption {
  program: string;
  booking_url: string;
  transfer_info: string[];
  economy?: CabinDeal;
  premium?: CabinDeal;
  business?: CabinDeal;
  first?: CabinDeal;
}

export interface CompactFlightDeal {
  id: string;
  route: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  flight_numbers: string[];
  stops?: string[];
  airlines?: string[];
  overnight_layover?: boolean;
  layover_duration?: number;
  layover_lengths?: number[];
  options: BookingOption[];
}