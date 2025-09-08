import React, { useMemo, useState, useRef, useEffect } from 'react';
import {
  FiStar,
  FiChevronDown,
  FiChevronUp,
  FiAlertTriangle,
} from 'react-icons/fi';
import DealFilters from '../DealFilters';
import Logo from '../Logo';
import type { FlightDeal, SlimCashFlightDetails } from '../../types';
import { formatDuration, formatFlightTimes } from '../../utils/formatters';
import { getAirlineNameByCode } from '../../utils/airlineMappings';

const CashFlightDetails = ({ details }: { details: SlimCashFlightDetails }) => {
  if (!details) return null;

  return (
    <div className="cash-flight-details" style={{ marginTop: '16px' }}>
        <div className="segment-details" style={{ marginBottom: '12px' }}>
            <p style={{ margin: '4px 0 0 10px', color: 'var(--gem-sys-color--on-surface-variant)'}}>
              {details.name} {details.flight_number}
            </p>
            {details.layover_details && (
              <div className="layover-details" style={{ marginLeft: '10px', padding: '8px', color: 'var(--gem-sys-color--on-surface-variant)'}}>
                Layover: {details.layover_details}
              </div>
            )}
        </div>
    </div>
  );
};

interface DealRowProps {
  deal: FlightDeal;
  cabin: 'economy' | 'premium' | 'business' | 'first';
  showDate: boolean;
  hasCashPrice: boolean;
}

const DealRow: React.FC<DealRowProps> = ({ deal, cabin, showDate, hasCashPrice }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const cabinData = deal[cabin];

  if (!cabinData) return null;

  const { points, fees, bonus } = cabinData;
  const { booking_url, transfer_info, cash_flight_details } = deal;

  const transferPartners =
    transfer_info?.map((t: { bank: string }) => t.bank) || [];
  const [origin, destination] = deal.route.split(' -> ');
  const { departureTime, arrivalTime, isNextDay } = formatFlightTimes(
    deal.departure_time,
    deal.arrival_time,
  );

  const gridStyle = {
    gridTemplateColumns: hasCashPrice
      ? '0.5fr 2.2fr 1fr 1fr 1fr 0.1fr'
      : '0.5fr 2.2fr 1fr 1fr 0.1fr',
  };

  const airlineName = deal.airlines && deal.airlines.length === 1 ? getAirlineNameByCode(deal.airlines[0]) : 'Mixed';

  const getDisplayName = (name: string) => {
    if (name === 'American Airlines') return 'American';
    if (name === 'Alaska Airlines') return 'Alaska';
    return name;
  };

  const displayName = getDisplayName(airlineName);

  const routeString =
    deal.direct
      ? `${origin} → ${destination}`
      : `${origin} → ${deal.stops.join(' → ')} → ${destination}`;

  const getCppColor = (cpp: number | string) => {
    if (typeof cpp === 'string') return 'inherit';
    if (cpp > 1.2) return '#81c995';
    if (cpp < 1) return '#f28b82';
    return 'inherit';
  };

  return (
    <div className="deal-row-container">
      <div className="deal-row" style={gridStyle} onClick={() => setIsExpanded(!isExpanded)}>
        <div className="section airline-info">
          <Logo
            type="airline"
            code={
              deal.airlines && deal.airlines.length === 1
                ? deal.airlines[0]
                : undefined
            }
            name={displayName}
          />
          <span className="airline-name">{displayName}</span>
        </div>
        <div className="section time-info">
          {showDate && (
            <div style={{ fontSize: '0.8em', fontFamily: 'roboto', color: 'var(--gem-sys-color--on-surface-variant)' }}>
              {new Date(deal.date.replace(/-/g, '/')).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </div>
          )}
          <span className="time">
            {departureTime} → {arrivalTime}
            {isNextDay && <sup>+1</sup>}
          </span>
          <div className="route">{routeString}</div>
        </div>
        <div className="section duration-info">
          <div className="duration">
            {formatDuration(deal.duration_minutes)}
          </div>
          <div className="stops">
            {deal.direct
              ? 'Nonstop'
              : `${(deal.stops || []).length} Stop${(deal.stops || []).length !== 1 ? 's' : ''}`}
            {!deal.direct && deal.overnight_layover && (
              <span
                title="Includes an overnight layover"
                className="overnight-warning"
              >
                <FiAlertTriangle />
              </span>
            )}
          </div>
        </div>
        <div className="section points-info">
          <div className="points-value">
            {bonus && (
              <span
                title={`Transfer Bonus: ${bonus.percentage}% from ${bonus.bank}`}
                className="transfer-bonus-star"
              >
                <FiStar />
              </span>
            )}
            {deal.program.split(' ')[0].toLowerCase() !== airlineName.split(' ')[0].toLowerCase() && (
              <div className="tooltip-container">
                <span style={{ color: 'var(--gem-sys-color--primary)' }}>*</span>
                <span className="tooltip-text">Book with {deal.program}</span>
              </div>
            )}
            {points.toLocaleString()}<span style={{ fontSize: '0.5em' }}> pts</span>
          </div>
          <div className="fees">+ {fees}</div>
        </div>
        {hasCashPrice &&
          (cabinData.exact_cpp && cabinData.exact_cpp !== 'N/A' ? (
            <div className="section cpp-info">
              <div
                className="points-value"
                style={{ color: getCppColor(cabinData.exact_cpp) }}
              >
                {`${cabinData.exact_cpp}¢`} / pt
              </div>
              <div className="fees">
                (Cash) ${cabinData.exact_cash_price}
              </div>
            </div>
          ) : (
            <div />
          ))}
        <div className="section details-toggle">
          {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
        </div>
      </div>
      {isExpanded && (
        <div className="deal-row-expanded-details">
          <div className="detail-item">
            <strong>Flight Numbers:</strong> {deal.flight_numbers.join(', ')}
          </div>
          {bonus && (
            <div className="detail-item transfer-bonus-details">
              <strong>✨ {bonus.percentage}% Transfer Bonus</strong> from{' '}
              {bonus.bank} (ends{' '}
              {new Date(Number(bonus.end_date) * 1000).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
              })}
              )
            </div>
          )}
          <div className="detail-item transfers">
            <strong>Transfer From:</strong>
            <div className="transfer-partners">
                {transferPartners.map((partner: string) => (
                  <Logo key={partner} type="bank" name={partner} />
                ))}
              </div>
            </div>
            {cash_flight_details && (
              <CashFlightDetails details={cash_flight_details} />
            )}
            <a
            href={booking_url}
            target="_blank"
            rel="noopener noreferrer"
            className="deal-card-book-btn"
          >
            Book on {deal.program}
          </a>
        </div>
      )}
    </div>
  );
};

interface FlightDealsTableProps {
  deals: FlightDeal[];
}

interface ActiveFilters {
  cabinClasses: string[];
  airlinePrograms: string[];
  stops: string[];
  maxPoints: number | null;
}

const calculateTopFlightScore = (deal: FlightDeal, cheapestPrice: number, shortestDuration: number) => {
  const weights = {
    price: 40,
    duration: 30,
    stops: 20,
    time: 10,
  };

  const cabinData = deal[deal.displayCabin as keyof FlightDeal] as any;
  if (!cabinData) return Infinity;

  const priceScore = (cabinData.points || 0) / cheapestPrice;
  const durationScore = deal.duration_minutes / shortestDuration;

  let stopsPenalty = 0;
  const stopCount = (deal.stops || []).length;
  if (stopCount === 1) {
    stopsPenalty = 1;
  } else if (stopCount >= 2) {
    stopsPenalty = 2.5;
  }
  if ((deal.layover_duration || 0) > 240) { // 4 hours
    stopsPenalty += 0.5;
  }

  let timePenalty = 0;
  const departureHour = new Date(deal.departure_time).getHours();
  const arrivalHour = new Date(deal.arrival_time).getHours();
  if (departureHour < 8 || departureHour > 20) {
    timePenalty += 0.5;
  }
  if (arrivalHour < 8 || arrivalHour > 20) {
    timePenalty += 0.5;
  }

  return (
    weights.price * priceScore +
    weights.duration * durationScore +
    weights.stops * stopsPenalty +
    weights.time * timePenalty
  );
};

const FlightDealsTable: React.FC<FlightDealsTableProps> = ({ deals }) => {
  const [filters, setFilters] = useState<ActiveFilters>({
    cabinClasses: ['Economy'],
    airlinePrograms: [],
    stops: [],
    maxPoints: null,
  });
  const [sortBy, setSortBy] = useState('top');
  const [isStuck, setIsStuck] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsStuck(entry.intersectionRatio < 1);
      },
      { threshold: [1] },
    );

    if (sentinelRef.current) {
      observer.observe(sentinelRef.current);
    }

    return () => {
      if (sentinelRef.current) {
        observer.unobserve(sentinelRef.current);
      }
    };
  }, []);

  const showDates = useMemo(() => {
    if (deals.length <= 1) return false;
    const firstDate = deals[0].date;
    return !deals.every(deal => deal.date === firstDate);
  }, [deals]);

  

  const { availablePrograms, minPoints, maxPoints, shortestDuration, availableCabins, availableStops } = useMemo(() => {
    const programs = new Set<string>();
    const cabins = new Set<string>();
    const stops = new Set<number>();
    let min = Infinity;
    let max = 0;
    let shortest = Infinity;

    deals.forEach(deal => {
      programs.add(deal.program);
      if (deal.duration_minutes < shortest) {
        shortest = deal.duration_minutes;
      }
      stops.add((deal.stops || []).length);
      ['economy', 'premium', 'business', 'first'].forEach(cabin => {
        const cabinData = deal[cabin as keyof FlightDeal] as any;
        if (cabinData && cabinData.points) {
          cabins.add(cabin.charAt(0).toUpperCase() + cabin.slice(1));
          if (cabinData.points < min) min = cabinData.points;
          if (cabinData.points > max) max = cabinData.points;
        }
      });
    });

    const availableStops: string[] = [];
    if (stops.has(0)) availableStops.push('Nonstop');
    if (stops.has(1)) availableStops.push('1 Stop');
    if ([...stops].some(count => count >= 2)) availableStops.push('2+ Stops');

    return {
      availablePrograms: Array.from(programs).sort(),
      minPoints: min === Infinity ? 0 : min,
      maxPoints: max === 0 ? 100000 : max,
      shortestDuration: shortest === Infinity ? 1 : shortest,
      availableCabins: Array.from(cabins),
      availableStops,
    };
  }, [deals]);

  const dealsWithCabin = useMemo(() => {
    const newDeals: (FlightDeal & { displayCabin: string })[] = [];
    deals.forEach(deal => {
      ['economy', 'premium', 'business', 'first'].forEach(cabin => {
        const cabinKey = cabin as keyof FlightDeal;
        if (deal[cabinKey]) {
          newDeals.push({
            ...deal,
            id: `${deal.id}-${cabin}`,
            displayCabin: cabin,
          });
        }
      });
    });
    return newDeals;
  }, [deals]);

  const filteredDeals = useMemo(() => {
    return dealsWithCabin.filter((deal) => {
      const { cabinClasses, airlinePrograms, stops, maxPoints } = filters;
      
      if (
        cabinClasses.length > 0 &&
        !cabinClasses.some((c) => deal.displayCabin.startsWith(c.toLowerCase()))
      ) {
        return false;
      }
      
      if (
        airlinePrograms.length > 0 &&
        !airlinePrograms.includes(deal.program)
      ) {
        return false;
      }
      
      if (stops.length > 0) {
        const stopCount = (deal.stops || []).length;
        
        const stopConditions = {
          'Nonstop': stopCount === 0,
          '1 Stop': stopCount === 1,
          '2+ Stops': stopCount >= 2,
        };

        const matches = stops.some(stop => stopConditions[stop as keyof typeof stopConditions]);

        if (!matches) {
          return false;
        }
      }

      if (maxPoints !== null) {
        const cabinData = deal[deal.displayCabin as keyof FlightDeal] as any;
        if (!cabinData || cabinData.points > maxPoints) {
          return false;
        }
      }

      return true;
    });
  }, [dealsWithCabin, filters]);

  const sortedDeals = useMemo(() => {
    const dealsWithScores = filteredDeals.map((deal) => ({
      ...deal,
      score: calculateTopFlightScore(
        deal as FlightDeal,
        minPoints,
        shortestDuration,
      ),
    }));

    if (sortBy === 'top') {
      const sortedByScore = [...dealsWithScores].sort((a, b) => a.score - b.score);
      if (sortedByScore.length > 20) {
        const percentileIndex = Math.floor(sortedByScore.length * 0.65);
        return sortedByScore.slice(0, percentileIndex + 1);
      }
      return sortedByScore;
    }

    return [...dealsWithScores].sort((a, b) => {
      const aCabin = a.displayCabin as
        | 'economy'
        | 'premium'
        | 'business'
        | 'first';
      const bCabin = b.displayCabin as
        | 'economy'
        | 'premium'
        | 'business'
        | 'first';

      if (sortBy === 'points') {
        const aData = a[aCabin];
        const bData = b[bCabin];
        return (aData?.points || Infinity) - (bData?.points || Infinity);
      }

      if (sortBy === 'fees') {
        const aData = a[aCabin];
        const bData = b[bCabin];
        const feeA = aData
          ? parseFloat(aData.fees.replace(/[^\d.]/g, ''))
          : Infinity;
        const feeB = bData
          ? parseFloat(bData.fees.replace(/[^\d.]/g, ''))
          : Infinity;
        return feeA - feeB;
      }
      return 0;
    });
  }, [filteredDeals, sortBy, minPoints, shortestDuration]);

  const hasAnyCashPrice = useMemo(() => {
    return sortedDeals.some(deal => {
        const cabinData = deal[deal.displayCabin as keyof FlightDeal] as any;
        return cabinData && cabinData.exact_cpp && cabinData.exact_cpp !== 'N/A';
    });
  }, [sortedDeals]);

  return (
    <>
      <div ref={sentinelRef} style={{ height: 1, width: '100%' }} />
      <DealFilters
        filters={filters}
        setFilters={setFilters}
        sortBy={sortBy}
        setSortBy={setSortBy}
        availablePrograms={availablePrograms}
        minPoints={minPoints}
        maxPoints={maxPoints}
        className={isStuck ? 'is-stuck' : ''}
        availableCabins={availableCabins}
        availableStops={availableStops}
      />
      <div className="deals-container">
        {sortedDeals.map((deal) => (
          <React.Fragment key={deal.id}>
            <DealRow
              deal={deal as FlightDeal}
              cabin={
                deal.displayCabin as
                  | 'economy'
                  | 'premium'
                  | 'business'
                  | 'first'
              }
              showDate={showDates}
              hasCashPrice={hasAnyCashPrice}
            />
          </React.Fragment>
        ))}
      </div>
    </>
  );
};

export default FlightDealsTable;