import React, { useMemo, useState, useRef, useEffect } from 'react';
import DealFilters from './DealFilters';
import DealRow from './DealRow';
import PaginationControls from './PaginationControls';
import type { CompactFlightDeal, BookingOption, CabinDeal } from '../../types';
import styles from './FlightDealsTable.module.css';

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
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

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
    setCurrentPage(1);
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

  const paginatedDeals = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return sortedDeals.slice(startIndex, endIndex);
  }, [sortedDeals, currentPage, itemsPerPage]);

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
        className={isStuck ? styles.isStuck : ''}
        availableCabins={availableCabins}
        availableStops={availableStops}
      />
      <div className={styles.dealsContainer}>
        {paginatedDeals.map((deal) => (
          <React.Fragment key={deal.id}>
            <DealRow
              deal={deal}
              showDate={showDates}
              hasCashPrice={hasAnyCashPrice}
            />
          </React.Fragment>
        ))}
      </div>
      <PaginationControls
        currentPage={currentPage}
        itemsPerPage={itemsPerPage}
        totalItems={sortedDeals.length}
        onPageChange={setCurrentPage}
        onItemsPerPageChange={setItemsPerPage}
      />
    </>
  );
};

export default FlightDealsTable;
