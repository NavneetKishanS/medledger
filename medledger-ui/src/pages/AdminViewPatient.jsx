// src/pages/AdminViewPatient.jsx
import React, { useEffect, useState } from 'react';
import {
  Container, Navbar, Nav,
  Spinner, Alert, Form, Button
} from 'react-bootstrap';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';

export default function AdminViewPatient() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();

  const [patient, setPatient] = useState(null);
  const [form, setForm]       = useState({
    gender: '',
    phone: '',
    email: '',
    address: '',
    emergencyContactName: '',
    emergencyContactPhone: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const resp = await api.get(`/patients/${id}`);
        const res = resp.data;
        setPatient(res);

        // prefill form
        const { gender, telecom, address, contact } = res;
        let phone = '', email = '', addr = '';
        let ecName = '', ecPhone = '';

        if (telecom) {
          const ph = telecom.find(t => t.system === 'phone');
          if (ph) phone = ph.value;
          const em = telecom.find(t => t.system === 'email');
          if (em) email = em.value;
        }

        if (address && address.length) {
          addr = address[0].text;
        }

        if (contact) {
          const ec = contact.find(c =>
            c.relationship?.[0]?.text === 'emergency'
          );
          if (ec) {
            ecName = ec.name?.text || '';
            const tp = ec.telecom?.find(t => t.system === 'phone');
            if (tp) ecPhone = tp.value;
          }
        }

        setForm({
          gender: gender || '',
          phone, email, address: addr,
          emergencyContactName: ecName,
          emergencyContactPhone: ecPhone
        });
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError(''); setSuccess('');
  };

  const handleSave = async e => {
    e.preventDefault();
    setSaving(true); setError(''); setSuccess('');
    try {
      await api.put(`/patients/additional/${id}`, form);
      setSuccess('Details saved.');
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spinner animation="border" />;

  return (
    <>
      <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand onClick={() => navigate('/dashboard/admin')}>
            ← Back to List
          </Navbar.Brand>
          <Nav className="ms-auto">
            <Nav.Link onClick={logout}>Logout</Nav.Link>
          </Nav>
        </Container>
      </Navbar>

      <Container className="mt-4">
        <h2>Patient #{id}</h2>
        {error   && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        {/* core demographics read‑only */}
        {patient && (
          <div className="mb-4">
            <p><strong>Name:</strong>{' '}
              {[...(patient.name?.[0]?.given||[]), patient.name?.[0]?.family].join(' ')}
            </p>
            <p><strong>Birth Date:</strong> {patient.birthDate}</p>
            <p><strong>Username:</strong>{' '}
              {patient.identifier?.find(i => i.system.includes('username'))
                ?.value}
            </p>
          </div>
        )}

        {/* additional fields */}
        <Form onSubmit={handleSave}>
          <Form.Group controlId="gender">
            <Form.Label>Gender</Form.Label>
            <Form.Select
              name="gender"
              value={form.gender}
              onChange={handleChange}
            >
              <option value="">(none)</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="unknown">Unknown</option>
            </Form.Select>
          </Form.Group>

          <Form.Group controlId="phone" className="mt-3">
            <Form.Label>Phone</Form.Label>
            <Form.Control
              name="phone"
              value={form.phone}
              onChange={handleChange}
            />
          </Form.Group>

          <Form.Group controlId="email" className="mt-3">
            <Form.Label>E‑mail</Form.Label>
            <Form.Control
              name="email"
              value={form.email}
              onChange={handleChange}
            />
          </Form.Group>

          <Form.Group controlId="address" className="mt-3">
            <Form.Label>Address</Form.Label>
            <Form.Control
              name="address"
              value={form.address}
              onChange={handleChange}
            />
          </Form.Group>

          <Form.Group controlId="emergencyContactName" className="mt-3">
            <Form.Label>Emergency Contact Name</Form.Label>
            <Form.Control
              name="emergencyContactName"
              value={form.emergencyContactName}
              onChange={handleChange}
            />
          </Form.Group>

          <Form.Group controlId="emergencyContactPhone" className="mt-3">
            <Form.Label>Emergency Contact Phone</Form.Label>
            <Form.Control
              name="emergencyContactPhone"
              value={form.emergencyContactPhone}
              onChange={handleChange}
            />
          </Form.Group>

          <Button type="submit" disabled={saving} className="mt-4">
            {saving ? 'Saving…' : 'Save Details'}
          </Button>
        </Form>
      </Container>
    </>
  );
}
