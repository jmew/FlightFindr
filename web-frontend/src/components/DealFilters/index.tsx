import React, { useState, useRef, useEffect } from 'react';
import { Dropdown, Form } from 'react-bootstrap';
import { FiChevronDown, FiX } from 'react-icons/fi';

const SORT_OPTIONS = [
  { value: 'top', label: 'Top Flights' },
  { value: 'points', label: 'Points (Lowest)' },
  { value: 'fees', label: 'Fees (Lowest)' },
];

type FilterChipProps = {
  label: string;
  options?: string[];
  selectedOptions: string[];
  onChange: (selected: string[]) => void;
  onClear: () => void;
  isMultiSelect?: boolean;
  children?: React.ReactNode;
  isActive: boolean;
};

const FilterChip: React.FC<FilterChipProps> = ({
  label,
  options,
  selectedOptions,
  onChange,
  onClear,
  isMultiSelect = true,
  children,
  isActive,
}) => {
  const handleSelect = (option: string) => {
    if (isMultiSelect) {
      const newSelection = selectedOptions.includes(option)
        ? selectedOptions.filter((item) => item !== option)
        : [...selectedOptions, option];
      onChange(newSelection);
    } else {
      onChange([option]);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClear();
  };

  const getButtonLabel = () => {
    if (!isActive) return label;
    if (label === 'Price') {
      return `Up to ${selectedOptions[0]} pts`;
    }
    if (selectedOptions.length === 0) return label;
    if (selectedOptions.length === 1) return selectedOptions[0];
    return `${selectedOptions.length} selected`;
  };

  return (
    <Dropdown className="filter-chip-dropdown">
      <Dropdown.Toggle className={`filter-chip ${isActive ? 'active' : ''}`}>
        {getButtonLabel()}
        {isActive ? (
          <FiX className="chip-icon" onClick={handleClear} />
        ) : (
          <FiChevronDown className="chip-icon" />
        )}
      </Dropdown.Toggle>

      <Dropdown.Menu popperConfig={{ strategy: 'fixed' }}>
        {options &&
          options.map((option) => (
            <Dropdown.ItemText key={option} onClick={(e) => e.stopPropagation()}>
              <Form.Check
                type={isMultiSelect ? 'checkbox' : 'radio'}
                id={`${label}-${option}`}
                label={option}
                checked={selectedOptions.includes(option)}
                onChange={() => handleSelect(option)}
                name={isMultiSelect ? option : label}
              />
            </Dropdown.ItemText>
          ))}
        {children && <div className="p-3"  onClick={(e) => e.stopPropagation()}>{children}</div>}
      </Dropdown.Menu>
    </Dropdown>
  );
};

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
          <Form.Label className="price-filter-label">Max Points: {currentMax.toLocaleString()}</Form.Label>
          <Form.Range
            min={minPoints}
            max={maxPoints}
            value={currentMax}
            onChange={handleSliderChange}
            onMouseUp={handleSliderMouseUp}
            onTouchEnd={handleSliderMouseUp}
          />
          <div className="price-range-labels">
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
    <div className={`deal-filters-container ${className || ''}`}>
      <div
        ref={scrollContainerRef}
        className={`filter-chips-scroll-container ${isScrollable ? 'is-scrollable' : ''}`}
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
