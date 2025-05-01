// src/api.js
import axios from 'axios';

// patient‐side
export const getMyAllergies    = () => api.get("/patients/me/allergies");

// doctor‐side
export const getAllergies    = id => api.get(`/doctor/allergies/${id}`);
export const addAllergy     = (id, text) => api.post(`/doctor/allergies/${id}`, { text });

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
  // We’ll override Content-Type per-call when needed (e.g. login)
});

export default api;
