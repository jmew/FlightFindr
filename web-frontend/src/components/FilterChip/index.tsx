import React from 'react';
import { Dropdown, Form } from 'react-bootstrap';
import { FiChevronDown, FiX } from 'react-icons/fi';

type FilterChipProps = {
  label: string;
  options?: string[];
  selectedOptions: string[];
  onChange: (selected: string[]) => void;
  isMultiSelect?: boolean;
  availableOptions?: string[];
};

const FilterChip: React.FC<FilterChipProps> = ({
  label,
  options,
  selectedOptions,
  onChange,
  isMultiSelect = true,
  availableOptions,
}) => {
  const isActive = selectedOptions.length > 0;

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
    onChange([]);
  };

  const getButtonLabel = () => {
    if (!isActive) return label;
    if (isMultiSelect) {
      if (selectedOptions.length === 1) return selectedOptions[0];
      return `${selectedOptions.length} selected`;
    }
    return selectedOptions[0];
  };

  return (
    <Dropdown className="filter-chip-dropdown" autoClose="outside">
      <Dropdown.Toggle className={`filter-chip ${isActive ? 'active' : ''}`}>
        {getButtonLabel()}
        {isActive ? (
          <FiX className="chip-icon" onClick={handleClear} />
        ) : (
          <FiChevronDown className="chip-icon" />
        )}
      </Dropdown.Toggle>

      {options && (
        <Dropdown.Menu>
          {options.map((option) => (
            <Dropdown.ItemText key={option}>
              <Form.Check
                type={isMultiSelect ? 'checkbox' : 'radio'}
                id={`${label}-${option}`}
                label={option}
                checked={selectedOptions.includes(option)}
                onChange={() => handleSelect(option)}
                name={isMultiSelect ? option : label}
                disabled={!selectedOptions.includes(option) && availableOptions && !availableOptions.includes(option)}
              />
            </Dropdown.ItemText>
          ))}
        </Dropdown.Menu>
      )}
    </Dropdown>
  );
};

export default FilterChip;
