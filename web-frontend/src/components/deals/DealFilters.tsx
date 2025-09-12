import React, { useState, useRef, useEffect } from 'react';
import { Form } from 'react-bootstrap';
import FilterChip from './FilterChip';
import styles from './DealFilters.module.css';

const SORT_OPTIONS = [
  { value: 'top', label: 'Top Flights' },
  { value: 'points', label: 'Points (Lowest)' },
  { value: 'fees', label: 'Fees (Lowest)' },
];

interface MinDeal {
  points: number;
  fees: number;
}

interface DealFiltersProps {
  filters: {
    cabinClasses: string[];
    airlinePrograms: string[];
    stops: string[];
    maxPoints: number | null;
  };
  setFilters: (filters: any) => void;
  sortBy: string;
  setSortBy: (sortBy: string) => void;
  availablePrograms: string[];
  minPoints: number;
  maxPoints: number;
  availableCabins: string[];
  availableStops: string[];
  minDealPerCabin: Record<string, MinDeal>;
  className?: string;
}

const DealFilters: React.FC<DealFiltersProps> = ({
  filters,
  setFilters,
  sortBy,
  setSortBy,
  availablePrograms,
  minPoints,
  maxPoints,
  availableCabins,
  availableStops,
  minDealPerCabin,
  className,
}) => {
  const [currentMax, setCurrentMax] = useState(filters.maxPoints || maxPoints);
  const isPriceActive = filters.maxPoints !== null;
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isScrollable, setIsScrollable] = useState(false);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const checkScrollable = () => {
      const hasOverflow = container.scrollWidth > container.clientWidth;
      setIsScrollable(hasOverflow);
    };

    checkScrollable(); // Initial check

    const resizeObserver = new ResizeObserver(checkScrollable);
    resizeObserver.observe(container);

    // Also observe children for changes
    Array.from(container.children).forEach(child => {
      resizeObserver.observe(child);
    });

    return () => {
      resizeObserver.disconnect();
    };
  }, [filters, availablePrograms]); // Re-check when filters or programs change


  const handleFilterChange = (filterName: string, value: any) => {
    setFilters((prevFilters: any) => ({ ...prevFilters, [filterName]: value }));
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMax(Number(e.target.value));
  };

  const handleSliderMouseUp = () => {
    handleFilterChange('maxPoints', currentMax);
  };
  
  const handlePriceClear = () => {
    handleFilterChange('maxPoints', null);
    setCurrentMax(maxPoints);
  }

  const formatNumber = (num: number) => {
    // This will be a string. If it ends with .0, remove it.
    const fixed = num.toFixed(1);
    if (fixed.endsWith('.0')) {
      return fixed.substring(0, fixed.length - 2);
    }
    return fixed;
  }

  const getCabinOption = (cabin: string) => {
    const minDeal = minDealPerCabin[cabin];
    const value = cabin;
    let label: React.ReactNode = cabin;

    if (minDeal) {
      const formattedPoints = formatNumber(minDeal.points / 1000);
      const formattedFees = formatNumber(minDeal.fees);
      label = (
        <span>
          {cabin} - from <b style={{ color: 'var(--gem-sys-color--primary)' }}>{formattedPoints}k</b> pts + ${formattedFees}
        </span>
      );
    }
    return { value, label };
  };

  const cabinOptions = ['Economy', 'Premium', 'Business', 'First'].map(getCabinOption);
  const availableCabinOptions = availableCabins.map(getCabinOption);

  const filtersConfig = [
    {
      id: 'stops',
      label: 'Stops',
      options: ['Nonstop', '1 Stop', '2+ Stops'],
      selectedOptions: filters.stops,
      onChange: (selected: string[]) => handleFilterChange('stops', selected),
      onClear: () => handleFilterChange('stops', []),
      isActive: filters.stops.length > 0,
      availableOptions: availableStops,
      isMultiSelect: false,
    },
    {
      id: 'airlines',
      label: 'Airlines',
      options: availablePrograms,
      selectedOptions: filters.airlinePrograms,
      onChange: (selected: string[]) => handleFilterChange('airlinePrograms', selected),
      onClear: () => handleFilterChange('airlinePrograms', []),
      isActive: filters.airlinePrograms.length > 0,
    },
    {
      id: 'cabins',
      label: 'Cabins',
      options: cabinOptions,
      selectedOptions: filters.cabinClasses,
      onChange: (selected: string[]) => {
        handleFilterChange('cabinClasses', selected);
      },
      onClear: () => handleFilterChange('cabinClasses', []),
      isActive: filters.cabinClasses.length > 0,
      availableOptions: availableCabinOptions,
    },
    {
      id: 'price',
      label: 'Price',
      selectedOptions: isPriceActive ? [currentMax.toLocaleString()] : [],
      onChange: () => {},
      onClear: handlePriceClear,
      isActive: isPriceActive,
      children: (
        <>
          <Form.Label className={styles.priceFilterLabel}>Max Points: {currentMax.toLocaleString()}</Form.Label>
          <Form.Range
            min={minPoints}
            max={maxPoints}
            value={currentMax}
            onChange={handleSliderChange}
            onMouseUp={handleSliderMouseUp}
            onTouchEnd={handleSliderMouseUp}
          />
          <div className={styles.priceRangeLabels}>
            <span>{minPoints.toLocaleString()}</span>
            <span>{maxPoints.toLocaleString()}</span>
          </div>
        </>
      ),
    },
    {
      id: 'sort',
      label: 'Sort By',
      options: SORT_OPTIONS.map(o => o.label),
      selectedOptions: [SORT_OPTIONS.find(o => o.value === sortBy)?.label || ''],
      onChange: (selected: string[]) => {
        const selectedValue = SORT_OPTIONS.find(o => o.label === selected[0])?.value;
        if (selectedValue) {
          setSortBy(selectedValue);
        }
      },
      onClear: () => setSortBy('top'),
      isActive: sortBy !== 'top',
      isMultiSelect: false,
    },
  ];

  const activeFilters = filtersConfig.filter(f => f.isActive);
  const inactiveFilters = filtersConfig.filter(f => !f.isActive);

  return (
    <div className={`${styles.dealFiltersContainer} ${className || ''}`}>
      <div
        ref={scrollContainerRef}
        className={`${styles.filterChipsScrollContainer} ${isScrollable ? styles.isScrollable : ''}`}>
        {inactiveFilters.map(filter => (
          <FilterChip key={filter.id} {...filter} />
        ))}
        {activeFilters.map(filter => (
          <FilterChip key={filter.id} {...filter} />
        ))}
      </div>
    </div>
  );
};

export default DealFilters;
