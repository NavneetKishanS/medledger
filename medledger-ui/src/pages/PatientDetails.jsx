import React, { useEffect, useState } from 'react';
import {
  Container, Navbar, Nav, Spinner, Alert,
  Card, Form, Table, ListGroup
} from 'react-bootstrap';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import Button from '../components/Button';
import ReactECharts from 'echarts-for-react';

import {
  FiUser, FiCalendar, FiAlertTriangle, FiDownload, FiArrowLeft
} from 'react-icons/fi';
import {
  FaNotesMedical, FaCapsules, FaProcedures, FaHeartbeat
} from 'react-icons/fa';
import { GiSyringe } from 'react-icons/gi';

export default function PatientDetails() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();

  const [selectedSection, setSelectedSection] = useState('profile');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  const [patient, setPatient] = useState(null);
  const [vitals, setVitals] = useState([]);
  const [observations, setObservations] = useState([]);
  const [treatments, setTreatments] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [immunizations, setImmunizations] = useState([]);

  const [note, setNote] = useState('');
  const [medText, setMedText] = useState('');
  const [allergyText, setAllergyText] = useState('');
  const [conditionText, setConditionText] = useState('');
  const [immunizationText, setImmunizationText] = useState('');

  const formatDate = d => {
    if (!d) return '';
    const date = new Date(d);
    return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
  };

  useEffect(() => {
    async function loadAll() {
      try {
        const [p, obs, trt, alr, cond, imm, vit] = await Promise.all([
          api.get(`/doctor/patients/${id}`),
          api.get(`/doctor/observations/${id}`),
          api.get(`/doctor/treatments/${id}`),
          api.get(`/doctor/allergies/${id}`),
          api.get(`/doctor/conditions/${id}`),
          api.get(`/doctor/immunizations/${id}`),
          api.get(`/vitals_raw/${id}?n=10`)
        ]);
        setPatient(p.data);
        setObservations(obs.data);
        setTreatments(trt.data);
        setAllergies(alr.data);
        setConditions(cond.data);
        setImmunizations(imm.data);
        setVitals(vit.data);
      } catch (e) {
        setErr(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, [id]);

  const handleDownloadReport = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await api.get(`/doctor/patients/${id}/report`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'patient_report.pdf');
      document.body.appendChild(link);
      link.click();
    } catch {
      alert('Failed to download report');
    }
  };

  const addItem = async (section, value, setter, reset, field = 'text') => {
    if (!value) return;
    await api.post(`/doctor/${section}/${id}`, { [field]: value });
    reset('');
    const res = await api.get(`/doctor/${section}/${id}`);
    setter(res.data);
  };

  const vitalsChart = {
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
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

  const renderSection = () => {
    const sectionProps = {
      observations: {
        title: 'Observations', icon: <FaNotesMedical />, data: observations,
        text: note, setText: setNote, setter: setObservations, field: 'text', color: '#0d6efd'
      },
      treatments: {
        title: 'Treatments', icon: <FaCapsules />, data: treatments,
        text: medText, setText: setMedText, setter: setTreatments, field: 'medicationText', color: '#198754'
      },
      allergies: {
        title: 'Allergies', icon: <FiAlertTriangle />, data: allergies,
        text: allergyText, setText: setAllergyText, setter: setAllergies, color: '#ffc107'
      },
      conditions: {
        title: 'Conditions', icon: <FaProcedures />, data: conditions,
        text: conditionText, setText: setConditionText, setter: setConditions, color: '#0dcaf0'
      },
      immunizations: {
        title: 'Immunizations', icon: <GiSyringe />, data: immunizations,
        text: immunizationText, setText: setImmunizationText, setter: setImmunizations, color: '#343a40'
      }
    };

    if (selectedSection === 'profile') {
      return (
        <Card>
          <Card.Header style={{ backgroundColor: '#00b8a9', color: 'white' }}>
            <FiUser className="me-2" /> Patient Profile
          </Card.Header>
          <Card.Body>
            <p><strong>Name:</strong> {patient?.name?.map(n => `${n.given.join(' ')} ${n.family}`).join(', ')}</p>
            <p><strong>Birth Date:</strong> {formatDate(patient?.birthDate)}</p>
          </Card.Body>
        </Card>
      );
    }

    if (selectedSection === 'vitals') {
      return (
        <Card>
          <Card.Header style={{ backgroundColor: '#00b8a9', color: 'white' }}>
            <FaHeartbeat className="me-2" /> Vitals
          </Card.Header>
          <Card.Body>
            {vitals.length ? (
              <ReactECharts option={vitalsChart} style={{ height: '300px', width: '100%' }} />
            ) : <Alert variant="info">No vitals data.</Alert>}
          </Card.Body>
        </Card>
      );
    }

    const sec = sectionProps[selectedSection];
    if (!sec) return null;

    return (
      <Card>
        <Card.Header style={{ backgroundColor: sec.color, color: 'white' }}>
          {sec.icon} {sec.title}
        </Card.Header>
        <Card.Body>
          <Form className="d-flex mb-3">
            <Form.Control placeholder={`New ${sec.title.toLowerCase().slice(0, -1)}...`} value={sec.text} onChange={e => sec.setText(e.target.value)} />
            <Button className="ms-2" onClick={() => addItem(selectedSection, sec.text, sec.setter, sec.setText, sec.field)}>Add</Button>
          </Form>
          {sec.data.length ? (
            <Table size="sm" bordered>
              <thead><tr><th>Date</th><th>Description</th></tr></thead>
              <tbody>
                {sec.data.map(item => (
                  <tr key={item.id}>
<td>
  {
    formatDate(
      selectedSection === 'treatments'
        ? item.authoredOn || item.date
        : selectedSection === 'immunizations'
          ? item.occurrenceDateTime || item.date
          : selectedSection === 'conditions'
            ? item.recordedDate || item.onsetDateTime || item.date
            : item.date || item.recordedDate || item.authoredOn || item.effectiveDateTime
    )
  }
</td>

                    <td>
  {
    selectedSection === 'treatments'
      ? item.medicationText || item.medication || item.medicationCodeableConcept?.text || '(No medication)'
      : selectedSection === 'immunizations'
        ? item.text || item.vaccineCode?.text || '(No vaccine info)'
        : item[sec.field] || item.text || item.valueString || item.substance?.text || item.code?.text || '(No data)'
  }
</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : <Alert variant="info">No {sec.title.toLowerCase()} recorded.</Alert>}
        </Card.Body>
      </Card>
    );
  };

  if (loading) return <div className="text-center my-5"><Spinner animation="border" /></div>;

  return (
    <div style={{ background: '#f2f2f2', minHeight: '100vh', fontFamily: 'Segoe UI, sans-serif' }}>
      <Navbar bg="dark" variant="dark">
        <Container>
          <Button variant="outline-light" onClick={() => navigate('/dashboard/doctor')}>
            <FiArrowLeft className="me-2" /> Back
          </Button>
          <Nav className="ms-auto">
            <Button variant="info" className="me-2" onClick={handleDownloadReport}>
              <FiDownload className="me-2" /> Download Report
            </Button>
            <Button variant="danger" onClick={logout}>Logout</Button>
          </Nav>
        </Container>
      </Navbar>

      <Container fluid className="d-flex pt-4">
        {/* Sidebar */}
        <div style={{ minWidth: '220px', background: '#00b8a9', color: 'white', padding: '1rem', borderRadius: '0 1rem 1rem 0' }}>
          <h5 className="text-white fw-bold mb-3">Sections</h5>
          <ListGroup variant="flush">
            {[
              { id: 'profile', label: 'Profile', icon: <FiUser /> },
              { id: 'vitals', label: 'Vitals', icon: <FaHeartbeat /> },
              { id: 'observations', label: 'Observations', icon: <FaNotesMedical /> },
              { id: 'treatments', label: 'Treatments', icon: <FaCapsules /> },
              { id: 'allergies', label: 'Allergies', icon: <FiAlertTriangle /> },
              { id: 'conditions', label: 'Conditions', icon: <FaProcedures /> },
              { id: 'immunizations', label: 'Immunizations', icon: <GiSyringe /> }
            ].map(sec => (
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

        {/* Main content */}
        <div className="flex-grow-1 px-4">
          <h2 className="fw-bold mb-4">Patient Details</h2>
          {err && <Alert variant="danger">{err}</Alert>}
          {renderSection()}
        </div>
      </Container>
    </div>
  );
}
