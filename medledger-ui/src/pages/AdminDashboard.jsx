// src/pages/AdminDashboard.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Container, Navbar, Nav,
  Table, Row, Col,
  Alert, Spinner, Form
} from 'react-bootstrap';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import Button from '../components/Button';

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // --- State for patient list ---
  const [patients, setPatients]     = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError]     = useState('');

  // --- State for create form ---
  const [form, setForm]         = useState({
    name: '', birthDate: '', username: '', password: ''
  });
  const [formError, setFormError]     = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  // 1) Fetch all patients
  const fetchPatients = useCallback(async () => {
    setLoadingList(true);
    setListError('');
    try {
      const resp = await api.get('/patients');
      setPatients(resp.data.patients || []);
    } catch (err) {
      setListError(err.response?.data?.detail || err.message);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  // 2) Form handlers
  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setFormError(''); setFormSuccess('');
  };

  const handleCreate = async e => {
    e.preventDefault();
    setFormError(''); setFormSuccess('');
    try {
      const payload = {
        name:      form.name,
        birthDate: form.birthDate,
        username:  form.username,
        password:  form.password
      };
      const resp = await api.post('/patients/create', payload);
      setFormSuccess(`Created patient ID=${resp.data.id}`);
      setForm({ name: '', birthDate: '', username: '', password: '' });
      await fetchPatients();
    } catch (err) {
      setFormError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async id => {
    if (!window.confirm(`Delete patient ${id}?`)) return;
    try {
      await api.delete(`/patients/delete/${id}`);
      await fetchPatients();
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    }
  };

  return (
    <>
      <Navbar bg="dark" variant="dark" expand="lg">
        <Container>
          <Navbar.Brand onClick={() => navigate('/')}>
            MedLedger
          </Navbar.Brand>
          <Nav className="ms-auto">
            <Nav.Link onClick={logout}>Logout</Nav.Link>
          </Nav>
        </Container>
      </Navbar>

      <Container className="mt-4">
        <h2>Admin Dashboard</h2>
        <p>Welcome, {user?.name || 'Admin'}!</p>

        {/* Create Patient */}
        <h4>Create New Patient</h4>
        {formError   && <Alert variant="danger">{formError}</Alert>}
        {formSuccess && <Alert variant="success">{formSuccess}</Alert>}
        <Form onSubmit={handleCreate}>
          <Row className="align-items-end">
            <Col md={4}>
              <Form.Group controlId="name">
                <Form.Label>Full Name</Form.Label>
                <Form.Control
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="e.g. John Doe"
                  required
                />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group controlId="birthDate">
                <Form.Label>Birth Date</Form.Label>
                <Form.Control
                  type="date"
                  name="birthDate"
                  value={form.birthDate}
                  onChange={handleChange}
                  required
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group controlId="username">
                <Form.Label>Username</Form.Label>
                <Form.Control
                  name="username"
                  value={form.username}
                  onChange={handleChange}
                  placeholder="login username"
                  required
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group controlId="password">
                <Form.Label>Password</Form.Label>
                <Form.Control
                  type="password"
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="login password"
                  required
                />
              </Form.Group>
            </Col>
          </Row>
          <Button type="submit" variant="success" className="mt-3">
            Create Patient
          </Button>
        </Form>

        {/* List & Actions */}
        <Row className="mt-5 mb-2">
          <Col><h4>Existing Patients</h4></Col>
          <Col className="text-end">
            <Button variant="secondary" onClick={fetchPatients}>
              Refresh List
            </Button>
          </Col>
        </Row>

        {loadingList && <Spinner animation="border" />}
        {listError   && <Alert variant="danger">{listError}</Alert>}

        {!loadingList && !listError && (
          <Table striped bordered hover>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Birth Date</th>
                <th>Username</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map(p => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>
                    {p.name?.map(n =>
                      `${n.given?.join(' ')} ${n.family}`
                    ).join(', ')}
                  </td>
                  <td>{p.birthDate}</td>
                  <td>
                    {p.identifier?.find(i =>
                      i.system === 'http://medledger.example.org/username'
                    )?.value || '—'}
                  </td>
                  <td>
                    <Link to={`/dashboard/admin/patient/${p.id}`}>
                      View / Modify
                    </Link>
                    {' | '}
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(p.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Container>
    </>
  );
}
