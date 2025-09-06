import React, { useState, useEffect } from 'react';
import { FaPlaneDeparture, FaPlaneArrival, FaCalendarAlt, FaClock, FaCity, FaPlus, FaTrash } from 'react-icons/fa';
import { Tabs, Tab, Form, Button, Row, Col, InputGroup } from 'react-bootstrap';
import './WelcomeScreen.css';

interface WelcomeScreenProps {
  handleSendMessage: (message: string) => void;
  isChatEmpty: boolean;
}

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ handleSendMessage, isChatEmpty }) => {
  const [key, setKey] = useState('single-flight');

  // State for multi-city form
  const [startLocation, setStartLocation] = useState('');
  const [endLocation, setEndLocation] = useState('');
  const [intermediateStops, setIntermediateStops] = useState(['']);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [maxLength, setMaxLength] = useState('');
  const [constraints, setConstraints] = useState('');
  const [flexible, setFlexible] = useState(false);
  const [isRoundTrip, setIsRoundTrip] = useState(true);

  useEffect(() => {
    if (isRoundTrip) {
      setEndLocation(startLocation);
    }
  }, [isRoundTrip, startLocation]);

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

  const handleMultiCitySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const finalEndLocation = isRoundTrip ? startLocation : endLocation;
    let message = `Find a multi-city trip for me. `;
    message += `I want to start in ${startLocation} and end in ${finalEndLocation}. `;
    if (intermediateStops.length > 0 && intermediateStops[0] !== '') {
      message += `I want to visit the following places: ${intermediateStops.join(', ')}. `;
    }
    message += `I want to travel between ${startDate} and ${endDate}, with a maximum trip length of ${maxLength} days. `;
    if (flexible) {
      message += `The order of the intermediate stops is flexible. `;
    }
    if (constraints) {
      message += `Please also consider the following constraints: ${constraints}`;
    }
    handleSendMessage(message);
  };


  if (!isChatEmpty) {
    return null; // Don't render if chat has started
  }

  return (
    <div className="welcome-container">
      <h1 className="welcome-title">
        Meet <span className="welcome-title-name">Miles</span>, your AI-powered flight finder
      </h1>
      <div className="search-form-container">
        <Tabs
          id="search-tabs"
          activeKey={key}
          onSelect={(k) => setKey(k || 'single-flight')}
          className="mb-3"
          justify
        >
          <Tab eventKey="single-flight" title="One-way / Round-trip">
            <p className="text-muted text-center">
              Start a conversation below to find the best flight deals. For example: "Find me a business class flight from SFO to Tokyo in the next 3 months"
            </p>
          </Tab>
          <Tab eventKey="multi-city" title="Multi-City Itinerary">
            <Form onSubmit={handleMultiCitySubmit}>
              <Row className="mb-3">
                <Col md={6}>
                  <InputGroup>
                    <InputGroup.Text><FaPlaneDeparture /></InputGroup.Text>
                    <Form.Control
                      type="text"
                      placeholder="From"
                      value={startLocation}
                      onChange={(e) => setStartLocation(e.target.value)}
                      required
                    />
                  </InputGroup>
                </Col>
                <Col md={6}>
                  <InputGroup>
                    <InputGroup.Text><FaPlaneArrival /></InputGroup.Text>
                    <Form.Control
                      type="text"
                      placeholder="To (optional)"
                      value={endLocation}
                      onChange={(e) => setEndLocation(e.target.value)}
                      disabled={isRoundTrip}
                    />
                  </InputGroup>
                </Col>
              </Row>

              <Form.Group className="mb-3">
                <Form.Check 
                  type="checkbox"
                  label="Round trip"
                  id="round-trip-checkbox"
                  checked={isRoundTrip}
                  onChange={(e) => setIsRoundTrip(e.target.checked)}
                />
              </Form.Group>

              {intermediateStops.map((stop, index) => (
                <Row key={index} className="mb-2 align-items-center leg-row">
                  <Col md={10}>
                    <InputGroup>
                      <InputGroup.Text><FaCity /></InputGroup.Text>
                      <Form.Control
                        type="text"
                        placeholder={`Stop ${index + 1}`}
                        value={stop}
                        onChange={(e) => handleStopChange(index, e.target.value)}
                        required
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
                  <Button variant="outline-primary" size="sm" onClick={handleAddStop}>
                    <FaPlus /> Add stop
                  </Button>
                </Col>
              </Row>

              <Row className="mb-3">
                <Col md={4}>
                  <InputGroup>
                    <InputGroup.Text><FaCalendarAlt /></InputGroup.Text>
                    <Form.Control
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      required
                    />
                  </InputGroup>
                </Col>
                <Col md={4}>
                  <InputGroup>
                    <InputGroup.Text><FaCalendarAlt /></InputGroup.Text>
                    <Form.Control
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      required
                    />
                  </InputGroup>
                </Col>
                <Col md={4}>
                   <InputGroup>
                    <InputGroup.Text><FaClock /></InputGroup.Text>
                    <Form.Control
                      type="number"
                      placeholder="Max trip length (days)"
                      value={maxLength}
                      onChange={(e) => setMaxLength(e.target.value)}
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
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Check 
                  type="checkbox"
                  label="Let us pick the order of the intermediate stops for the best itinerary"
                  id="flexible-itinerary-checkbox"
                  checked={flexible}
                  onChange={(e) => setFlexible(e.target.checked)}
                />
              </Form.Group>

              <div className="d-grid">
                <Button variant="primary" type="submit">
                  Find Itineraries
                </Button>
              </div>
            </Form>
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};

export default WelcomeScreen;