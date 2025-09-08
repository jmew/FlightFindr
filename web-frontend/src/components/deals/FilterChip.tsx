import React from 'react';
import { Dropdown, Form } from 'react-bootstrap';
import { FiChevronDown, FiX } from 'react-icons/fi';
import styles from './FilterChip.module.css';

type FilterChipProps = {
  label: string;
  options?: string[];
  selectedOptions: string[];
  onChange: (selected: string[]) => void;
  onClear: () => void;
  isMultiSelect?: boolean;
  children?: React.ReactNode;
  isActive: boolean;
  availableOptions?: string[];
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
  availableOptions,
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
    <Dropdown className={styles.filterChipDropdown}>
      <Dropdown.Toggle className={`${styles.dropdownToggle} ${isActive ? styles.active : ''}`}>
        {getButtonLabel()}
        {isActive ? (
          <FiX className={styles.chipIcon} onClick={handleClear} />
        ) : (
          <FiChevronDown className={styles.chipIcon} />
        )}
      </Dropdown.Toggle>

      <Dropdown.Menu popperConfig={{ strategy: 'fixed' }} renderOnMount className={styles.dropdownMenu}>
        {options &&
          options.map((option) => (
            <Dropdown.ItemText key={option} onClick={(e) => e.stopPropagation()} className={styles.dropdownItemText}>
              <Form.Check
                type={isMultiSelect ? 'checkbox' : 'radio'}
                id={`${label}-${option}`}
                label={option}
                checked={selectedOptions.includes(option)}
                onChange={() => handleSelect(option)}
                name={isMultiSelect ? option : label}
                disabled={!selectedOptions.includes(option) && availableOptions && !availableOptions.includes(option)}
                className={styles.formCheckInput}
              />
            </Dropdown.ItemText>
          ))}
        {children && <div className="p-3"  onClick={(e) => e.stopPropagation()}>{children}</div>}
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default FilterChip;
