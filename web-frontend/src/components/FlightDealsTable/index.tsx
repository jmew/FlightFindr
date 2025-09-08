import React, { useMemo, useState, useRef, useEffect } from 'react';
import {
  FiStar,
  FiChevronDown,
  FiChevronUp,
  FiAlertTriangle,
} from 'react-icons/fi';
import DealFilters from '../DealFilters';
import Logo from '../Logo';
import type { CompactFlightDeal, BookingOption, CabinDeal } from '../../types';
import { formatDuration, formatFlightTimes } from '../../utils/formatters';
import { getAirlineNameByCode } from '../../utils/airlineMappings';

interface DealRowProps {
  deal: CompactFlightDeal;
  showDate: boolean;
  hasCashPrice: boolean;
}

const DealRow: React.FC<DealRowProps> = ({ deal, showDate, hasCashPrice }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const bestDeal = useMemo(() => {
    let bestCabinDeal: CabinDeal | undefined;
    let bestOption: BookingOption | undefined;

    deal.options.forEach(option => {
      ['economy', 'premium', 'business', 'first'].forEach(cabin => {
        const cabinKey = cabin as keyof BookingOption;
        const cabinData = option[cabinKey] as CabinDeal | undefined;
        if (cabinData) {
          if (!bestCabinDeal || cabinData.points < bestCabinDeal.points) {
            bestCabinDeal = cabinData;
            bestOption = option;
          }
        }
      });
    });

    return { bestCabinDeal, bestOption };
  }, [deal]);

  if (!bestDeal.bestCabinDeal || !bestDeal.bestOption) {
    return null;
  }

  const { bestCabinDeal, bestOption } = bestDeal;
  const { points, fees, bonus } = bestCabinDeal;
  const { transfer_info, program } = bestOption;

  const [origin, destination] = deal.route.split(' -> ');
  const { departureTime, arrivalTime, isNextDay } = formatFlightTimes(
    deal.departure_time,
    deal.arrival_time,
  );

  const isDirect = (deal.stops || []).length === 0;

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
    isDirect
      ? `${origin} → ${destination}`
      : `${origin} → ${(deal.stops || []).join(' → ')} → ${destination}`;

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
              {new Date(deal.departure_time.replace(/-/g, '/')).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
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
            {isDirect
              ? 'Nonstop'
              : `${(deal.stops || []).length} Stop${(deal.stops || []).length !== 1 ? 's' : ''}`}
            {!isDirect && deal.overnight_layover && (
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
            {program.split(' ')[0].toLowerCase() !== airlineName.split(' ')[0].toLowerCase() && (
              <div className="tooltip-container">
                <span style={{ color: 'var(--gem-sys-color--primary)' }}>*</span>
                <span className="tooltip-text">Book with {program}</span>
              </div>
            )}
            {points.toLocaleString()}<span style={{ fontSize: '0.5em' }}> pts</span>
          </div>
          <div className="fees">+ {fees} USD</div>
        </div>
        {hasCashPrice &&
          (bestCabinDeal.exact_cpp && bestCabinDeal.exact_cpp !== 'N/A' ? (
            <div className="section cpp-info">
              <div
                className="points-value"
                style={{ color: getCppColor(bestCabinDeal.exact_cpp) }}
              >
                {`${bestCabinDeal.exact_cpp}¢`} / pt
              </div>
              <div className="fees">
                (Cash) ${bestCabinDeal.exact_cash_price} USD
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
          {deal.layover_lengths && deal.layover_lengths.length > 0 && (
              <div className="detail-item">
                <strong>Layovers:</strong>
                <span>
                  {deal.layover_lengths.map((duration, index) => (
                    `Layover ${index + 1}: ${formatDuration(duration)}`
                  )).join(', ')}
                </span>
              </div>
            )}
          <div className="detail-item transfers">
            <strong>Transfer From:</strong>
            <div className="transfer-partners">
                {transfer_info.map((partner: string) => (
                  <Logo key={partner} type="bank" name={partner} />
                ))}
              </div>
            </div>
            <div className="booking-options-container">
              {deal.options.map(option => (
                <div key={option.program} className="booking-option-card">
                  <div className="booking-option-header">
                    <span className="booking-option-program">Book on {option.program}</span>
                    <div className="transfer-partners-small">
                      {option.transfer_info.map(p => <Logo key={p} type="bank" name={p} />)}
                    </div>
                  </div>
                  <div className="cabin-options">
                    {['economy', 'premium', 'business', 'first'].map(cabin => {
                      const cabinData = option[cabin as keyof BookingOption] as CabinDeal | undefined;
                      if (!cabinData) return null;
                      return (
                        <div key={cabin} className="cabin-option">
                          <span className="cabin-name">{cabin.charAt(0).toUpperCase() + cabin.slice(1)}</span>
                          <span className="cabin-points">{cabinData.points.toLocaleString()} pts</span>
                          <span className="cabin-fees">+ {cabinData.fees}</span>
                        </div>
                      )
                    })}
                  </div>
                  <a
                    href={option.booking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="deal-card-book-btn"
                  >
                    Go to Booking
                  </a>
                </div>
              ))}
            </div>
        </div>
      )}
    </div>
  );
};

interface FlightDealsTableProps {
  deals: CompactFlightDeal[];
}

interface ActiveFilters {
  cabinClasses: string[];
  airlinePrograms: string[];
  stops: string[];
  maxPoints: number | null;
}

const calculateTopFlightScore = (deal: CompactFlightDeal, cheapestPrice: number, shortestDuration: number) => {
  const weights = {
    price: 40,
    duration: 30,
    stops: 20,
    time: 10,
  };

  const bestOption = deal.options.reduce((best, option) => {
    const optionPoints = Math.min(...Object.values(option).filter(c => c && typeof c === 'object' && 'points' in c).map(c => (c as CabinDeal).points));
    if (optionPoints < best.points) {
      return { points: optionPoints };
    }
    return best;
  }, { points: Infinity });

  if (bestOption.points === Infinity) return Infinity;

  const priceScore = bestOption.points / cheapestPrice;
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
    const firstDate = new Date(deals[0].departure_time).toDateString();
    return !deals.every(deal => new Date(deal.departure_time).toDateString() === firstDate);
  }, [deals]);

  const { availablePrograms, minPoints, maxPoints, shortestDuration, availableCabins, availableStops } = useMemo(() => {
    const programs = new Set<string>();
    const cabins = new Set<string>();
    const stops = new Set<number>();
    let min = Infinity;
    let max = 0;
    let shortest = Infinity;

    deals.forEach(deal => {
      if (deal.duration_minutes < shortest) {
        shortest = deal.duration_minutes;
      }
      stops.add((deal.stops || []).length);
      deal.options.forEach(option => {
        programs.add(option.program);
        ['economy', 'premium', 'business', 'first'].forEach(cabin => {
          const cabinData = option[cabin as keyof BookingOption] as CabinDeal | undefined;
          if (cabinData && cabinData.points) {
            cabins.add(cabin.charAt(0).toUpperCase() + cabin.slice(1));
            if (cabinData.points < min) min = cabinData.points;
            if (cabinData.points > max) max = cabinData.points;
          }
        });
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

  const filteredDeals = useMemo(() => {
    return deals.filter((deal) => {
      const { cabinClasses, airlinePrograms, stops, maxPoints } = filters;

      const hasMatchingOption = deal.options.some(option => {
        if (airlinePrograms.length > 0 && !airlinePrograms.includes(option.program)) {
          return false;
        }

        const hasMatchingCabin = ['economy', 'premium', 'business', 'first'].some(cabin => {
          const cabinKey = cabin as keyof BookingOption;
          const cabinData = option[cabinKey] as CabinDeal | undefined;
          if (!cabinData) return false;

          if (cabinClasses.length > 0 && !cabinClasses.some(c => cabin.startsWith(c.toLowerCase()))) {
            return false;
          }
          if (maxPoints !== null && cabinData.points > maxPoints) {
            return false;
          }
          return true;
        });

        return hasMatchingCabin;
      });

      if (!hasMatchingOption) return false;

      if (stops.length > 0) {
        const stopCount = (deal.stops || []).length;
        const stopConditions = {
          'Nonstop': stopCount === 0,
          '1 Stop': stopCount === 1,
          '2+ Stops': stopCount >= 2,
        };
        const matches = stops.some(stop => stopConditions[stop as keyof typeof stopConditions]);
        if (!matches) return false;
      }

      return true;
    });
  }, [deals, filters]);

  const sortedDeals = useMemo(() => {
    const getDealSortValue = (deal: CompactFlightDeal, cabinFilter: string[]) => {
      let bestPoints = Infinity;
      let bestFees = Infinity;

      deal.options.forEach(option => {
        ['economy', 'premium', 'business', 'first'].forEach(cabin => {
          if (cabinFilter.length > 0 && !cabinFilter.some(c => cabin.startsWith(c.toLowerCase()))) return;

          const cabinData = option[cabin as keyof BookingOption] as CabinDeal | undefined;
          if (cabinData) {
            if (cabinData.points < bestPoints) {
              bestPoints = cabinData.points;
            }
            const feeValue = parseFloat(cabinData.fees.replace(/[^\d.]/g, ''));
            if (feeValue < bestFees) {
              bestFees = feeValue;
            }
          }
        });
      });

      return { points: bestPoints, fees: bestFees };
    };

    const dealsWithScores = filteredDeals.map((deal) => ({
      ...deal,
      score: calculateTopFlightScore(deal, minPoints, shortestDuration),
      sortValues: getDealSortValue(deal, filters.cabinClasses),
    }));

    if (sortBy === 'top') {
      return [...dealsWithScores].sort((a, b) => a.score - b.score);
    }

    return [...dealsWithScores].sort((a, b) => {
      if (sortBy === 'points') {
        const pointsA = a.sortValues.points;
        const pointsB = b.sortValues.points;
        if (pointsA !== pointsB) {
          return pointsA - pointsB;
        }
        const stopsA = a.stops?.length || 0;
        const stopsB = b.stops?.length || 0;
        return stopsA - stopsB;
      }
      if (sortBy === 'fees') {
        return a.sortValues.fees - b.sortValues.fees;
      }
      return 0;
    });
  }, [filteredDeals, sortBy, minPoints, shortestDuration, filters.cabinClasses]);

  const hasAnyCashPrice = useMemo(() => {
    return sortedDeals.some(deal => {
      return deal.options.some(option => {
        return ['economy', 'premium', 'business', 'first'].some(cabin => {
          const cabinData = option[cabin as keyof BookingOption] as CabinDeal | undefined;
          return cabinData && cabinData.exact_cpp && cabinData.exact_cpp !== 'N/A';
        });
      });
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
              deal={deal}
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
