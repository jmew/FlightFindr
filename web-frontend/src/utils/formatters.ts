export const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return 'N/A';
  try {
    // Adding T00:00:00 ensures the date is parsed in UTC, preventing off-by-one day errors
    const date = new Date(dateString + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  } catch (e) {
    return 'Invalid Date';
  }
};

export const formatTime = (isoString: string | undefined): string => {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch (e) {
    return 'Invalid Date';
  }
};

export const formatFlightTimes = (departureISO: string, arrivalISO: string) => {
  if (!departureISO || !arrivalISO) {
    return { departureTime: 'N/A', arrivalTime: 'N/A', isNextDay: false };
  }

  const departure = new Date(departureISO);
  const arrival = new Date(arrivalISO);

  const formatOptions: Intl.DateTimeFormatOptions = {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  };

  const departureTime = departure.toLocaleTimeString('en-US', formatOptions);
  const arrivalTime = arrival.toLocaleTimeString('en-US', formatOptions);

  // Check if the arrival date is on a different calendar day than the departure date
  const isNextDay =
    arrival.getFullYear() > departure.getFullYear() ||
    arrival.getMonth() > departure.getMonth() ||
    arrival.getDate() > departure.getDate();

  return {
    departureTime,
    arrivalTime,
    isNextDay,
  };
};


export const formatDuration = (minutes: number | undefined): string => {
  if (minutes === undefined || minutes === null) return 'N/A';
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
};
