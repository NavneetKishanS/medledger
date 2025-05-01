import React, { useEffect, useState } from 'react';
import {
  Container, Navbar, Nav, Spinner, Alert,
  Row, Col, Card, ListGroup
} from 'react-bootstrap';
import Button from '../components/Button';
import ReactECharts from 'echarts-for-react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import SectionCard from '../components/SectionCard';
import {
  FaNotesMedical, FaCapsules, FaProcedures, FaHeartbeat,
  FaUser, FaSyringe, FaExclamationTriangle
} from 'react-icons/fa';

const sections = [
  { id: 'profile', label: 'Profile', icon: <FaUser /> },
  { id: 'vitals', label: 'Vitals', icon: <FaHeartbeat /> },
  { id: 'observations', label: 'Observations', icon: <FaNotesMedical /> },
  { id: 'treatments', label: 'Treatments', icon: <FaCapsules /> },
  { id: 'allergies', label: 'Allergies', icon: <FaExclamationTriangle /> },
  { id: 'conditions', label: 'Conditions', icon: <FaProcedures /> },
  { id: 'immunizations', label: 'Immunizations', icon: <FaSyringe /> }
];

export default function PatientDashboard() {
  const { logout, user } = useAuth();
  const [selectedSection, setSelectedSection] = useState('profile');

  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [vitals, setVitals] = useState([]);
  const [vitalError, setVitalError] = useState('');
  const [observations, setObservations] = useState([]);
  const [treatments, setTreatments] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [immunizations, setImmunizations] = useState([]);

  useEffect(() => {
    async function loadAll() {
      try {
        const [p, obs, trt, alr, cond, imm] = await Promise.all([
          api.get('/patients/me'),
          api.get('/patients/me/observations'),
          api.get('/patients/me/treatments'),
          api.get('/patients/me/allergies'),
          api.get('/patients/me/conditions'),
          api.get('/patients/me/immunizations')
        ]);
        setPatient(p.data);
        setObservations(obs.data);
        setTreatments(trt.data);
        setAllergies(alr.data);
        setConditions(cond.data);
        setImmunizations(imm.data);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  useEffect(() => {
    if (!patient?.id) return;
    api.get(`/vitals_raw/${patient.id}?n=10`)
      .then(res => setVitals(res.data || []))
      .catch(err => setVitalError('Failed to load vitals data.'));
  }, [patient]);

  const fullName = patient?.name?.[0]
    ? [...(patient.name[0].given || []), patient.name[0].family].join(' ')
    : '(no name)';

  const computeAge = birth => {
    const d = new Date(birth), n = new Date();
    let y = n.getFullYear() - d.getFullYear(), m = n.getMonth() - d.getMonth();
    if (m < 0) { y--; m += 12; } return `${y} yrs, ${m} mos`;
  };

  // Format mapped data
  const mappedObservations = observations.map(o => {
    const rawDate = o.payload?.effectiveDateTime || o.timestamp;
    let dateStr = '(Invalid date)';
    try { dateStr = new Date(rawDate).toLocaleDateString('en-GB'); } catch {}
    const note = o.payload?.valueString || o.payload?.code?.text || o.text || '(No note)';
    return { id: o.id || o._id?.$oid, date: dateStr, text: note };
  }).filter(o => o.date && o.text);

  const mappedTreatments = treatments.map(t => ({
    id: t.id,
    date: t.date || t.authoredOn,
    text: t.medication || t.medicationText || t.medicationCodeableConcept?.text || '(No medication)'
  })).filter(t => t.id && t.date && t.text);

  const mappedAllergies = allergies.map(a => ({
    id: a.id,
    date: a.date || a.recordedDate,
    text: a.text || a.substance?.text || a.code?.text
  })).filter(a => a.id && a.date && a.text);

  const mappedConditions = conditions.map(c => ({
    id: c.id,
    date: c.date || c.recordedDate,
    text: c.text
  })).filter(c => c.id && c.date && c.text);

  const mappedImmunizations = immunizations.map(i => ({
    id: i.id,
    date: i.date || i.occurrenceDateTime,
    text: i.text || i.vaccineCode?.text
  })).filter(i => i.id && i.date && i.text);

  const chartOption = {
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const index = params[0].dataIndex;
        const time = vitals[index]?.timestamp?.slice(11, 16);
        const anomaly = vitals[index]?.anomaly ? '🚨 Anomaly Detected' : '✅ Normal';
        return `
          <b>Time: ${time}</b><br/>
          SpO₂: ${params[0].data}<br/>
          Temp: ${params[1].data}°C<br/>
          Heart Rate: ${params[2].data} bpm<br/>
          <i>${anomaly}</i>
        `;
      }
    },
    legend: { data: ['SpO₂', 'Temperature', 'Heart Rate'] },
    xAxis: {
      type: 'category',
      data: vitals.map(v => v.timestamp?.slice(11, 16))
    },
    yAxis: { type: 'value' },
    series: [
      { name: 'SpO₂', type: 'line', data: vitals.map(v => v.spo2) },
      { name: 'Temperature', type: 'line', data: vitals.map(v => v.temperature) },
      { name: 'Heart Rate', type: 'line', data: vitals.map(v => v.heart_rate) }
    ]
  };

  return (
    <div style={{ background: '#f2f2f2', minHeight: '100vh', fontFamily: 'Segoe UI, sans-serif' }}>
      <Navbar bg="dark" variant="dark" className="px-3">
        <Navbar.Brand>MedLedger</Navbar.Brand>
        <Nav className="ms-auto align-items-center gap-2">
          <Button variant="info" onClick={logout}>Logout</Button>
          <Button variant="info" onClick={async () => {
            try {
              const token = localStorage.getItem('access_token');
              const response = await api.get(`/patients/me/report`, {
                headers: { Authorization: `Bearer ${token}` },
                responseType: 'blob'
              });
              const url = window.URL.createObjectURL(new Blob([response.data]));
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', `my_patient_report.pdf`);
              document.body.appendChild(link);
              link.click();
            } catch {
              alert('Failed to download report');
            }
          }}>
            Download Report
          </Button>
        </Nav>
      </Navbar>

      <Container fluid className="d-flex" style={{ paddingTop: '20px' }}>
        {/* Sidebar */}
        <div style={{ minWidth: '220px', background: '#00b8a9', color: 'white', padding: '1rem', borderRadius: '0 1rem 1rem 0' }}>
          <h5 className="text-white fw-bold mb-3">Sections</h5>
          <ListGroup variant="flush">
            {sections.map(sec => (
              <ListGroup.Item
                key={sec.id}
                onClick={() => setSelectedSection(sec.id)}
                style={{
                  cursor: 'pointer',
                  background: selectedSection === sec.id ? '#fff' : 'transparent',
                  color: selectedSection === sec.id ? '#00b8a9' : 'white',
                  fontWeight: selectedSection === sec.id ? '600' : '400',
                  borderRadius: '0.5rem',
                  marginBottom: '0.5rem'
                }}
              >
                {sec.icon} <span className="ms-2">{sec.label}</span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </div>

        {/* Main Content */}
        <div className="flex-grow-1 px-4 py-2">
          <h2 className="fw-bold">Patient Dashboard</h2>
          <p style={{ fontSize: '1.2rem' }}>Welcome, {fullName}</p>

          {loading && <Spinner animation="border" className="mt-4" />}
          {error && <Alert variant="danger">{error}</Alert>}

          {!loading && selectedSection === 'profile' && (
            <Card>
              <Card.Header style={{ backgroundColor: '#00b8a9', color: 'white' }}>
                <FaUser className="me-2" /> Profile
              </Card.Header>
              <Card.Body>
  <p><strong>ID:</strong> {patient?.id}</p>
  <p><strong>Name:</strong> {fullName}</p>
  <p><strong>Birth Date:</strong> {patient?.birthDate}</p>
  <p><strong>Age:</strong> {computeAge(patient?.birthDate)}</p>
  <p><strong>Email:</strong> {patient?.telecom?.find(t => t.system === 'email')?.value || 'N/A'}</p>
  <p><strong>Phone:</strong> {patient?.telecom?.find(t => t.system === 'phone')?.value || 'N/A'}</p>
  <p><strong>Address:</strong> {patient?.address?.[0]?.text || '(No address listed)'}</p>
  {patient?.contact?.some(c => c.relationship?.[0]?.text === 'emergency') && (
    <>
      <hr />
      <p><strong>Emergency Contact:</strong> {patient.contact.find(c => c.relationship?.[0]?.text === 'emergency')?.name?.text}</p>
      <p><strong>Phone:</strong> {patient.contact.find(c => c.relationship?.[0]?.text === 'emergency')?.telecom?.[0]?.value}</p>
    </>
  )}
</Card.Body>
            </Card>
          )}

          {selectedSection === 'vitals' && (
            <Card>
              <Card.Header style={{ backgroundColor: '#00b8a9', color: 'white' }}>
                <FaHeartbeat className="me-2" /> Recent Vitals
              </Card.Header>
              <Card.Body>
                {vitalError && <Alert variant="danger">{vitalError}</Alert>}
                {vitals.length > 0 ? (
                  <ReactECharts option={chartOption} style={{ height: '300px', width: '100%' }} />
                ) : (
                  <div className="text-muted">No vitals data yet.</div>
                )}
              </Card.Body>
            </Card>
          )}

          {selectedSection === 'observations' && (
            <SectionCard title="Observations" items={mappedObservations} />
          )}
          {selectedSection === 'treatments' && (
            <SectionCard title="Treatments" items={mappedTreatments} />
          )}
          {selectedSection === 'allergies' && (
            <SectionCard title="Allergies" items={mappedAllergies} />
          )}
          {selectedSection === 'conditions' && (
            <SectionCard title="Conditions" items={mappedConditions} />
          )}
          {selectedSection === 'immunizations' && (
            <SectionCard title="Immunizations" items={mappedImmunizations} />
          )}
        </div>
      </Container>
    </div>
  );
}
