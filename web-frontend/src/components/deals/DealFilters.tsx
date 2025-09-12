import React, { useState, useRef, useEffect } from 'react';
import { Form } from 'react-bootstrap';
import FilterChip from './FilterChip';
import styles from './DealFilters.module.css';

const SORT_OPTIONS = [
  { value: 'top', label: 'Top Flights' },
  { value: 'points', label: 'Points (Lowest)' },
  { value: 'fees', label: 'Fees (Lowest)' },
];

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
      options: ['Economy', 'Premium', 'Business', 'First'],
      selectedOptions: filters.cabinClasses,
      onChange: (selected: string[]) => handleFilterChange('cabinClasses', selected),
      onClear: () => handleFilterChange('cabinClasses', []),
      isActive: filters.cabinClasses.length > 0,
      availableOptions: availableCabins,
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
        className={`${styles.filterChipsScrollContainer} ${isScrollable ? styles.isScrollable : ''}`}
      >
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
