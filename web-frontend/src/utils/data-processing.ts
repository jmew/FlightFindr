import type { CompactFlightDeal, BookingOption, FlightSegment } from '../types';
import { getTimezoneOffset } from 'date-fns-tz';
import { differenceInMinutes, format } from 'date-fns';
import airportTimezone from 'airport-timezone';

const BOOKING_URLS: Record<string, string> = {
    "EY": "https://digital.etihad.com/book/search?{params}",
    "AS": "https://www.alaskaair.com/search/results?{params}",
    "VA": "https://book.virginaustralia.com/dx/VADX/#/flight-selection?{params}",
    "UA": "https://www.united.com/en/us/fsr/choose-flights?{params}",
    "BA": "https://www.britishairways.com/travel/redeem/execclub/_gf/en_us?{params}",
    "AC": "https://www.aircanada.com/aeroplan/redeem/availability/outbound?{params}",
    "KL": "https://www.klm.com/flight-search/search-results?{params}",
    "VS": "https://flywith.virginatlantic.com/gb/en/reward-flights-search/results/outbound?{params}",
    "AA": "https://www.aa.com/booking/search?{params}",
    "QF": "https://www.qantas.com/au/en/book-a-trip/flights.html?{params}",
    "DL": "https://www.delta.com"
};

const constructBookingUrl = (programCode: string, segments: any[]): string => {
    const baseUrl = BOOKING_URLS[programCode];
    if (!baseUrl) return '';

    const firstSegment = segments[0];
    const lastSegment = segments[segments.length - 1];
    const departureDate = new Date(firstSegment[3] * 1000);
    
    let params = '';
    switch (programCode) {
        case 'AC':
            params = `org0=${firstSegment[1]}&dest0=${lastSegment[2]}&departureDate0=${format(departureDate, 'yyyy-MM-dd')}&lang=en-US&t=O&ADT=1&YTH=0&CHD=0&INF=0&INS=0&marketCode=INT`;
            break;
        case 'UA':
            params = `f=${firstSegment[1]}&t=${lastSegment[2]}&d=${format(departureDate, 'yyyy-MM-dd')}&tt=1&at=1&sc=7&px=1&taxng=1&newHP=True&clm=7&st=bestmatches&tqp=A`;
            break;
        case 'AS':
            params = `O=${firstSegment[1]}&D=${lastSegment[2]}&OD=${format(departureDate, 'yyyy-MM-dd')}&A=1&C=0&L=0&RT=false&ShoppingMethod=onlineaward`;
            break;
        case 'B6':
             params = `from=${firstSegment[1]}&to=${lastSegment[2]}&depart=${format(departureDate, 'yyyy-MM-dd')}&isMultiCity=false&noOfRoute=1&as=1&ch=0&infants=0&sharedMarket=false&roundTripFaresFlag=false&usePoints=true&redemPoint=true`;
             break;
        case 'EY':
            params = `LANGUAGE=EN&CHANNEL=MOBILEWEB&B_LOCATION=${firstSegment[1]}&E_LOCATION=${lastSegment[2]}&TRIP_TYPE=O&CABIN=E&TRAVELERS=ADT&TRIP_FLOW_TYPE=AVAILABILITY&DATE_1=${format(departureDate, 'yyyyMMdd')}0000&WDS_ENABLE_MILES_TOGGLE=TRUE&FLOW=AWARD`;
            break;
        // Add other airline-specific parameter construction here
        default:
            // A generic fallback, might not work for all airlines
            params = `origin=${firstSegment[1]}&destination=${lastSegment[2]}&date=${format(departureDate, 'yyyy-MM-dd')}`;
            break;
    }

    return baseUrl.replace('{params}', params);
};

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
    
    // Convert timestamps back to ISO strings
    const departure_time = new Date(firstSegment[3] * 1000).toISOString();
    const arrival_time = new Date(lastSegment[4] * 1000).toISOString();
    const route = `${firstSegment[1]} -> ${lastSegment[2]}`;
    
    const stops = segments.slice(0, -1).map((seg: any) => seg[2]);
    const airlines = [...new Set(segments.map((seg: any) => seg[0].substring(0, 2)))];
    const flight_numbers = segments.map((seg: any) => seg[0]);

    const processedSegments: FlightSegment[] = segments.map((seg: any, i: number) => {
        const depAirport = seg[1];
        const arrAirport = seg[2];
        const depTimestamp = seg[3];
        const arrTimestamp = seg[4];

        const depTimeStr = new Date(depTimestamp * 1000).toISOString();
        const arrTimeStr = new Date(arrTimestamp * 1000).toISOString();

        const depTz = airportTimezone.find((a: any) => a.code === depAirport)?.timezone;
        const arrTz = airportTimezone.find((a: any) => a.code === arrAirport)?.timezone;

        let durationMinutes = 0;
        let arrivalDayDiff: number | undefined = undefined;
        let isOvernight = false;

        if (depTz && arrTz) {
            const depTimePre = new Date(depTimeStr);
            const arrTimePre = new Date(arrTimeStr);

            const depOffset = getTimezoneOffset(depTz, depTimePre);
            const arrOffset = getTimezoneOffset(arrTz, arrTimePre);

            const depTime = new Date(depTimePre.getTime() - depOffset);
            const arrTime = new Date(arrTimePre.getTime() - arrOffset);

            durationMinutes = differenceInMinutes(arrTime, depTime);
            
            const depDate = new Date(depTime.getFullYear(), depTime.getMonth(), depTime.getDate());
            const arrDate = new Date(arrTime.getFullYear(), arrTime.getMonth(), arrTime.getDate());
            const calDayDiff = (arrDate.getTime() - depDate.getTime()) / (1000 * 60 * 60 * 24);

            if (calDayDiff > 0) {
                arrivalDayDiff = calDayDiff;
                isOvernight = true;
            }
        }
        
        let layoverMinutes: number | undefined = undefined;
        if (i < segments.length - 1) {
            const nextDepTimestamp = segments[i+1][3];
            layoverMinutes = (nextDepTimestamp - arrTimestamp) / 60;
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
        const [program_code, transfer_partner_codes, cabin_deals] = opt;
        
        const program = programs[program_code] || program_code;
        const transfer_info = transfer_partner_codes.map((code: string) => banks[code] || code);

        const booking_url = constructBookingUrl(program_code, segments);

        const bookingOption: BookingOption = {
            program,
            booking_url,
            transfer_info,
        };

        for (const cabin_deal of cabin_deals) {
            const [cabin_code, points, tax, cash_price, cpp] = cabin_deal;

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
