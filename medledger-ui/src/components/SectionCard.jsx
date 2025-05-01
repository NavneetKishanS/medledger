// src/components/SectionCard.jsx

import React from 'react';
import PropTypes from 'prop-types';
import { Alert } from 'react-bootstrap';
import './SectionCard.css';

export default function SectionCard({ title, items }) {
  const pad2 = n => String(n).padStart(2, '0');
  const formatDate = iso => {
    const d = new Date(iso);
    return isNaN(d) ? 'Invalid date' : `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
  };

  const renderHeader = () => (
    <div className="section-card-header">
      {title}
    </div>
  );

  if (!items || items.length === 0) {
    return (
      <div className="section-card">
        {renderHeader()}
        <div className="section-card-body">
          <Alert variant="info" className="mb-0">
            No {title.toLowerCase()} to show.
          </Alert>
        </div>
      </div>
    );
  }

  const clean = items
    .filter(r => r && r.id && r.date && r.text)
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  if (clean.length === 0) {
    return (
      <div className="section-card">
        {renderHeader()}
        <div className="section-card-body">
          <Alert variant="info" className="mb-0">
            No valid {title.toLowerCase()} entries.
          </Alert>
        </div>
      </div>
    );
  }

  const latest = clean[0];
  const singular = title.endsWith('s') ? title.slice(0, -1) : title;

  return (
    <div className="section-card">
      {renderHeader()}
      <div className="section-card-body">
        <div className="latest-line">
          <strong>Latest {singular}</strong> — {formatDate(latest.date)}
        </div>
        <div className="latest-text">{latest.text}</div>
        <div className="separator" />
        <div className="history">
          {clean.map(item => (
            <div key={item.id}>
              <span className="item-date">{formatDate(item.date)}</span>: {item.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

SectionCard.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    date: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired,
  })).isRequired,
};
