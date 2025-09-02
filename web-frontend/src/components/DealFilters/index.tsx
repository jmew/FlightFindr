import React from 'react';

const CABIN_CLASSES = ['Economy', 'Premium', 'Business', 'First'];
const SORT_OPTIONS = [
  { value: 'points', label: 'Points (Lowest)' },
  { value: 'fees', label: 'Fees (Lowest)' },
];

interface DealFiltersProps {
  filters: {
    cabinClasses: string[];
  };
  setFilters: (filters: any) => void;
  sortBy: string;
  setSortBy: (sortBy: string) => void;
}

const DealFilters: React.FC<DealFiltersProps> = ({ filters, setFilters, sortBy, setSortBy }) => {
  const handleCabinClassChange = (cabinClass: string) => {
    const currentClasses = filters.cabinClasses;
    const newClasses = currentClasses.includes(cabinClass)
      ? currentClasses.filter((c: string) => c !== cabinClass)
      : [...currentClasses, cabinClass];
    setFilters({ ...filters, cabinClasses: newClasses });
  };

  return (
    <div className="deal-filters-container">
      <div className="filter-group">
        <span className="filter-label">Cabin Class</span>
        <div className="toggle-buttons">
          {CABIN_CLASSES.map(cabinClass => (
            <button
              key={cabinClass}
              className={`toggle-btn ${filters.cabinClasses.includes(cabinClass) ? 'active' : ''}`}
              onClick={() => handleCabinClassChange(cabinClass)}
            >
              {cabinClass}
            </button>
          ))}
        </div>
      </div>
      <div className="filter-group">
        <span className="filter-label">Sort By</span>
        <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          {SORT_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default DealFilters;