import React from 'react';
import { Dropdown, Form } from 'react-bootstrap';
import { FiChevronDown, FiX } from 'react-icons/fi';
import styles from './FilterChip.module.css';

type OptionObject = {
  value: string;
  label: React.ReactNode;
};

type FilterOption = string | OptionObject;

type FilterChipProps = {
  label: string;
  options?: FilterOption[];
  selectedOptions: string[];
  onChange: (selected: string[]) => void;
  onClear: () => void;
  isMultiSelect?: boolean;
  children?: React.ReactNode;
  isActive: boolean;
  availableOptions?: FilterOption[];
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
  const handleSelect = (optionValue: string) => {
    if (isMultiSelect) {
      const newSelection = selectedOptions.includes(optionValue)
        ? selectedOptions.filter((item) => item !== optionValue)
        : [...selectedOptions, optionValue];
      onChange(newSelection);
    } else {
      onChange([optionValue]);
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
    if (selectedOptions.length === 1) {
        const selectedOption = options?.find(opt => {
            const value = typeof opt === 'string' ? opt : opt.value;
            return value === selectedOptions[0];
        });
        if (selectedOption && typeof selectedOption !== 'string' && selectedOption.label) {
            // If we have a rich label, we might want a simpler text label for the button
            // For now, let's just use the value, which is the simple string.
            return selectedOptions[0];
        }
        return selectedOptions[0];
    }
    return `${selectedOptions.length} selected`;
  };

  const availableValues = availableOptions?.map(opt => typeof opt === 'string' ? opt : opt.value);

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
          options.map((option) => {
            const value = typeof option === 'string' ? option : option.value;
            const displayLabel = typeof option === 'string' ? option : option.label;

            return (
              <Dropdown.ItemText key={value} onClick={(e) => e.stopPropagation()} className={styles.dropdownItemText}>
                <Form.Check
                  type={isMultiSelect ? 'checkbox' : 'radio'}
                  id={`${label}-${value}`}
                  label={displayLabel}
                  checked={selectedOptions.includes(value)}
                  onChange={() => handleSelect(value)}
                  name={isMultiSelect ? value : label}
                  disabled={!selectedOptions.includes(value) && availableValues && !availableValues.includes(value)}
                  className={styles.formCheckInput}
                />
              </Dropdown.ItemText>
            );
          })}
        {children && <div className="p-3"  onClick={(e) => e.stopPropagation()}>{children}</div>}
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default FilterChip;
