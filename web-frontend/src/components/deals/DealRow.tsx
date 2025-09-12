import React, { useMemo, useState } from 'react';
import {
  FiStar,
  FiChevronDown,
  FiChevronUp,
  FiAlertTriangle,
} from 'react-icons/fi';
import Logo from '../common/Logo';
import type { CompactFlightDeal, BookingOption, CabinDeal } from '../../types';
import { formatDuration, formatFlightTimes, formatTime, formatDate } from '../../utils/formatters';
import { getAirlineNameByCode } from '../../utils/airlineMappings';
import aircodes from 'aircodes';
import styles from './FlightDealsTable.module.css';
import itineraryStyles from './Itinerary.module.css';

interface DealRowProps {
  deal: CompactFlightDeal;
  hasCashPrice: boolean;
  showDate?: boolean;
  medianFee: number;
}

const DealRow: React.FC<DealRowProps> = ({ deal, hasCashPrice, showDate, medianFee }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const bestDeal = useMemo(() => {
    let bestCabinDeal: CabinDeal | undefined;
    let bestOption: BookingOption | undefined;
    let bestCabinName: string | undefined;

    deal.options.forEach(option => {
      (['economy', 'premium', 'business', 'first'] as const).forEach(cabin => {
        const cabinData = option[cabin];
        if (cabinData) {
          if (!bestCabinDeal || cabinData.points < bestCabinDeal.points) {
            bestCabinDeal = cabinData;
            bestOption = option;
            bestCabinName = cabin;
          }
        }
      });
    });

    return { bestCabinDeal, bestOption, bestCabinName };
  }, [deal]);

  if (!bestDeal.bestCabinDeal || !bestDeal.bestOption) {
    return null;
  }

  const { bestCabinDeal, bestOption, bestCabinName } = bestDeal;
  const { points, fees, bonus } = bestCabinDeal;
  const { program } = bestOption;

  const [origin, destination] = deal.route.split(' -> ');
  const { departureTime, arrivalTime, isNextDay } = formatFlightTimes(
    deal.departure_time,
    deal.arrival_time,
  );

  const departureDate = showDate ? formatDate(deal.departure_time): null;

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
    if (name === 'Delta Air Lines') return 'Delta';
    return name;
  };

  const displayName = getDisplayName(airlineName);

  const routeString =
    isDirect
      ? `${origin} → ${destination}`
      : `${origin} → ${(deal.stops || []).join(' → ')} → ${destination}`;

  const getCppColor = (cpp: number | string) => {
    if (typeof cpp === 'string') return 'inherit';
    if (cpp > 1.2) return 'var(--gem-sys-color--positive)';
    if (cpp < 1) return 'var(--gem-sys-color--negative)';
    return 'inherit';
  };

  return (
    <div className={styles.dealRowContainer}>
      <div className={styles.dealRow} style={gridStyle} onClick={() => setIsExpanded(!isExpanded)}>
        <div className={`${styles.section} ${styles.airlineInfo}`}>
          <Logo
            type="airline"
            code={
              deal.airlines && deal.airlines.length === 1
                ? deal.airlines[0]
                : undefined
            }
            name={displayName}
          />
          <span className={styles.airlineName}>{displayName}</span>
        </div>
        <div className={`${styles.section} ${styles.timeInfo}`} data-label="Flight">
          <div className={styles.timeInfoContent}>
            {departureDate && <div className={styles.date}>{departureDate}</div>}
            <span className={styles.time}>
              {departureTime} → {arrivalTime}
              {isNextDay && <sup>+1</sup>}
            </span>
            <div className={styles.route}>{routeString}</div>
          </div>
        </div>
        <div className={`${styles.section} ${styles.durationInfo}`} data-label="Duration">
          <div className={styles.sectionContent}>
            <div className={styles.duration}>
              {formatDuration(deal.duration_minutes)}
            </div>
            <div className={styles.stops}>
              {isDirect
                ? 'Nonstop'
                : `${(deal.stops || []).length} Stop${(deal.stops || []).length !== 1 ? 's' : ''}`}
              {!isDirect && deal.overnight_layover && (
                <span
                  title="Includes an overnight layover"
                  className={styles.overnightWarning}
                >
                  <FiAlertTriangle />
                </span>
              )}
            </div>
          </div>
        </div>
        <div className={`${styles.section} ${styles.pointsInfo}`} data-label="Cost">
          <div className={styles.sectionContent}>
            <div className={styles.pointsValue}>
              {bonus && (
                <span
                  title={`Transfer Bonus: ${bonus.percentage}% from ${bonus.bank}`}
                  className={styles.transferBonusStar}
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
            <div 
              className={styles.fees}
              style={{
                color: parseFloat(fees.replace(/[^\d.]/g, '')) > medianFee * 1.5 ? 'rgb(242, 139, 130)' : 'inherit'
              }}
            >
              + ${fees} USD
            </div>
          </div>
        </div>
        {hasCashPrice &&
          (bestCabinDeal.exact_cpp && bestCabinDeal.exact_cpp !== 'N/A' ? (
            <div className={`${styles.section} ${styles.cppInfo}`} data-label="Value">
              <div
                className={styles.pointsValue}
                style={{ color: getCppColor(bestCabinDeal.exact_cpp) }}
              >
                {`${bestCabinDeal.exact_cpp}¢`} / pt
              </div>
              <div className={styles.fees}>
                ${bestCabinDeal.exact_cash_price} USD
              </div>
            </div>
          ) : (
            <div />
          ))}
        <div className={`${styles.section} ${styles.detailsToggle}`}>
          {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
        </div>
      </div>
      {isExpanded && (
        <div className={styles.dealRowExpandedDetails}>
          <div className={itineraryStyles.itineraryContainer}>
            {deal.segments.map((segment, index) => {
              const firstSegmentDepartureDate = deal.segments[0].departureTime.substring(0, 10);
              const nextSegment = deal.segments[index + 1];
              // let showLayoverDate = false;
              if (nextSegment) {
                const nextSegmentDepartureDate = nextSegment.departureTime.substring(0, 10);
                // if (nextSegmentDepartureDate !== firstSegmentDepartureDate) {
                //   showLayoverDate = true;
                // }
              }

              return (
                <React.Fragment key={index}>
                  <div className={itineraryStyles.itinerarySegment}>
                    <div className={itineraryStyles.logoContainer}>
                      <Logo type="airline" code={segment.airlineCode} name={getAirlineNameByCode(segment.airlineCode)} />
                    </div>
                    <div className={itineraryStyles.timeline}>
                      <div className={itineraryStyles.dot}></div>
                      <div className={itineraryStyles.line}></div>
                      <div className={itineraryStyles.dot}></div>
                    </div>
                    <div className={itineraryStyles.legDetails}>
                      <div className={itineraryStyles.timeAndAirport}>
                        <span className={itineraryStyles.time}>{formatTime(segment.departureTime)}</span>
                        <span>·</span>
                        <span className={itineraryStyles.airport}>
                          {aircodes.getAirportByIata(segment.departureAirport)?.name || segment.departureAirport} ({segment.departureAirport})
                        </span>
                      </div>
                      <div className={itineraryStyles.travelTime}>
                        <span>Travel time: {formatDuration(segment.durationMinutes)}</span>
                        {bestCabinName && (
                          <>
                            <span>·</span>
                            <span className={itineraryStyles.cabin}>{bestCabinName.charAt(0).toUpperCase() + bestCabinName.slice(1)}</span>
                          </>
                        )}
                        {segment.isOvernight && (
                          <>
                            <span>·</span>
                            <span className={itineraryStyles.overnight}>
                              <FiAlertTriangle />
                              Overnight
                            </span>
                          </>
                        )}
                      </div>
                      <div className={itineraryStyles.timeAndAirport}>
                        <span className={itineraryStyles.time}>
                          {formatTime(segment.arrivalTime)}
                          {segment.arrivalDayDiff && <sup>+{segment.arrivalDayDiff}</sup>}
                        </span>
                        <span>·</span>
                        <span className={itineraryStyles.airport}>
                          {aircodes.getAirportByIata(segment.arrivalAirport)?.name || segment.arrivalAirport} ({segment.arrivalAirport})
                        </span>
                      </div>
                    </div>
                    <div className={itineraryStyles.flightInfo}>
                      <div>{getAirlineNameByCode(segment.airlineCode)}</div>
                      <div>{segment.flightNumber}</div>
                    </div>
                  </div>
                  {segment.layoverMinutes && (
                    <div className={itineraryStyles.layover}>
                      <div className={itineraryStyles.layoverContent}>
                        {formatDuration(segment.layoverMinutes)} layover · {aircodes.getAirportByIata(segment.arrivalAirport)?.city || segment.arrivalAirport} ({segment.arrivalAirport})
                      </div>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
          <div className={styles.bookingOptionsContainer}>
            {deal.options.map(option => (
              <div key={option.program} className={styles.bookingOptionCard}>
                <div className={styles.bookingOptionHeader}>
                  <span className={styles.bookingOptionProgram}>Book on {option.program}</span>
                  <div className={styles.transferPartnersSmall}>
                    {option.transfer_info.map(p => <Logo key={p} type="bank" name={p} />)}
                  </div>
                </div>
                <div className={styles.cabinOptions}>
                  {['economy', 'premium', 'business', 'first'].map(cabin => {
                    const cabinData = option[cabin as keyof BookingOption] as CabinDeal | undefined;
                    if (!cabinData) return null;
                    return (
                      <div key={cabin} className={styles.cabinOption}>
                        <span className={styles.cabinName}>{cabin.charAt(0).toUpperCase() + cabin.slice(1)}</span>
                        <span className={styles.cabinPoints}>{cabinData.points.toLocaleString()} pts</span>
                        <span className={styles.cabinFees}>+ {cabinData.fees}</span>
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
                  Book Award Flight
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DealRow;
