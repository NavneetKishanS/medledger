// src/pages/DoctorDashboard.jsx

import React, { useState, useEffect, useCallback } from 'react';
import {
  Container, Navbar, Nav, Form, Spinner, Alert, Row, Col, Card
} from 'react-bootstrap';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import Button from '../components/Button';
import { FiUser, FiCalendar, FiLogOut } from 'react-icons/fi';

export default function DoctorDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [q, setQ] = useState('');
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchPatients = useCallback(async (searchQ = '') => {
    setLoading(true);
    setError('');
    try {
      const resp = await api.get('/doctor/patients', {
        params: searchQ ? { q: searchQ } : {}
      });
      setPatients(resp.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const handleSearch = e => {
    e.preventDefault();
    fetchPatients(q.trim());
  };

  const formatName = nameObj => {
    if (!nameObj || nameObj.length === 0) return '(no name)';
    return nameObj.map(n => `${n.given?.join(' ') || ''} ${n.family}`).join(', ');
  };

  return (
    <div style={{ background: '#f2f2f2', minHeight: '100vh' }}>
      <Navbar style={{ backgroundColor: '#00b8a9' }} variant="dark" expand="lg">
        <Container>
          <Navbar.Brand
            onClick={() => navigate('/')}
            style={{ cursor: 'pointer', fontWeight: 600 }}
          >
            MedLedger
          </Navbar.Brand>
          <Nav className="ms-auto">
            <Button variant="light" onClick={logout}>
              <FiLogOut className="me-2" /> Logout
            </Button>
          </Nav>
        </Container>
      </Navbar>

      <Container className="py-4">
        <h2 className="fw-bold mb-1">Doctor Dashboard</h2>
        <p className="text-muted mb-4">Welcome, Dr. {user?.name || '(Unknown)'}</p>

        <Form className="d-flex mb-4" onSubmit={handleSearch}>
          <Form.Control
            placeholder="Search by ID or name"
            value={q}
            onChange={e => setQ(e.target.value)}
            className="shadow-sm"
          />
          <Button type="submit" className="ms-2" variant="info">
            Search
          </Button>
        </Form>

        {loading && (
          <div className="text-center my-5">
            <Spinner animation="border" />
          </div>
        )}
        {error && <Alert variant="danger">{error}</Alert>}

        {!loading && !error && patients.length === 0 && (
          <Alert variant="info">No patients found.</Alert>
        )}

        <Row className="g-4">
          {patients.map(p => (
            <Col md={6} lg={4} key={p.id}>
              <Card
                className="shadow-sm h-100"
                style={{
                  transition: 'transform 0.2s ease',
                  borderRadius: '1rem',
                  cursor: 'pointer'
                }}
                onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.03)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
              >
                <Card.Body>
                  <Card.Title>
                    <FiUser className="me-2 text-primary" />
                    {formatName(p.name)}
                  </Card.Title>
                  <Card.Text><strong>ID:</strong> {p.id}</Card.Text>
                  <Card.Text>
                    <FiCalendar className="me-2 text-secondary" />
                    <strong>Birth Date:</strong> {p.birthDate || '(not listed)'}
                  </Card.Text>
                  <div className="mt-3">
                    <Link to={`/dashboard/doctor/patient/${p.id}`}>
                      <Button variant="outline-primary" size="sm">
                        View Details
                      </Button>
                    </Link>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          ))}
        </Row>
      </Container>
    </div>
  );
}
