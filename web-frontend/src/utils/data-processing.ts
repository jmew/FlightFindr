import type { CompactFlightDeal, BookingOption } from '../types';

export const decompressFlightData = (parsedResult: any): CompactFlightDeal[] => {
  if (!parsedResult.deals || !parsedResult.legend) {
    return [];
  }

  const { legend, deals } = parsedResult;
  const { cabin_codes, programs, banks, booking_urls } = legend;

  const decompressedDeals: CompactFlightDeal[] = deals.map((deal: any, index: number) => {
    const [segments, options, duration_minutes] = deal;

    const firstSegment = segments[0];
    const lastSegment = segments[segments.length - 1];
    const departure_time = firstSegment[3];
    const arrival_time = lastSegment[4];
    const route = `${firstSegment[1]} -> ${lastSegment[2]}`;
    
    const stops = segments.slice(0, -1).map((seg: any) => seg[2]);
    const airlines = [...new Set(segments.map((seg: any) => seg[0].substring(0, 2)))];
    const flight_numbers = segments.map((seg: any) => seg[0]);
    const layover_lengths = segments.slice(0, -1).map((seg: any) => seg[5]);
    
    let overnight_layover = false;
    for (let i = 0; i < segments.length - 1; i++) {
        const arr_time = new Date(segments[i][4]);
        const dep_time = new Date(segments[i+1][3]);
        if (arr_time.getDate() !== dep_time.getDate()) {
            overnight_layover = true;
            break;
        }
    }

    const bookingOptions: BookingOption[] = options.map((opt: any) => {
        const [program_code, transfer_partner_codes, url_params, cabin_deals] = opt;
        
        const program = programs[program_code] || program_code;
        const booking_url = booking_urls[program_code]?.replace('{params}', url_params) || '';
        const transfer_info = transfer_partner_codes.map((code: string) => banks[code] || code);

        const bookingOption: BookingOption = {
            program,
            booking_url,
            transfer_info,
        };

        for (const cabin_code in cabin_deals) {
            const [points, tax, cash_price, cpp] = cabin_deals[cabin_code];
            const cabin_name_full = cabin_codes[cabin_code] || cabin_code;
            const cabin_name = cabin_name_full.toLowerCase().replace(' ', '');
            
            let cabin_key: 'economy' | 'premium' | 'business' | 'first' = 'economy';
            if (cabin_name.startsWith('premium')) cabin_key = 'premium';
            else if (cabin_name.startsWith('business')) cabin_key = 'business';
            else if (cabin_name.startsWith('first')) cabin_key = 'first';

            bookingOption[cabin_key] = {
                points,
                fees: `$${tax}`,
                bonus: null,
                exact_cash_price: cash_price,
                exact_cpp: cpp,
            };
        }
        return bookingOption;
    });

    return {
        id: `${route}-${departure_time}-${index}`,
        route,
        departure_time,
        arrival_time,
        duration_minutes,
        stops,
        airlines,
        overnight_layover,
        layover_duration: layover_lengths.reduce((a: number, b: number) => a + b, 0),
        flight_numbers,
        layover_lengths,
        options: bookingOptions,
    };
  });

  return decompressedDeals;
}
