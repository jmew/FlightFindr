import { useState, useMemo } from 'react';
import { DataGrid, type SortColumn } from 'react-data-grid';
import 'react-data-grid/lib/styles.css';
import { FiMaximize } from 'react-icons/fi';
import FullScreenModal from './FlightDealsTable/index';

export interface FlightDealRow {
  id: number;
  date: string;
  airline: string;
  route: string;
  class: string;
  points: number;
  fees: string;
  departureTime: string;
  arrivalTime: string;
  flightNumbers: string;
}

interface FlightDealsTableProps {
  deals: FlightDealRow[];
}

const columns = [
  { key: 'date', name: 'Date', sortable: true },
  { key: 'airline', name: 'Airline', sortable: true },
  { key: 'route', name: 'Route', sortable: true },
  { key: 'class', name: 'Class', sortable: true },
  { key: 'points', name: 'Points', sortable: true },
  { key: 'fees', name: 'Fees', sortable: true },
  { key: 'departureTime', name: 'Departure', sortable: true },
  { key: 'arrivalTime', name: 'Arrival', sortable: true },
  { key: 'flightNumbers', name: 'Flights', sortable: true },
];

const FlightDealsTable = ({ deals }: FlightDealsTableProps) => {
  const [sortColumns, setSortColumns] = useState<readonly SortColumn[]>([
    { columnKey: 'points', direction: 'ASC' },
  ]);
  const [airlineFilter, setAirlineFilter] = useState('');
  const [routeFilter, setRouteFilter] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [isFullScreen, setIsFullScreen] = useState(false);

  const filteredRows = useMemo(() => {
    return deals.filter((row) => {
      return (
        row.airline.toLowerCase().includes(airlineFilter.toLowerCase()) &&
        row.route.toLowerCase().includes(routeFilter.toLowerCase()) &&
        row.class.toLowerCase().includes(classFilter.toLowerCase())
      );
    });
  }, [deals, airlineFilter, routeFilter, classFilter]);

  const sortedRows = useMemo((): readonly FlightDealRow[] => {
    if (sortColumns.length === 0) return filteredRows;

    const { columnKey, direction } = sortColumns[0];

    return [...filteredRows].sort((a, b) => {
      const aValue = a[columnKey as keyof FlightDealRow];
      const bValue = b[columnKey as keyof FlightDealRow];

      if (aValue > bValue) {
        return direction === 'ASC' ? 1 : -1;
      }
      if (bValue > aValue) {
        return direction === 'ASC' ? -1 : 1;
      }
      return 0;
    });
  }, [filteredRows, sortColumns]);

  const table = (
    <DataGrid
      columns={columns}
      rows={sortedRows}
      sortColumns={sortColumns}
      onSortColumnsChange={setSortColumns}
      className="rdg-dark"
      style={{ height: '100%' }}
    />
  );

  return (
    <div>
      <div className="table-toolbar">
        <div className="filter-container">
          <input
            type="text"
            placeholder="Filter by Airline"
            value={airlineFilter}
            onChange={(e) => setAirlineFilter(e.target.value)}
            className="filter-input"
          />
          <input
            type="text"
            placeholder="Filter by Route"
            value={routeFilter}
            onChange={(e) => setRouteFilter(e.target.value)}
            className="filter-input"
          />
          <input
            type="text"
            placeholder="Filter by Class"
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
            className="filter-input"
          />
        </div>
        <button
          className="fullscreen-button"
          onClick={() => setIsFullScreen(true)}
        >
          <FiMaximize />
        </button>
      </div>
      <div style={{ height: 400 }}>{table}</div>
      {isFullScreen && (
        <FullScreenModal onClose={() => setIsFullScreen(false)}>
          {table}
        </FullScreenModal>
      )}
    </div>
  );
};

export default FlightDealsTable;
