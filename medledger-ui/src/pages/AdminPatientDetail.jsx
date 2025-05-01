// src/pages/AdminPatientDetail.jsx
import React, { useEffect, useState } from 'react';
import {
  Container, Navbar, Nav,
  Spinner, Alert, Form, Button, Card
} from 'react-bootstrap';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';

export default function AdminPatientDetail() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { id } = useParams();

  const [patient, setPatient]   = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [saving, setSaving]     = useState(false);
  const [success, setSuccess]   = useState('');

  // form state for new fields
  const [gender, setGender]         = useState('');
  const [phone, setPhone]           = useState('');
  const [email, setEmail]           = useState('');
  const [address, setAddress]       = useState({
    line: '', city: '', state: '', postalCode: '', country: ''
  });
  const [emContactName, setEmName]  = useState('');
  const [emContactPhone, setEmPhone]= useState('');

  useEffect(() => {
    async function load() {
      try {
        const resp = await api.get(`/patients/${id}`);
        const p = resp.data;
        setPatient(p);
        // prefill form fields if present:
        setGender(p.gender || '');
        const tel = p.telecom || [];
        setPhone(
          (tel.find(t=>t.system==='phone')||{}).value || ''
        );
        setEmail(
          (tel.find(t=>t.system==='email')||{}).value || ''
        );
        const addr = (p.address && p.address[0]) || {};
        setAddress({
          line: (addr.line||[]).join(' '),
          city: addr.city||'',
          state: addr.state||'',
          postalCode: addr.postalCode||'',
          country: addr.country||'',
        });
        const ct = (p.contact && p.contact[0]) || {};
        setEmName(ct.name?.text||'');
        setEmPhone(
          (ct.telecom||[]).find(t=>t.system==='phone')?.value || ''
        );
      } catch (e) {
        console.error(e);
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleSave = async () => {
    setSaving(true);
    setError(''); setSuccess('');
    // build the update payload:
    const updated = {
      resourceType: 'Patient',
      // preserve name / birthDate / id from original:
      id: patient.id,
      name: patient.name,
      birthDate: patient.birthDate,
      gender,
      telecom: [
        { system:'phone', value: phone, use:'home' },
        { system:'email', value: email, use:'home' }
      ].filter(x=>x.value),
      address: [{
        line: address.line ? [address.line] : [],
        city: address.city,
        state: address.state,
        postalCode: address.postalCode,
        country: address.country
      }],
      contact: emContactName || emContactPhone
        ? [{
            name: { text: emContactName },
            telecom: emContactPhone
              ? [{ system:'phone', value: emContactPhone }]
              : []
          }]
        : []
    };

    try {
      const resp = await api.put(`/patients/update/${id}`, updated);
      setSuccess(`Saved!`);
      // refresh:
      const updatedResp = await api.get(`/patients/${id}`);
      setPatient(updatedResp.data);
    } catch (e) {
      console.error(e);
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
          <Navbar.Brand onClick={() => nav('/dashboard/admin')}>← Back</Navbar.Brand>
          <Nav className="ms-auto">
            <Nav.Link onClick={logout}>Logout</Nav.Link>
          </Nav>
        </Container>
      </Navbar>

      <Container className="mt-4">
        <h2>Admin: Edit Patient {id}</h2>
        {error   && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <Card className="p-3 mb-4" style={{ maxWidth: 600 }}>
          <Card.Title>Demographics & Contact</Card.Title>

          <Form.Group className="mb-2">
            <Form.Label>Gender</Form.Label>
            <Form.Select value={gender} onChange={e=>setGender(e.target.value)}>
              <option value="">— select —</option>
              <option>male</option>
              <option>female</option>
              <option>other</option>
              <option>unknown</option>
            </Form.Select>
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label>Address</Form.Label>
            <Form.Control
              placeholder="Street, number"
              className="mb-1"
              value={address.line}
              onChange={e=>setAddress({...address, line:e.target.value})}
            />
            <div className="d-flex mb-1">
              <Form.Control
                placeholder="City"
                className="me-2"
                value={address.city}
                onChange={e=>setAddress({...address, city:e.target.value})}
              />
              <Form.Control
                placeholder="State"
                className="me-2"
                value={address.state}
                onChange={e=>setAddress({...address, state:e.target.value})}
              />
              <Form.Control
                placeholder="Postal"
                className="me-2"
                value={address.postalCode}
                onChange={e=>setAddress({...address, postalCode:e.target.value})}
              />
              <Form.Control
                placeholder="Country"
                value={address.country}
                onChange={e=>setAddress({...address, country:e.target.value})}
              />
            </div>
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label>Phone</Form.Label>
            <Form.Control
              type="tel"
              placeholder="e.g. 555-1234"
              value={phone}
              onChange={e=>setPhone(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label>Email</Form.Label>
            <Form.Control
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e=>setEmail(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label>Emergency Contact Name</Form.Label>
            <Form.Control
              placeholder="Name"
              value={emContactName}
              onChange={e=>setEmName(e.target.value)}
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Emergency Contact Phone</Form.Label>
            <Form.Control
              type="tel"
              placeholder="Phone"
              value={emContactPhone}
              onChange={e=>setEmPhone(e.target.value)}
            />
          </Form.Group>

          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save Changes'}
          </Button>
        </Card>
      </Container>
    </>
  );
}
