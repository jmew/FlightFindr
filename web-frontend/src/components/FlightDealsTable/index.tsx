import React, { useMemo, useState } from 'react';
import { FiStar, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { MdAirlineSeatReclineNormal } from 'react-icons/md';
import DealFilters from '../DealFilters';
import Logo from '../Logo';

export interface FlightDealRow {
  id: number;
  date: string;
  airline: string;
  route: string;
  class: string;
  points: number;
  fees: string;
  departureTime: string;
  arrivalTime: string;
  flightNumbers: string;
  bookingUrl: string;
  transferFrom: string;
  transferBonus: string;
  duration: number;
  isBestDeal?: boolean;
}

interface DealCardProps {
  deal: FlightDealRow;
}

const DealCard = ({ deal }: DealCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const transferPartners = deal.transferFrom ? deal.transferFrom.split(',').map(p => p.trim()) : [];

  const getDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const stops = deal.flightNumbers ? deal.flightNumbers.split(',').length - 1 : 0;

  return (
    <div className={`deal-card ${deal.isBestDeal ? 'best-deal' : ''}`}>
      {deal.isBestDeal && <div className="best-deal-badge">Best {deal.class} Deal</div>}
      <div className="deal-card-main">
        <div className="deal-card-airline">
          <Logo type="airline" name={deal.airline} />
          <span>{deal.airline}</span>
        </div>
        <div className="deal-card-points">
          <span className="points-value">{deal.points.toLocaleString()}</span>
          <span className="points-label">pts</span>
          {deal.transferBonus && deal.transferBonus !== 'None' && (
            <span title={`Transfer Bonus: ${deal.transferBonus}`} className="transfer-bonus-star">
              <FiStar />
            </span>
          )}
        </div>
        <div className="deal-card-fees">
          + {deal.fees}
        </div>
      </div>
      <div className="deal-card-details">
        <div className="deal-card-cabin">
          <MdAirlineSeatReclineNormal />
          <span>{deal.class}</span>
        </div>
        <div className="deal-card-route">{deal.route}</div>
        <a href={deal.bookingUrl} target="_blank" rel="noopener noreferrer" className="deal-card-book-btn">
          Book on {deal.airline}
        </a>
      </div>
      
      <div className="deal-card-footer">
        <div className="deal-card-transfers">
          {transferPartners.length > 0 && (
            <>
              <span className="transfer-label">Transfer from:</span>
              <div className="transfer-partners">
                {transferPartners.map(partner => (
                  <Logo key={partner} type="bank" name={partner} />
                ))}
              </div>
            </>
          )}
        </div>
        <button className="details-toggle-btn" onClick={() => setIsExpanded(!isExpanded)}>
          <span>{isExpanded ? 'Hide' : 'Details'}</span>
          {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
        </button>
      </div>

      {isExpanded && (
        <div className="deal-card-expanded-details">
          <div className="detail-item">
            <strong>Flight Numbers:</strong> {deal.flightNumbers || 'N/A'}
          </div>
          <div className="detail-item">
            <strong>Departure:</strong> {new Date(deal.departureTime).toLocaleString()}
          </div>
          <div className="detail-item">
            <strong>Arrival:</strong> {new Date(deal.arrivalTime).toLocaleString()}
          </div>
          <div className="detail-item">
            <strong>Duration:</strong> {getDuration(deal.duration)}
          </div>
          <div className="detail-item">
            <strong>Stops:</strong> {stops > 0 ? `${stops} stop(s)` : 'Nonstop'}
          </div>
          {deal.transferBonus && deal.transferBonus !== 'None' && (
            <div className="detail-item transfer-bonus-details">
              <strong>✨ Transfer Bonus:</strong> {deal.transferBonus}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface FlightDealsProps {
  deals: FlightDealRow[];
}

const FlightDeals = ({ deals }: FlightDealsProps) => {
  const [filters, setFilters] = useState<{ cabinClasses: string[] }>({ cabinClasses: ['Economy'] });
  const [sortBy, setSortBy] = useState('points');

  const filteredDeals = useMemo(() => {
    return deals.filter(deal => {
      const { cabinClasses } = filters;
      if (cabinClasses.length > 0 && !cabinClasses.includes(deal.class)) {
        return false;
      }
      return true;
    });
  }, [deals, filters]);

  const dealsWithBestBadge = useMemo(() => {
    const bestDeals: { [key: string]: FlightDealRow } = {};
    filteredDeals.forEach(deal => {
      const currentBest = bestDeals[deal.class];
      if (!currentBest || deal.points < currentBest.points) {
        bestDeals[deal.class] = deal;
      }
    });
    return filteredDeals.map(deal => ({
      ...deal,
      isBestDeal: !!bestDeals[deal.class] && bestDeals[deal.class].id === deal.id,
    }));
  }, [filteredDeals]);

  const sortedDeals = useMemo(() => {
    return [...dealsWithBestBadge].sort((a, b) => {
      if (sortBy === 'points') {
        if (a.isBestDeal && !b.isBestDeal) return -1;
        if (!a.isBestDeal && b.isBestDeal) return 1;
        return a.points - b.points;
      }
      if (sortBy === 'fees') {
        const feeA = parseFloat(a.fees.replace(/[^\d.]/g, ''));
        const feeB = parseFloat(b.fees.replace(/[^\d.]/g, ''));
        return feeA - feeB;
      }
      return 0;
    });
  }, [dealsWithBestBadge, sortBy]);

  const lastBestDealIndex = sortedDeals.findLastIndex((d: FlightDealRow) => d.isBestDeal);

  return (
    <>
      <DealFilters filters={filters} setFilters={setFilters} sortBy={sortBy} setSortBy={setSortBy} />
      <div className="deals-container">
        {sortedDeals.map((deal, index) => (
          <React.Fragment key={deal.id}>
            <DealCard deal={deal} />
            {deal.isBestDeal && index === lastBestDealIndex && (
              <div className="deal-separator" />
            )}
          </React.Fragment>
        ))}
      </div>
    </>
  );
};

export default FlightDeals;
