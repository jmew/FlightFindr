import type { FlightDealRow } from './components/FlightDealsTable';

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
  flightData?: FlightDealRow[];
}

export interface Deal {
  [key: string]: any;
  date: string;
  program: string;
  route: string;
  departure_time: string;
  arrival_time: string;
  flight_numbers: string[];
  economy?: { points: number; fees: string; booking_url: string; transfer_info: any[], bonus: any };
  business?: { points: number; fees: string; booking_url: string; transfer_info: any[], bonus: any };
  first?: { points: number; fees: string; booking_url: string; transfer_info: any[], bonus: any };
  premium?: { points: number; fees: string; booking_url: string; transfer_info: any[], bonus: any };
}
