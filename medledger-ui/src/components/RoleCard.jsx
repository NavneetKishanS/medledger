// src/components/RoleCard.jsx
import React from 'react';
import { Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import Button from './Button';

function RoleCard({ role, description, dashboardLink }) {
  const navigate = useNavigate();

  return (
    <Card className="role-card shadow-sm">
      <Card.Body className="text-center">
        <Card.Title className="text-capitalize">{role}</Card.Title>
        <Card.Text>{description}</Card.Text>
        <Button variant="info" onClick={() => navigate(dashboardLink)}>
          Select
        </Button>
      </Card.Body>
    </Card>
  );
}

export default RoleCard;
