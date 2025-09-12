import React from 'react';
import { Form } from 'react-bootstrap';
import { FaAngleDoubleLeft, FaAngleLeft, FaAngleRight, FaAngleDoubleRight } from 'react-icons/fa';
import styles from './PaginationControls.module.css';

interface PaginationControlsProps {
  currentPage: number;
  itemsPerPage: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (items: number) => void;
}

const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  itemsPerPage,
  totalItems,
  onPageChange,
  onItemsPerPageChange,
}) => {
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  const handleFirstPage = () => onPageChange(1);
  const handlePrevPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };
  const handleLastPage = () => onPageChange(totalPages);

  return (
    <div className={styles.paginationContainer}>
      <div className={styles.itemsPerPageSelector}>
        <Form.Select
          value={itemsPerPage}
          onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
          aria-label="Items per page"
        >
          <option value={10}>10 per page</option>
          <option value={25}>25 per page</option>
          <option value={50}>50 per page</option>
        </Form.Select>
      </div>
      <div className={styles.pageControls}>
        <button onClick={handleFirstPage} disabled={currentPage === 1}>
          <FaAngleDoubleLeft />
        </button>
        <button onClick={handlePrevPage} disabled={currentPage === 1}>
          <FaAngleLeft />
        </button>
        <span>
          Page {currentPage} of {totalPages}
        </span>
        <button onClick={handleNextPage} disabled={currentPage === totalPages}>
          <FaAngleRight />
        </button>
        <button onClick={handleLastPage} disabled={currentPage === totalPages}>
          <FaAngleDoubleRight />
        </button>
      </div>
    </div>
  );
};

export default PaginationControls;
