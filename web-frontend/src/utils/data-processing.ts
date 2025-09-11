import type { CompactFlightDeal, BookingOption, FlightSegment } from '../types';
import { toZonedTime } from 'date-fns-tz';
import { differenceInMinutes, differenceInCalendarDays } from 'date-fns';
import airportTimezone from 'airport-timezone';

export const decompressFlightData = (parsedResult: any): CompactFlightDeal[] => {
  if (!parsedResult.deals || !parsedResult.legend) {
    return [];
  }

  const { legend, deals } = parsedResult;
  const { cabin_codes, programs, banks } = legend;

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

    const processedSegments: FlightSegment[] = segments.map((seg: any, i: number) => {
        const depAirport = seg[1];
        const arrAirport = seg[2];
        const depTimeStr = seg[3];
        const arrTimeStr = seg[4];

        const depTzEntry = airportTimezone.find((airport: any) => airport.code === depAirport);
        const arrTzEntry = airportTimezone.find((airport: any) => airport.code === arrAirport);
        const depTz = depTzEntry?.timezone;
        const arrTz = arrTzEntry?.timezone;

        let duration = 0;
        let dayDiff: number | undefined = undefined;
        let isOvernight = false;

        if (depTz && arrTz) {
            const depTime = toZonedTime(depTimeStr, depTz);
            const arrTime = toZonedTime(arrTimeStr, arrTz);
            
            duration = differenceInMinutes(arrTime, depTime);
            const calDayDiff = differenceInCalendarDays(arrTime, depTime);
            if (calDayDiff > 0) {
                dayDiff = calDayDiff;
                isOvernight = true;
            }
        } else {
            // Fallback for airports not in the library
            const depTime = new Date(depTimeStr);
            const arrTime = new Date(arrTimeStr);
            duration = (arrTime.getTime() - depTime.getTime()) / (1000 * 60);
            const depDate = new Date(depTime.getFullYear(), depTime.getMonth(), depTime.getDate());
            const arrDate = new Date(arrTime.getFullYear(), arrTime.getMonth(), arrTime.getDate());
            const calDayDiff = (arrDate.getTime() - depDate.getTime()) / (1000 * 60 * 60 * 24);
            if (calDayDiff > 0) {
                dayDiff = calDayDiff;
                isOvernight = true;
            }
        }
        
        let layoverMins: number | undefined = undefined;
        if (i < segments.length - 1) {
            const nextDepTime = new Date(segments[i+1][3]);
            const arrTime = new Date(arrTimeStr);
            layoverMins = (nextDepTime.getTime() - arrTime.getTime()) / (1000 * 60);
        }

        return {
            airlineCode: seg[0].substring(0, 2),
            flightNumber: seg[0],
            departureAirport: depAirport,
            arrivalAirport: arrAirport,
            departureTime: depTimeStr,
            arrivalTime: arrTimeStr,
            durationMinutes: duration,
            layoverMinutes: layoverMins,
            arrivalDayDiff: dayDiff,
            isOvernight: isOvernight,
        };
    });
    
    const overnight_layover = processedSegments.some(seg => seg.isOvernight);

    const bookingOptions: BookingOption[] = options.map((opt: any) => {
        const [program_code, transfer_partner_codes, booking_url, cabin_deals] = opt;
        
        const program = programs[program_code] || program_code;
        const transfer_info = transfer_partner_codes.map((code: string) => banks[code] || code);

        const bookingOption: BookingOption = {
            program,
            booking_url,
            transfer_info,
        };

        for (const cabin_code in cabin_deals) {
            const dealData = cabin_deals[cabin_code];
            const [points, tax] = dealData;
            const cash_price = dealData.length > 2 ? dealData[2] : undefined;
            const cpp = dealData.length > 3 ? dealData[3] : undefined;

            const cabin_name_full = cabin_codes[cabin_code] || cabin_code;
            const cabin_name = cabin_name_full.toLowerCase().replace(' ', '');
            
            let cabin_key: 'economy' | 'premium' | 'business' | 'first' = 'economy';
            if (cabin_name.startsWith('premium')) cabin_key = 'premium';
            else if (cabin_name.startsWith('business')) cabin_key = 'business';
            else if (cabin_name.startsWith('first')) cabin_key = 'first';

            bookingOption[cabin_key] = {
                points,
                fees: `${tax}`,
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
        flight_numbers,
        options: bookingOptions,
        segments: processedSegments,
    };
  });

  return decompressedDeals;
}
