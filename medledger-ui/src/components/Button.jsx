// src/components/Button.jsx
import React from 'react';
import { Button as BootstrapButton } from 'react-bootstrap';

function Button({ onClick, children, variant = 'primary', ...props }) {
  return (
    <BootstrapButton onClick={onClick} variant={variant} {...props}>
      {children}
    </BootstrapButton>
  );
}

export default Button;
