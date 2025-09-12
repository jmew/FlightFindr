export function parseMultiCityMessage(message: string) {
  const startMatch = message.match(/I want to start in (.*?) and end in (.*?)\./);
  const startLocation = startMatch ? startMatch[1] : '';
  const endLocation = startMatch ? startMatch[2] : '';

  const stopsMatch = message.match(/I want to visit the following places: (.*?)\./);
  const intermediateStops = stopsMatch ? stopsMatch[1].split(', ') : [];

  const datesMatch = message.match(/I want to travel between ([\d-]+) and ([\d-]+)\./);
  const startDate = datesMatch ? datesMatch[1] : '';
  const endDate = datesMatch ? datesMatch[2] : '';

  const maxLengthMatch = message.match(/maximum trip length is (.*?) days/);
  const maxLength = maxLengthMatch ? maxLengthMatch[1] : '';

  const flexibleMatch = message.match(/The order of the intermediate stops is flexible\. /);
  const flexible = !!flexibleMatch;

  const constraintsMatch = message.match(/Please also consider the following constraints: (.*)/);
  const constraints = constraintsMatch ? constraintsMatch[1] : '';

  return { startLocation, endLocation, intermediateStops, startDate, endDate, maxLength, constraints, flexible };
}
