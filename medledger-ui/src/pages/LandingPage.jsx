// src/pages/LandingPage.jsx
import React from 'react';
import { Container, Row, Col, Button } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page d-flex align-items-center justify-content-center">
      <Container className="text-center">
        <Row>
          <Col>
            <h1 className="display-4">Welcome to MedLedger</h1>
            <p className="lead mt-3">
              Securely manage and access your health records anytime, anywhere.
            </p>
            <Button variant="success" size="lg" onClick={() => navigate('/login')}>
              Login
            </Button>
          </Col>
        </Row>
      </Container>
    </div>
  );
}

export default LandingPage;
