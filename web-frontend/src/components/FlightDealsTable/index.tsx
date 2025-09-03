import React, { useMemo, useState } from 'react';
import { FiStar, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import DealFilters from '../DealFilters';
import Logo from '../Logo';
import type { FlightDeal } from '../../types';
import { formatDuration, formatFlightTimes } from '../../utils/formatters';

interface DealRowProps {
  deal: FlightDeal;
  cabin: 'economy' | 'premium' | 'business' | 'first';
}

const DealRow: React.FC<DealRowProps> = ({ deal, cabin }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const cabinData = deal[cabin];

  if (!cabinData) return null;

  const { points, fees, booking_url, transfer_info, bonus } = cabinData;
  const transferPartners = transfer_info?.map((t: { bank: string }) => t.bank) || [];
  const [origin, destination] = deal.route.split(' -> ');
  const { departureTime, arrivalTime, isNextDay } = formatFlightTimes(deal.departure_time, deal.arrival_time);

  return (
    <div className="deal-row-container">
      <div className="deal-row" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="section airline-info">
          <Logo type="airline" name={deal.program} />
          <span className="airline-name">{deal.program}</span>
        </div>
        <div className="section time-info">
          <span className="time">
            {departureTime} → {arrivalTime}
            {isNextDay && <sup>+1</sup>}
          </span>
          <div className="route">{deal.route}</div>
        </div>
        <div className="section duration-info">
          <div className="duration">{formatDuration(deal.duration_minutes)}</div>
          <div className="stops">{deal.direct ? 'Nonstop' : `${deal.flight_numbers.length - 1} Stop(s)`}</div>
        </div>
        <div className="section points-info">
          <div className="points-value">
            {points.toLocaleString()} pts
            {bonus && (
              <span title={`Transfer Bonus: ${bonus.percentage}% from ${bonus.bank}`} className="transfer-bonus-star">
                <FiStar />
              </span>
            )}
          </div>
          <div className="fees">+ {fees}</div>
        </div>
        <div className="section details-toggle">
          {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
        </div>
      </div>
      {isExpanded && (
        <div className="deal-row-expanded-details">
          <div className="detail-item">
            <strong>{origin}:</strong>
            <span>{deal.origin_airport_info.name}</span>
          </div>
          <div className="detail-item">
            <strong>{destination}:</strong>
            <span>{deal.destination_airport_info.name}</span>
          </div>
          <div className="detail-item">
            <strong>Flight Numbers:</strong> {deal.flight_numbers.join(', ')}
          </div>
          {bonus && (
            <div className="detail-item transfer-bonus-details">
              <strong>✨ {bonus.percentage}% Transfer Bonus</strong> from {bonus.bank} (ends {bonus.end_date})
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
          <a href={booking_url} target="_blank" rel="noopener noreferrer" className="deal-card-book-btn">
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

const FlightDealsTable: React.FC<FlightDealsTableProps> = ({ deals }) => {
  const [filters, setFilters] = useState<{ cabinClasses: string[] }>({ cabinClasses: ['economy'] });
  const [sortBy, setSortBy] = useState('points');

  const dealsWithCabin = useMemo(() => {
    const cabinPriority: ('economy' | 'premium' | 'business' | 'first')[] = ['economy', 'premium', 'business', 'first'];
    
    return deals.map(deal => {
      for (const cabin of cabinPriority) {
        if (deal[cabin]) {
          return { ...deal, displayCabin: cabin };
        }
      }
      return { ...deal, displayCabin: 'economy' }; // Fallback
    });
  }, [deals]);

  const filteredDeals = useMemo(() => {
    return dealsWithCabin.filter(deal => {
      const { cabinClasses } = filters;
      if (cabinClasses.length > 0 && !cabinClasses.includes(deal.displayCabin)) {
        return false;
      }
      return true;
    });
  }, [dealsWithCabin, filters]);

  const sortedDeals = useMemo(() => {
    return [...filteredDeals].sort((a, b) => {
      const aCabin = a.displayCabin as 'economy' | 'premium' | 'business' | 'first';
      const bCabin = b.displayCabin as 'economy' | 'premium' | 'business' | 'first';
      
      if (sortBy === 'points') {
        const aData = a[aCabin];
        const bData = b[bCabin];
        return (aData?.points || Infinity) - (bData?.points || Infinity);
      }
      
      if (sortBy === 'fees') {
        const aData = a[aCabin];
        const bData = b[bCabin];
        const feeA = aData ? parseFloat(aData.fees.replace(/[^\d.]/g, '')) : Infinity;
        const feeB = bData ? parseFloat(bData.fees.replace(/[^\d.]/g, '')) : Infinity;
        return feeA - feeB;
      }
      return 0;
    });
  }, [filteredDeals, sortBy]);

  return (
    <>
      <DealFilters filters={filters} setFilters={setFilters} sortBy={sortBy} setSortBy={setSortBy} />
      <div className="deals-container">
        {sortedDeals.map((deal) => (
          <React.Fragment key={deal.id}>
            <DealRow deal={deal as FlightDeal} cabin={deal.displayCabin as 'economy' | 'premium' | 'business' | 'first'} />
          </React.Fragment>
        ))}
      </div>
    </>
  );
};

export default FlightDealsTable;
