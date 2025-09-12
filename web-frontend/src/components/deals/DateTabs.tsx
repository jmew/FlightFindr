import React from 'react';
import styles from './DateTabs.module.css';

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
  if (dates.length <= 1) {
    return null;
  }

  return (
    <div className={styles.tabsContainer}>
      <button
        className={`${styles.tab} ${selectedDate === 'all' ? styles.active : ''}`}
        onClick={() => onDateChange('all')}
      >
        All Dates
      </button>
      {dates.map(({ date, rawDate, points }) => (
        <button
          key={rawDate}
          className={`${styles.tab} ${selectedDate === rawDate ? styles.active : ''}`}
          onClick={() => onDateChange(rawDate)}
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
  );
};

export default DateTabs;
