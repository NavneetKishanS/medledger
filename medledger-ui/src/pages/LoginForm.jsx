// src/pages/LoginForm.jsx

import React, { useState } from 'react';
import { Container, Form, Alert, Card } from 'react-bootstrap';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import Button from '../components/Button';

export default function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { role } = useParams(); // "patient" | "doctor" | "admin"
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate(`/dashboard/${role}`);
    } catch (err) {
      console.error(err);
      setError('Login failed. Check your credentials.');
    }
  };

  return (
    <div style={{ background: '#f2f2f2', minHeight: '100vh' }}>
      <div className="text-center py-4" style={{ backgroundColor: '#00b8a9', color: 'white' }}>
        <h2 className="text-capitalize fw-bold">{role} Login</h2>
      </div>

      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
        <Card className="shadow p-4" style={{ width: '100%', maxWidth: '420px', borderRadius: '1rem' }}>
          <h4 className="mb-4 text-center text-muted fw-semibold">Enter your credentials</h4>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="username">
              <Form.Label className="fw-semibold">Username</Form.Label>
              <Form.Control
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
              />
            </Form.Group>

            <Form.Group className="mb-4" controlId="password">
              <Form.Label className="fw-semibold">Password</Form.Label>
              <Form.Control
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </Form.Group>

            <div className="d-grid">
              <Button variant="info" type="submit">
                Login
              </Button>
            </div>
          </Form>
        </Card>
      </Container>
    </div>
  );
}
