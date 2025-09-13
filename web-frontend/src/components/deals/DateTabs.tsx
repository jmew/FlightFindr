import React, { useRef, useEffect, useState } from 'react';
import styles from './DateTabs.module.css';
import { FaChevronRight } from 'react-icons/fa';

interface DateTab {
  date: string; // Formatted for display
  rawDate: string; // YYYY-MM-DD for logic
  points: number | null;
}

interface DateTabsProps {
  dates: DateTab[];
  selectedDate: string; // This will be the rawDate
  onDateChange: (date: string) => void;
  cheapestDate: string | null;
}

const DateTabs: React.FC<DateTabsProps> = ({ dates, selectedDate, onDateChange, cheapestDate }) => {
  const tabsContainerRef = useRef<HTMLDivElement>(null);
  const cheapestTabRef = useRef<HTMLButtonElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  useEffect(() => {
    const checkCheapestTabVisibility = () => {
      if (tabsContainerRef.current && cheapestTabRef.current) {
        const container = tabsContainerRef.current;
        const cheapestTab = cheapestTabRef.current;

        const containerRect = container.getBoundingClientRect();
        const cheapestTabRect = cheapestTab.getBoundingClientRect();

        // Check if the cheapest tab is outside the visible area of the container on the right
        if (cheapestTabRect.right > containerRect.right) {
          setShowScrollButton(true);
        } else {
          setShowScrollButton(false);
        }
      }
    };

    // Check on initial render and when dates change
    checkCheapestTabVisibility();

    // Optional: Add resize listener if the window size can change
    window.addEventListener('resize', checkCheapestTabVisibility);
    return () => window.removeEventListener('resize', checkCheapestTabVisibility);
  }, [dates, cheapestDate]);

  const scrollToCheapest = () => {
    if (cheapestTabRef.current) {
      cheapestTabRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    }
  };

  if (dates.length <= 1) {
    return null;
  }

  return (
    <div className={styles.tabsWrapper}>
      <div className={styles.tabsContainer} ref={tabsContainerRef}>
        <button
          className={`${styles.tab} ${selectedDate === 'all' ? styles.active : ''}`}
          onClick={() => onDateChange('all')}
        >
          All Dates
        </button>
        {dates.map(({ date, rawDate, points }) => (
          <button
            key={rawDate}
            ref={rawDate === cheapestDate ? cheapestTabRef : null}
            className={`${styles.tab} ${selectedDate === rawDate ? styles.active : ''}`}
            onClick={() => onDateChange(rawDate)}
            disabled={points === null}
          >
            <span className={styles.date}>{date}</span>
            {points !== null && (
              <span className={`${styles.points} ${rawDate === cheapestDate ? styles.cheapest : ''}`}>
                from {(points / 1000).toFixed(0)}k pts
              </span>
            )}
          </button>
        ))}
      </div>
      {showScrollButton && (
        <button className={styles.scrollButton} onClick={scrollToCheapest}>
          <FaChevronRight />
        </button>
      )}
    </div>
  );
};

export default DateTabs;