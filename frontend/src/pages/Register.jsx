import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserPlus, AlertCircle, CheckCircle2 } from 'lucide-react';
import api from '../services/api';
import { validateName, validatePhone, validateEmail } from '../validation/rules';

export default function Register() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Instant validation on change
    if (name === 'name') setErrors((prev) => ({ ...prev, name: validateName(value) }));
    if (name === 'phone') setErrors((prev) => ({ ...prev, phone: validatePhone(value) }));
    if (name === 'email') setErrors((prev) => ({ ...prev, email: validateEmail(value) }));
    if (name === 'password') {
      const err = value.length < 8 ? 'Password must be at least 8 characters long.' : null;
      setErrors((prev) => ({ ...prev, password: err }));
    }
    if (name === 'confirmPassword') {
      const matchErr = value !== formData.password ? 'Passwords do not match.' : null;
      setErrors((prev) => ({ ...prev, confirmPassword: matchErr }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    setSuccessMsg('');

    const nameErr = validateName(formData.name);
    const phoneErr = validatePhone(formData.phone);
    const emailErr = validateEmail(formData.email);
    const pwdErr = formData.password.length < 8 ? 'Password must be at least 8 characters long.' : null;
    const matchErr = formData.password !== formData.confirmPassword ? 'Passwords do not match.' : null;

    if (nameErr || phoneErr || emailErr || pwdErr || matchErr) {
      setErrors({
        name: nameErr,
        phone: phoneErr,
        email: emailErr,
        password: pwdErr,
        confirmPassword: matchErr,
      });
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/register', {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        password: formData.password,
      });

      setSuccessMsg('Citizen registration successful! Redirecting to login...');
      setTimeout(() => {
        navigate('/login');
      }, 1500);
    } catch (err) {
      if (!err.response) {
        setServerError('Cannot connect to the backend server at http://localhost:8000. Please verify the backend service is running.');
      } else {
        const msg = err.response?.data?.error?.message || 'Registration failed. Please check your details.';
        setServerError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '580px', marginTop: '30px' }}>
      <div className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '12px',
              backgroundColor: '#ea580c',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
            }}
          >
            <UserPlus size={30} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.4rem', color: '#102a43', fontWeight: 700 }}>
            Citizen Portal Registration
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Register to book postal parcels and request doorstep collection.
          </p>
          <div style={{ fontSize: '0.78rem', color: '#92400e', background: '#fef3c7', padding: '6px', borderRadius: '4px', marginTop: '10px' }}>
            🔒 Public registration provisions <strong>CITIZEN</strong> accounts only.
          </div>
        </div>

        {serverError && (
          <div className="alert alert-error">
            <AlertCircle size={18} />
            <span>{serverError}</span>
          </div>
        )}

        {successMsg && (
          <div className="alert alert-success">
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label">
              Full Name (As per Govt. ID) <span className="required">*</span>
            </label>
            <input
              type="text"
              name="name"
              className="form-input"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Rahul Kumar or A. Kumar"
              required
            />
            {errors.name && <span className="form-error">{errors.name}</span>}
            <span className="form-hint">Alphabetic characters and optional initials only.</span>
          </div>

          <div className="form-grid" style={{ marginBottom: '16px' }}>
            <div className="form-group">
              <label className="form-label">
                Email Address <span className="required">*</span>
              </label>
              <input
                type="email"
                name="email"
                className="form-input"
                value={formData.email}
                onChange={handleChange}
                placeholder="user@example.com"
                required
              />
              {errors.email && <span className="form-error">{errors.email}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                Mobile Number (10 Digits) <span className="required">*</span>
              </label>
              <input
                type="tel"
                name="phone"
                className="form-input"
                value={formData.phone}
                onChange={handleChange}
                placeholder="9876543210"
                maxLength={10}
                required
              />
              {errors.phone && <span className="form-error">{errors.phone}</span>}
            </div>
          </div>

          <div className="form-grid" style={{ marginBottom: '24px' }}>
            <div className="form-group">
              <label className="form-label">
                Password (Min 8 chars) <span className="required">*</span>
              </label>
              <input
                type="password"
                name="password"
                className="form-input"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
              {errors.password && <span className="form-error">{errors.password}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">
                Confirm Password <span className="required">*</span>
              </label>
              <input
                type="password"
                name="confirmPassword"
                className="form-input"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
              {errors.confirmPassword && <span className="form-error">{errors.confirmPassword}</span>}
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '12px' }}
            disabled={loading}
          >
            <UserPlus size={18} /> {loading ? 'Registering Citizen...' : 'Complete Registration'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem' }}>
          Already registered?{' '}
          <Link to="/login" style={{ color: '#ea580c', fontWeight: 600 }}>
            Sign in here
          </Link>
        </div>
      </div>
    </div>
  );
}
