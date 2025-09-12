import type { CompactFlightDeal, BookingOption, FlightSegment } from '../types';
import { toZonedTime, getTimezoneOffset } from 'date-fns-tz';
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

        const depTz = airportTimezone.find((a: any) => a.code === depAirport)?.timezone;
        const arrTz = airportTimezone.find((a: any) => a.code === arrAirport)?.timezone;

        let durationMinutes = 0;
        let arrivalDayDiff: number | undefined = undefined;
        let isOvernight = false;

        if (depTz && arrTz) {
            const depTimePre = new Date(depTimeStr + 'Z');
            const arrTimePre = new Date(arrTimeStr + 'Z');

            const depOffset = getTimezoneOffset(depTz, depTimePre);
            const arrOffset = getTimezoneOffset(arrTz, arrTimePre);

            const depTime = new Date(depTimePre.getTime() - depOffset);
            const arrTime = new Date(arrTimePre.getTime() - arrOffset);

            durationMinutes = differenceInMinutes(arrTime, depTime);

            const depDate = new Date(depTimeStr.substring(0, 10) + 'T00:00:00Z');
            const arrDate = new Date(arrTimeStr.substring(0, 10) + 'T00:00:00Z');
            const calDayDiff = (arrDate.getTime() - depDate.getTime()) / (1000 * 60 * 60 * 24);

            if (calDayDiff > 0) {
                arrivalDayDiff = calDayDiff;
                isOvernight = true;
            }
        }
        
        let layoverMinutes: number | undefined = undefined;
        if (i < segments.length - 1) {
            const nextDepTimeStr = segments[i+1][3];
            if (arrTz) {
                const arrTimePre = new Date(arrTimeStr + 'Z');
                const nextDepTimePre = new Date(nextDepTimeStr + 'Z');
                const arrOffset = getTimezoneOffset(arrTz, arrTimePre);
                const nextDepOffset = getTimezoneOffset(arrTz, nextDepTimePre);

                const arrTime = new Date(arrTimePre.getTime() - arrOffset);
                const nextDepTime = new Date(nextDepTimePre.getTime() - nextDepOffset);
                
                layoverMinutes = differenceInMinutes(nextDepTime, arrTime);
            }
        }

        return {
            airlineCode: seg[0].substring(0, 2),
            flightNumber: seg[0],
            departureAirport: depAirport,
            arrivalAirport: arrAirport,
            departureTime: depTimeStr,
            arrivalTime: arrTimeStr,
            durationMinutes,
            layoverMinutes,
            arrivalDayDiff,
            isOvernight,
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
