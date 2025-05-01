// src/pages/LoginPage.jsx

import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { FaUser, FaUserMd, FaCogs } from 'react-icons/fa';

const roles = [
  { icon: <FaUser size={40} />, label: 'Patient', link: '/login/patient' },
  { icon: <FaUserMd size={40} />, label: 'Doctor', link: '/login/doctor' },
  { icon: <FaCogs size={40} />, label: 'Admin', link: '/login/admin' }
];

export default function LoginPage() {
  const navigate = useNavigate();

  return (
    <div style={{ background: '#f2f2f2', minHeight: '100vh' }}>
      <div className="text-center py-5" style={{ backgroundColor: '#00b8a9', color: 'white' }}>
        <h1 className="fw-bold">Welcome to MedLedger</h1>
        <p className="lead mb-0">Please select your role to continue</p>
      </div>

      <Container className="py-5">
        <Row className="justify-content-center g-4">
          {roles.map((role, idx) => (
            <Col key={idx} xs={10} sm={6} md={4} lg={3}>
              <Card
                className="text-center shadow"
                onClick={() => navigate(role.link)}
                style={{
                  padding: '2rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  border: 'none',
                  borderRadius: '1rem'
                }}
                onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
              >
                <div style={{ color: '#00b8a9' }}>{role.icon}</div>
                <h5 className="mt-3 mb-0">{role.label}</h5>
              </Card>
            </Col>
          ))}
        </Row>
      </Container>
    </div>
  );
}
