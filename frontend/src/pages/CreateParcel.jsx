import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Send,
  CheckCircle2,
  Copy,
  AlertCircle,
  Calendar,
  Receipt,
  Info,
  Sparkles,
  MapPin,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  Check
} from 'lucide-react';
import api from '../services/api';
import {
  validateName,
  validatePhone,
  validatePin,
  validateAddress,
  validateWeight,
  validateCity,
  validateState,
} from '../validation/rules';

const FALLBACK_INDIAN_STATES = [
  'Andaman and Nicobar Islands',
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chandigarh',
  'Chhattisgarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jammu and Kashmir',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Ladakh',
  'Lakshadweep',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Puducherry',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
];

export default function CreateParcel() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    receiver_name: '',
    receiver_phone: '',
    destination_address: '',
    destination_city: '',
    destination_state: '',
    destination_pin: '',
    weight: '1.0',
    parcel_type: 'DOCUMENT',
    priority: 'STANDARD',
  });

  const [quote, setQuote] = useState({
    total_price: 40.0,
    base_price: 25.0,
    weight_charge: 15.0,
    express_surcharge: 0.0,
    currency: 'INR',
  });

  const [statesList, setStatesList] = useState(FALLBACK_INDIAN_STATES);
  const [availableCities, setAvailableCities] = useState([]);
  const [availablePins, setAvailablePins] = useState([]);
  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingPinLookup, setLoadingPinLookup] = useState(false);
  const [locationVerification, setLocationVerification] = useState(null);
  const [mismatchError, setMismatchError] = useState(null);

  const [errors, setErrors] = useState({});
  const [validationSummary, setValidationSummary] = useState([]);
  const [serverError, setServerError] = useState('');
  const [createdParcel, setCreatedParcel] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load official states from backend dataset on mount
  useEffect(() => {
    const fetchStates = async () => {
      try {
        const res = await api.get('/postal/states');
        if (res.data?.data && Array.isArray(res.data.data) && res.data.data.length > 0) {
          setStatesList(res.data.data);
        }
      } catch (err) {
        console.warn('Using fallback state directory:', err);
      }
    };
    fetchStates();
  }, []);

  // Live price quote calculation
  useEffect(() => {
    const fetchQuote = async () => {
      const weightNum = parseFloat(formData.weight);
      if (isNaN(weightNum) || weightNum <= 0) return;

      try {
        const res = await api.post('/parcels/quote', {
          weight: weightNum,
          parcel_type: formData.parcel_type,
          priority: formData.priority,
        });
        if (res.data?.data) {
          setQuote(res.data.data);
        }
      } catch {
        const base =
          formData.parcel_type === 'DOCUMENT'
            ? 25
            : formData.parcel_type === 'SMALL_PARCEL'
            ? 45
            : formData.parcel_type === 'MEDIUM_PARCEL'
            ? 90
            : 180;
        const perKg =
          formData.parcel_type === 'DOCUMENT'
            ? 15
            : formData.parcel_type === 'SMALL_PARCEL'
            ? 25
            : formData.parcel_type === 'MEDIUM_PARCEL'
            ? 35
            : 45;
        const wtCharge = weightNum * perKg;
        const sub = base + wtCharge;
        const express = formData.priority === 'EXPRESS' ? sub * 0.5 : 0;
        setQuote({
          total_price: sub + express,
          base_price: base,
          weight_charge: wtCharge,
          express_surcharge: express,
          currency: 'INR',
        });
      }
    };

    fetchQuote();
  }, [formData.weight, formData.parcel_type, formData.priority]);

  // Handler: When user selects State -> Auto-fill City & PIN from Dataset
  const handleStateChange = async (selectedState) => {
    setMismatchError(null);
    setErrors((prev) => ({ ...prev, destination_state: null, destination_pin: null, destination_city: null }));

    if (!selectedState) {
      setFormData((prev) => ({
        ...prev,
        destination_state: '',
        destination_city: '',
        destination_pin: '',
      }));
      setAvailableCities([]);
      setAvailablePins([]);
      setLocationVerification(null);
      return;
    }

    setLoadingCities(true);
    try {
      const res = await api.get('/postal/cities', { params: { state: selectedState } });
      const { cities = [], default_pin = '' } = res.data?.data || {};

      setAvailableCities(cities);

      // Choose representative city (first district in dataset)
      const primaryCity = cities.length > 0 ? cities[0] : '';
      const chosenPin = default_pin || '';

      setFormData((prev) => ({
        ...prev,
        destination_state: selectedState,
        destination_city: primaryCity,
        destination_pin: chosenPin,
      }));

      setLocationVerification({
        verified: true,
        message: `Dataset Linked: Auto-filled ${primaryCity}, ${selectedState} (PIN: ${chosenPin}) from official postal database.`,
        source: 'STATE_AUTOFILL',
      });

      // Load matching PINs for this state & district
      if (primaryCity) {
        loadPinsForLocation(selectedState, primaryCity);
      }
    } catch (err) {
      console.error('Failed to load cities for state:', err);
      setFormData((prev) => ({ ...prev, destination_state: selectedState }));
    } finally {
      setLoadingCities(false);
    }
  };

  // Handler: When user selects City / District -> Auto-fill representative PIN
  const handleCityChange = async (selectedCity) => {
    setMismatchError(null);
    setErrors((prev) => ({ ...prev, destination_city: null, destination_pin: null }));

    setFormData((prev) => ({ ...prev, destination_city: selectedCity }));

    if (selectedCity && formData.destination_state) {
      loadPinsForLocation(formData.destination_state, selectedCity);
    }
  };

  // Helper: Fetch valid PINs for state and city
  const loadPinsForLocation = async (state, city) => {
    try {
      const res = await api.get('/postal/pincodes', {
        params: { state, city, limit: 40 },
      });
      const pins = res.data?.data || [];
      setAvailablePins(pins);
      if (pins.length > 0) {
        // Pre-fill primary PIN for the chosen city
        setFormData((prev) => ({ ...prev, destination_pin: pins[0] }));
        setLocationVerification({
          verified: true,
          message: `Official PIN ${pins[0]} matched for ${city}, ${state}.`,
          source: 'CITY_SELECT',
        });
      }
    } catch (err) {
      console.warn('Could not fetch PINs for city:', err);
    }
  };

  // Handler: When user manually types or pastes PIN code (6 Digits)
  const handlePinInput = async (pinValue) => {
    const cleaned = pinValue.replace(/\D/g, '').slice(0, 6);

    setFormData((prev) => ({ ...prev, destination_pin: cleaned }));
    setErrors((prev) => ({ ...prev, destination_pin: validatePin(cleaned) }));

    if (cleaned.length !== 6) {
      setLocationVerification(null);
      setMismatchError(null);
      return;
    }

    setLoadingPinLookup(true);
    try {
      const res = await api.get(`/postal/pincode/${cleaned}`);
      const loc = res.data?.data;

      if (!loc) {
        setLocationVerification(null);
        return;
      }

      const pinState = loc.state;
      const pinCity = loc.district || loc.city;

      // Check for Mismatch with currently selected State
      if (
        formData.destination_state &&
        formData.destination_state.toLowerCase().trim() !== pinState.toLowerCase().trim()
      ) {
        setMismatchError({
          isMismatch: true,
          message: `Mismatch Detected: PIN ${cleaned} belongs to ${pinState} (${pinCity}), but '${formData.destination_state}' is currently selected.`,
          expectedState: pinState,
          expectedCity: pinCity,
          officename: loc.officename,
        });
        setLocationVerification(null);
        setErrors((prev) => ({
          ...prev,
          destination_pin: `PIN belongs to ${pinState}, not ${formData.destination_state}.`,
        }));
      } else {
        // Match or state was unselected: auto-fill State and City from Dataset
        setMismatchError(null);
        setFormData((prev) => ({
          ...prev,
          destination_state: pinState,
          destination_city: pinCity,
          destination_pin: cleaned,
        }));

        setLocationVerification({
          verified: true,
          message: `Verified: ${pinCity}, ${pinState} (${loc.officename || 'Postal Hub'})`,
          source: 'PIN_LOOKUP',
        });

        // Ensure available cities list has the state's cities
        if (pinState !== formData.destination_state) {
          api.get('/postal/cities', { params: { state: pinState } }).then((r) => {
            if (r.data?.data?.cities) setAvailableCities(r.data.data.cities);
          });
        }
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setLocationVerification({
          verified: false,
          message: `PIN ${cleaned} not found in offline dataset directory.`,
          source: 'NOT_FOUND',
        });
      }
    } finally {
      setLoadingPinLookup(false);
    }
  };

  // 1-Click Auto-Fix Mismatch Action
  const handleAutoFixMismatch = () => {
    if (!mismatchError) return;
    const { expectedState, expectedCity } = mismatchError;

    setFormData((prev) => ({
      ...prev,
      destination_state: expectedState,
      destination_city: expectedCity,
    }));

    setMismatchError(null);
    setErrors((prev) => ({
      ...prev,
      destination_state: null,
      destination_city: null,
      destination_pin: null,
    }));

    setLocationVerification({
      verified: true,
      message: `Mismatch resolved: Successfully aligned state to ${expectedState} and city to ${expectedCity}.`,
      source: 'AUTO_FIX',
    });

    // Refresh cities for the new state
    api.get('/postal/cities', { params: { state: expectedState } }).then((r) => {
      if (r.data?.data?.cities) setAvailableCities(r.data.data.cities);
    });
  };

  // General Input Change Handler
  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === 'destination_state') {
      handleStateChange(value);
      return;
    }
    if (name === 'destination_city') {
      handleCityChange(value);
      return;
    }
    if (name === 'destination_pin') {
      handlePinInput(value);
      return;
    }

    setFormData((prev) => ({ ...prev, [name]: value }));

    if (validationSummary.length > 0) {
      setValidationSummary([]);
    }

    // Instant validation
    if (name === 'receiver_name') setErrors((prev) => ({ ...prev, receiver_name: validateName(value) }));
    if (name === 'receiver_phone') setErrors((prev) => ({ ...prev, receiver_phone: validatePhone(value) }));
    if (name === 'destination_address') setErrors((prev) => ({ ...prev, destination_address: validateAddress(value) }));
    if (name === 'weight') setErrors((prev) => ({ ...prev, weight: validateWeight(value) }));
  };

  const handleCopy = () => {
    if (createdParcel?.tracking_id) {
      navigator.clipboard.writeText(createdParcel.tracking_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    setValidationSummary([]);

    if (mismatchError) {
      setServerError('Please resolve the Address-PIN mismatch before submitting your booking.');
      return;
    }

    const rNameErr = validateName(formData.receiver_name);
    const rPhoneErr = validatePhone(formData.receiver_phone);
    const addrErr = validateAddress(formData.destination_address);
    const cityErr = validateCity(formData.destination_city);
    const stateErr = validateState(formData.destination_state);
    const pinErr = validatePin(formData.destination_pin);
    const weightErr = validateWeight(formData.weight);

    const newErrors = {
      receiver_name: rNameErr,
      receiver_phone: rPhoneErr,
      destination_address: addrErr,
      destination_city: cityErr,
      destination_state: stateErr,
      destination_pin: pinErr,
      weight: weightErr,
    };

    const errorList = Object.values(newErrors).filter(Boolean);

    if (errorList.length > 0) {
      setErrors(newErrors);
      setValidationSummary(errorList);

      const firstErrorKey = Object.keys(newErrors).find((k) => newErrors[k]);
      if (firstErrorKey) {
        setTimeout(() => {
          const el = document.querySelector(`[name="${firstErrorKey}"]`);
          if (el) {
            el.focus();
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 50);
      }
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/parcels', {
        receiver_name: formData.receiver_name.trim(),
        receiver_phone: formData.receiver_phone.trim(),
        destination_address: formData.destination_address.trim(),
        destination_city: formData.destination_city.trim(),
        destination_state: formData.destination_state.trim(),
        destination_pin: formData.destination_pin.trim(),
        weight: parseFloat(formData.weight),
        parcel_type: formData.parcel_type,
        priority: formData.priority,
      });
      setCreatedParcel(response.data.data);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to book parcel. Please review your details.';
      setServerError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '840px' }}>
      <div className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <h1 className="page-title">Book New Consignment</h1>
          <p className="page-subtitle">
            Register your parcel with verified delivery parameters and automated tariff computation.
          </p>
        </div>
      </div>

      {createdParcel ? (

        <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div
            style={{
              display: 'inline-flex',
              padding: '16px',
              background: '#e6f4ea',
              borderRadius: '50%',
              color: '#137333',
              marginBottom: '16px',
            }}
          >
            <CheckCircle2 size={48} />
          </div>
          <h2 style={{ fontSize: '22px', fontWeight: '700', marginBottom: '8px' }}>
            Consignment Booked Successfully!
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Your parcel has been entered into the national transit network with official tariff ₹
            {Number(createdParcel.price).toFixed(2)}.
          </p>

          <div
            style={{
              background: '#f8f9fa',
              border: '1px dashed var(--border-color)',
              borderRadius: '8px',
              padding: '20px',
              maxWidth: '440px',
              margin: '0 auto 28px auto',
            }}
          >
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Server-Generated Tracking ID
            </span>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
              <span
                style={{
                  fontSize: '24px',
                  fontWeight: '800',
                  fontFamily: 'monospace',
                  letterSpacing: '1px',
                  color: 'var(--primary-color)',
                }}
              >
                {createdParcel.tracking_id}
              </span>
              <button
                type="button"
                onClick={handleCopy}
                className="btn btn-outline"
                style={{ padding: '6px 12px', fontSize: '12px' }}
              >
                {copied ? <CheckCircle2 size={14} color="#137333" /> : <Copy size={14} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', margin: '8px 0 0 0' }}>
              Destination: {createdParcel.destination_city}, {createdParcel.destination_state} - {createdParcel.destination_pin}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <Link to={`/parcels/${createdParcel.tracking_id}/qr`} className="btn btn-primary">
              View Tracking QR Code
            </Link>
            <Link to={`/track/${createdParcel.tracking_id}`} className="btn btn-outline">
              Track Consignment
            </Link>
            <button
              type="button"
              onClick={() => {
                setCreatedParcel(null);
                setFormData({
                  receiver_name: '',
                  receiver_phone: '',
                  destination_address: '',
                  destination_city: '',
                  destination_state: '',
                  destination_pin: '',
                  weight: '1.0',
                  parcel_type: 'DOCUMENT',
                  priority: 'STANDARD',
                });
                setLocationVerification(null);
                setMismatchError(null);
              }}
              className="btn btn-outline"
            >
              Book Another Parcel
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          {serverError && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              <AlertCircle size={18} />
              <span>{serverError}</span>
            </div>
          )}

          {validationSummary.length > 0 && (
            <div
              className="alert alert-error"
              style={{
                marginBottom: '20px',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
                <AlertCircle size={18} />
                <span>Please correct the following errors before submitting:</span>
              </div>
              <ul style={{ margin: '0 0 0 24px', padding: 0, fontSize: '0.85rem' }}>
                {validationSummary.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <h3 className="card-title">1. Receiver Information</h3>
            <div className="form-grid" style={{ marginBottom: '20px' }}>
              <div className="form-group">
                <label className="form-label">
                  Receiver Full Name <span className="required">*</span>
                </label>
                <input
                  type="text"
                  name="receiver_name"
                  className={`form-input ${errors.receiver_name ? 'is-invalid' : ''}`}
                  value={formData.receiver_name}
                  onChange={handleChange}
                  placeholder="e.g. Priya Sharma"
                  required
                />
                {errors.receiver_name && <span className="form-error">{errors.receiver_name}</span>}
                <span className="form-hint">Alphabetic characters and initials only.</span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Receiver Mobile Number <span className="required">*</span>
                </label>
                <input
                  type="tel"
                  name="receiver_phone"
                  className={`form-input ${errors.receiver_phone ? 'is-invalid' : ''}`}
                  value={formData.receiver_phone}
                  onChange={handleChange}
                  placeholder="10-digit mobile number"
                  maxLength={13}
                  required
                />
                {errors.receiver_phone && <span className="form-error">{errors.receiver_phone}</span>}
                <span className="form-hint">Format: 10 digits starting with 6, 7, 8, or 9.</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <h3 className="card-title" style={{ margin: 0 }}>2. Destination Address (Dataset-Linked)</h3>
              <span style={{ fontSize: '0.78rem', color: '#059669', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
                <Sparkles size={14} /> Zero-Mismatch Smart Auto-fill
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label className="form-label" style={{ margin: 0 }}>
                  Street Address / Premises <span className="required">*</span>
                </label>
                <span
                  style={{
                    fontSize: '0.78rem',
                    color: formData.destination_address.trim().length >= 10 ? '#10b981' : '#64748b',
                    fontWeight: 500,
                  }}
                >
                  {formData.destination_address.trim().length} / 10 characters minimum
                </span>
              </div>
              <textarea
                name="destination_address"
                className={`form-textarea ${errors.destination_address ? 'is-invalid' : ''}`}
                rows={2}
                value={formData.destination_address}
                onChange={handleChange}
                placeholder="e.g. 12/4 Gandhi Street, Near Bus Stand, Flat 2B"
                required
              />
              {errors.destination_address && <span className="form-error">{errors.destination_address}</span>}
              <span className="form-hint">Must include specific premises, street name, or area details (min. 10 chars).</span>
            </div>

            {/* Smart Address Grid: State -> City -> PIN */}
            <div className="form-grid" style={{ marginBottom: '16px' }}>
              {/* 1. State / UT Selection */}
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600 }}>
                  State / UT <span className="required">*</span>
                </label>
                <select
                  name="destination_state"
                  className={`form-select ${errors.destination_state ? 'is-invalid' : ''}`}
                  value={formData.destination_state}
                  onChange={handleChange}
                  required
                  style={{ borderColor: formData.destination_state ? '#10b981' : undefined }}
                >
                  <option value="">-- 1. Select State / UT --</option>
                  {statesList.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
                {errors.destination_state && <span className="form-error">{errors.destination_state}</span>}
                <span className="form-hint">Selecting state auto-fills verified PIN and City list.</span>
              </div>

              {/* 2. City / District Selection (Auto-populated from dataset) */}
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600 }}>
                  City / District <span className="required">*</span>
                  {loadingCities && <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '6px' }}>(Loading...)</span>}
                </label>
                {availableCities.length > 0 ? (
                  <select
                    name="destination_city"
                    className={`form-select ${errors.destination_city ? 'is-invalid' : ''}`}
                    value={formData.destination_city}
                    onChange={handleChange}
                    required
                  >
                    <option value="">-- 2. Select City / District --</option>
                    {availableCities.map((city) => (
                      <option key={city} value={city}>
                        {city}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    name="destination_city"
                    className={`form-input ${errors.destination_city ? 'is-invalid' : ''}`}
                    value={formData.destination_city}
                    onChange={handleChange}
                    placeholder="Select State first or type City"
                    required
                  />
                )}
                {errors.destination_city && <span className="form-error">{errors.destination_city}</span>}
                <span className="form-hint">Official postal districts for {formData.destination_state || 'selected state'}.</span>
              </div>

              {/* 3. PIN Code (6 Digits) - Auto-filled from dataset */}
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600 }}>
                  PIN Code (6 Digits) <span className="required">*</span>
                  {loadingPinLookup && <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '6px' }}>(Verifying...)</span>}
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    name="destination_pin"
                    list="available-pins-list"
                    className={`form-input ${errors.destination_pin || mismatchError ? 'is-invalid' : ''}`}
                    value={formData.destination_pin}
                    onChange={handleChange}
                    placeholder="e.g. 600001"
                    maxLength={6}
                    required
                    style={{
                      fontFamily: 'monospace',
                      letterSpacing: '1px',
                      fontWeight: '600',
                    }}
                  />
                  {availablePins.length > 0 && (
                    <datalist id="available-pins-list">
                      {availablePins.map((pin) => (
                        <option key={pin} value={pin} />
                      ))}
                    </datalist>
                  )}
                </div>
                {errors.destination_pin && <span className="form-error">{errors.destination_pin}</span>}
                <span className="form-hint">Auto-filled from dataset; supports quick manual entry.</span>
              </div>
            </div>

            {/* Live Location Verification Badge */}
            {locationVerification && !mismatchError && (
              <div
                style={{
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  borderRadius: '6px',
                  padding: '10px 14px',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '0.86rem',
                  color: '#15803d',
                }}
              >
                <CheckCircle2 size={16} />
                <span>{locationVerification.message}</span>
              </div>
            )}

            {/* Mismatch Prevention Alert Banner */}
            {mismatchError && (
              <div
                style={{
                  background: '#fff1f2',
                  border: '1px solid #fecdd3',
                  borderRadius: '8px',
                  padding: '14px 16px',
                  marginBottom: '20px',
                  color: '#be123c',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '4px' }}>
                      Geographic Mismatch Prevented!
                    </div>
                    <div style={{ fontSize: '0.85rem', marginBottom: '10px', color: '#9f1239' }}>
                      {mismatchError.message}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={handleAutoFixMismatch}
                        className="btn btn-sm btn-primary"
                        style={{ fontSize: '0.8rem', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      >
                        <RefreshCw size={13} />
                        Auto-Fix: Switch State to {mismatchError.expectedState}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          // Reset PIN to valid default for the currently selected state
                          handleStateChange(formData.destination_state);
                        }}
                        className="btn btn-sm btn-outline"
                        style={{ fontSize: '0.8rem', padding: '5px 10px', background: '#ffffff' }}
                      >
                        Reset PIN for {formData.destination_state}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <h3 className="card-title">3. Consignment Specifications</h3>
            <div className="form-grid" style={{ marginBottom: '24px' }}>
              <div className="form-group">
                <label className="form-label">
                  Weight (in Kilograms) <span className="required">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="50.0"
                  name="weight"
                  className={`form-input ${errors.weight ? 'is-invalid' : ''}`}
                  value={formData.weight}
                  onChange={handleChange}
                  required
                />
                {errors.weight && <span className="form-error">{errors.weight}</span>}
                <span className="form-hint">Max weight: 50.00 kg</span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Parcel Type <span className="required">*</span>
                </label>
                <select
                  name="parcel_type"
                  className="form-select"
                  value={formData.parcel_type}
                  onChange={handleChange}
                >
                  <option value="DOCUMENT">Document / Letter</option>
                  <option value="SMALL_PARCEL">Small Parcel (&lt; 2 kg)</option>
                  <option value="MEDIUM_PARCEL">Medium Parcel (2 - 10 kg)</option>
                  <option value="LARGE_PARCEL">Large Parcel (&gt; 10 kg)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Delivery Priority <span className="required">*</span>
                </label>
                <select
                  name="priority"
                  className="form-select"
                  value={formData.priority}
                  onChange={handleChange}
                >
                  <option value="STANDARD">Standard Post</option>
                  <option value="EXPRESS">Express Consignment (1.5x Multiplier)</option>
                </select>
              </div>
            </div>

            {/* Authoritative Live Tariff Quotation */}
            <div
              style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '16px 20px',
                marginBottom: '24px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Receipt size={18} color="var(--primary-navy)" />
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Authoritative Tariff Quotation</span>
                </div>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Statutory India Post Pricing Schedule
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '12px', fontSize: '0.85rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block' }}>Base Service Fee</span>
                  <strong>₹{quote.base_price.toFixed(2)}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block' }}>Weight Fee</span>
                  <strong>₹{quote.weight_charge.toFixed(2)}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block' }}>Priority Surcharge</span>
                  <strong>₹{quote.express_surcharge.toFixed(2)}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block' }}>Final Amount Payable</span>
                  <strong style={{ fontSize: '1.15rem', color: 'var(--accent-saffron)' }}>
                    ₹{quote.total_price.toFixed(2)}
                  </strong>
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || Boolean(mismatchError)}
              style={{
                padding: '12px 24px',
                fontSize: '1rem',
                opacity: mismatchError ? 0.6 : 1,
                cursor: mismatchError ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? (
                'Processing Official Booking...'
              ) : mismatchError ? (
                'Resolve Address Mismatch to Proceed'
              ) : (
                <>
                  <Send size={18} /> Confirm &amp; Register Consignment (₹{quote.total_price.toFixed(2)})
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
