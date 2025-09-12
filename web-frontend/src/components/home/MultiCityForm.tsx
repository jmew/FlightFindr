import React, { useState, useEffect, useRef } from 'react';
import { FaPlaneDeparture, FaPlaneArrival, FaCalendarAlt, FaClock, FaCity, FaPlus, FaTrash } from 'react-icons/fa';
import { Form, Button, Row, Col, InputGroup } from 'react-bootstrap';
import styles from './WelcomeScreen.module.css';

interface MultiCityFormProps {
  handleSendMessage: (message: string) => void;
}

const MultiCityForm: React.FC<MultiCityFormProps> = ({ handleSendMessage }) => {
  const [startLocation, setStartLocation] = useState('');
  const [endLocation, setEndLocation] = useState('');
  const [intermediateStops, setIntermediateStops] = useState(['']);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [minLength, setMinLength] = useState('');
  const [maxLength, setMaxLength] = useState('');
  const [constraints, setConstraints] = useState('');
  const [isRoundTrip, setIsRoundTrip] = useState(true);
  const [startDateType, setStartDateType] = useState('text');
  const [endDateType, setEndDateType] = useState('text');

  const startDateRef = useRef<HTMLInputElement>(null);
  const endDateRef = useRef<HTMLInputElement>(null);

  const [maxEndDate, setMaxEndDate] = useState('');

  useEffect(() => {
    if (isRoundTrip) {
      setEndLocation(startLocation);
    }
  }, [isRoundTrip, startLocation]);

  useEffect(() => {
    if (startDate) {
      const start = new Date(startDate);
      const maxDate = new Date(start.getTime() + 21 * 24 * 60 * 60 * 1000); // 21 days later
      const formattedMaxDate = maxDate.toISOString().split('T')[0];
      setMaxEndDate(formattedMaxDate);

      // If endDate is beyond the new maxDate, adjust it
      if (endDate && endDate > formattedMaxDate) {
        setEndDate(formattedMaxDate);
      }
    } else {
      setMaxEndDate(''); // Clear maxEndDate if startDate is cleared
    }
  }, [startDate, endDate]);

  const handleAddStop = () => {
    setIntermediateStops([...intermediateStops, '']);
  };

  const handleRemoveStop = (index: number) => {
    const newStops = intermediateStops.filter((_, i) => i !== index);
    setIntermediateStops(newStops);
  };

  const handleStopChange = (index: number, value: string) => {
    const newStops = [...intermediateStops];
    newStops[index] = value;
    setIntermediateStops(newStops);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const finalEndLocation = isRoundTrip ? startLocation : endLocation;
    let message = `Find a multi-city trip for me. `;
    message += `I want to start in ${startLocation} and end in ${finalEndLocation}. `;
    if (intermediateStops.length > 0 && intermediateStops[0] !== '') {
      message += `I want to visit the following places: ${intermediateStops.join(', ')}. `;
    }
    message += `I want to travel between ${startDate} and ${endDate}. `;
    if (minLength) {
      message += `The minimum trip length is ${minLength} days. `;
    }
    if (maxLength) {
      message += `The maximum trip length is ${maxLength} days. `;
    }
    if (constraints) {
      message += `Please also consider the following constraints: ${constraints}`;
    }
    handleSendMessage(message);
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <Form onSubmit={handleSubmit}>
      <Row className={`mb-3 ${styles.formRow}`}>
        <Col md={6}>
          <InputGroup>
            <InputGroup.Text className={styles.inputGroupText}><FaPlaneDeparture /></InputGroup.Text>
            <Form.Control
              type="text"
              placeholder="From"
              value={startLocation}
              onChange={(e) => setStartLocation(e.target.value)}
              required
              className={styles.formControl}
            />
          </InputGroup>
        </Col>
        <Col md={6}>
          <InputGroup>
            <InputGroup.Text className={styles.inputGroupText}><FaPlaneArrival /></InputGroup.Text>
            <Form.Control
              type="text"
              placeholder="To (optional)"
              value={endLocation}
              onChange={(e) => setEndLocation(e.target.value)}
              disabled={isRoundTrip}
              className={styles.formControl}
            />
          </InputGroup>
        </Col>
      </Row>

      <Form.Group className="mb-3">
        <Form.Check 
          type="checkbox"
          label="I want my last flight to return back to where I started"
          id="round-trip-checkbox"
          checked={isRoundTrip}
          onChange={(e) => setIsRoundTrip(e.target.checked)}
        />
      </Form.Group>

      {intermediateStops.map((stop, index) => (
        <Row key={index} className={`mb-2 align-items-center ${styles.legRow}`}>
          <Col md={10}>
            <InputGroup>
              <InputGroup.Text className={styles.inputGroupText}><FaCity /></InputGroup.Text>
              <Form.Control
                type="text"
                placeholder={`Stop ${index + 1}`}
                value={stop}
                onChange={(e) => handleStopChange(index, e.target.value)}
                required
                className={styles.formControl}
              />
            </InputGroup>
          </Col>
          <Col md={2} className="text-end">
            <Button variant="danger" size="sm" onClick={() => handleRemoveStop(index)}>
              <FaTrash />
            </Button>
          </Col>
        </Row>
      ))}

      <Row className="mb-3">
        <Col xs={12}>
          <Button variant="outline-primary" size="sm" onClick={handleAddStop} disabled={intermediateStops.length >= 6}>
            <FaPlus /> Add stop
          </Button>
        </Col>
      </Row>

      <Row className={`mb-3 ${styles.formRow}`}>
        <Col md={6}>
          <InputGroup onClick={() => startDateRef.current?.focus()}>
            <InputGroup.Text className={styles.inputGroupText}><FaCalendarAlt /></InputGroup.Text>
            <Form.Control
              type={startDateType}
              onFocus={() => {
                setStartDateType('date');
                setTimeout(() => startDateRef.current?.showPicker(), 0);
              }}
              onBlur={() => !startDate && setStartDateType('text')}
              placeholder="Start date"
              min={today}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className={styles.formControl}
              ref={startDateRef}
            />
          </InputGroup>
        </Col>
        <Col md={6}>
          <InputGroup onClick={() => endDateRef.current?.focus()}>
            <InputGroup.Text className={styles.inputGroupText}><FaCalendarAlt /></InputGroup.Text>
            <Form.Control
              type={endDateType}
              onFocus={() => {
                setEndDateType('date');
                setTimeout(() => endDateRef.current?.showPicker(), 0);
              }}
              onBlur={() => !endDate && setEndDateType('text')}
              placeholder="End date"
              min={startDate || today}
              max={maxEndDate}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className={styles.formControl}
              ref={endDateRef}
            />
          </InputGroup>
        </Col>
      </Row>

      <Row className={`mb-3 ${styles.formRow}`}>
        <Col md={6}>
           <InputGroup>
            <InputGroup.Text className={styles.inputGroupText}><FaClock /></InputGroup.Text>
            <Form.Control
              type="number"
              placeholder="Min trip length (days)"
              value={minLength}
              onChange={(e) => setMinLength(e.target.value)}
              className={styles.formControl}
            />
          </InputGroup>
        </Col>
        <Col md={6}>
           <InputGroup>
            <InputGroup.Text className={styles.inputGroupText}><FaClock /></InputGroup.Text>
            <Form.Control
              type="number"
              placeholder="Max trip length (days)"
              value={maxLength}
              onChange={(e) => setMaxLength(e.target.value)}
              className={styles.formControl}
            />
          </InputGroup>
        </Col>
      </Row>

      <Form.Group className="mb-3">
        <Form.Control
          as="textarea"
          rows={2}
          placeholder="Optional constraints (e.g., 'I prefer morning flights', 'Visit Paris before Rome')"
          value={constraints}
          onChange={(e) => setConstraints(e.target.value)}
          className={styles.formControl}
        />
      </Form.Group>

      <div className="d-grid">
        <Button variant="primary" type="submit">
          Find Itineraries
        </Button>
      </div>
    </Form>
  );
}

export default MultiCityForm;
