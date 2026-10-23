import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Calendar, Truck, AlertCircle, CheckCircle2, UserCheck, Clock, MapPin, Sparkles } from 'lucide-react';
import api, { generateUUID } from '../services/api';
import {
  validateAddress,
  validateName,
  validatePin,
  validatePickupDate,
} from '../validation/rules';

const INDIAN_STATES_AND_UTS = [
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

const DEFAULT_PICKUP_HUBS = [
  { pin: '600001', city: 'Chennai', state: 'Tamil Nadu', has_active_agent: true, officename: 'Chennai GPO' },
  { pin: '110001', city: 'New Delhi', state: 'Delhi', has_active_agent: true, officename: 'New Delhi GPO' },
  { pin: '400001', city: 'Mumbai', state: 'Maharashtra', has_active_agent: true, officename: 'Mumbai GPO' },
  { pin: '560001', city: 'Bengaluru', state: 'Karnataka', has_active_agent: false, officename: 'Bengaluru GPO' },
  { pin: '700001', city: 'Kolkata', state: 'West Bengal', has_active_agent: false, officename: 'Kolkata GPO' },
  { pin: '500001', city: 'Hyderabad', state: 'Telangana', has_active_agent: false, officename: 'Hyderabad GPO' },
  { pin: '380001', city: 'Ahmedabad', state: 'Gujarat', has_active_agent: false, officename: 'Ahmedabad GPO' },
  { pin: '302001', city: 'Jaipur', state: 'Rajasthan', has_active_agent: false, officename: 'Jaipur GPO' },
  { pin: '226001', city: 'Lucknow', state: 'Uttar Pradesh', has_active_agent: false, officename: 'Lucknow GPO' },
  { pin: '682001', city: 'Kochi', state: 'Kerala', has_active_agent: false, officename: 'Kochi Head Post Office' },
  { pin: '160017', city: 'Chandigarh', state: 'Chandigarh', has_active_agent: false, officename: 'Sector 17 Head Post Office' },
  { pin: '800001', city: 'Patna', state: 'Bihar', has_active_agent: false, officename: 'Patna GPO' },
  { pin: '751001', city: 'Bhubaneswar', state: 'Odisha', has_active_agent: false, officename: 'Bhubaneswar GPO' },
  { pin: '462001', city: 'Bhopal', state: 'Madhya Pradesh', has_active_agent: false, officename: 'Bhopal GPO' },
  { pin: '403001', city: 'Panaji', state: 'Goa', has_active_agent: false, officename: 'Panaji Head Post Office' },
];

function getStateFromPinPrefix(pin) {
  if (!pin || pin.length < 2) return null;
  const prefix = parseInt(pin.substring(0, 2), 10);
  if (prefix === 11) return 'Delhi';
  if (prefix >= 12 && prefix <= 13) return 'Haryana';
  if (prefix >= 14 && prefix <= 15) return 'Punjab';
  if (prefix === 16) return 'Chandigarh';
  if (prefix === 17) return 'Himachal Pradesh';
  if (prefix >= 18 && prefix <= 19) return 'Jammu and Kashmir';
  if (prefix >= 20 && prefix <= 28) return 'Uttar Pradesh';
  if (prefix >= 30 && prefix <= 34) return 'Rajasthan';
  if (prefix >= 36 && prefix <= 39) return 'Gujarat';
  if (prefix >= 40 && prefix <= 44) return 'Maharashtra';
  if (prefix >= 45 && prefix <= 48) return 'Madhya Pradesh';
  if (prefix === 49) return 'Chhattisgarh';
  if (prefix >= 50 && prefix <= 53) return 'Andhra Pradesh';
  if (prefix >= 56 && prefix <= 59) return 'Karnataka';
  if (prefix >= 60 && prefix <= 64) return 'Tamil Nadu';
  if (prefix >= 67 && prefix <= 69) return 'Kerala';
  if (prefix >= 70 && prefix <= 74) return 'West Bengal';
  if (prefix >= 75 && prefix <= 77) return 'Odisha';
  if (prefix === 78) return 'Assam';
  if (prefix >= 80 && prefix <= 85) return 'Bihar';
  return null;
}

export default function CreatePickup() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedParcelId = searchParams.get('parcel_id');

  const [parcels, setParcels] = useState([]);
  const [loadingParcels, setLoadingParcels] = useState(true);
  const [hubs, setHubs] = useState(DEFAULT_PICKUP_HUBS);
  const [selectedHub, setSelectedHub] = useState('');
  const [isCustomPin, setIsCustomPin] = useState(false);
  const [autoDetected, setAutoDetected] = useState(false);

  const [formData, setFormData] = useState({
    parcel_id: preselectedParcelId ? parseInt(preselectedParcelId, 10) : '',
    pickup_address: '',
    pickup_city: '',
    pickup_state: '',
    pickup_pin: '',
    requested_date: new Date().toISOString().split('T')[0],
  });

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [createdPickup, setCreatedPickup] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function loadInitialData() {
      try {
        const res = await api.get('/parcels/my');
        const list = res.data.data || [];
        setParcels(list);
        if (!formData.parcel_id && list.length > 0) {
          setFormData((prev) => ({ ...prev, parcel_id: list[0].id }));
        }
      } catch (err) {
        console.error('Failed to load parcels for selection', err);
      } finally {
        setLoadingParcels(false);
      }

      // Fetch dynamic active pickup hubs from backend
      try {
        const hubsRes = await api.get('/postal/available-pickup-hubs');
        if (hubsRes.data?.data && hubsRes.data.data.length > 0) {
          setHubs(hubsRes.data.data);
        }
      } catch (e) {
        // Fallback to DEFAULT_PICKUP_HUBS
      }
    }
    loadInitialData();
  }, []);

  // Handle Hub Selection from the Dropdown
  const handleHubSelect = (e) => {
    const val = e.target.value;
    setSelectedHub(val);

    if (val === 'custom') {
      setIsCustomPin(true);
      return;
    }

    if (!val) {
      setIsCustomPin(false);
      setAutoDetected(false);
      return;
    }

    setIsCustomPin(false);
    const matched = hubs.find((h) => h.pin === val);
    if (matched) {
      setFormData((prev) => ({
        ...prev,
        pickup_pin: matched.pin,
        pickup_city: matched.city,
        pickup_state: matched.state,
      }));
      setAutoDetected(true);
      setErrors((prev) => ({
        ...prev,
        pickup_pin: null,
        pickup_city: null,
        pickup_state: null,
      }));
    }
  };

  // Lookup custom PIN code details dynamically
  const lookupCustomPin = async (pin) => {
    if (pin.length !== 6 || !/^\d{6}$/.test(pin) || pin.startsWith('0')) return;

    try {
      const res = await api.get(`/postal/pincode/${pin}`);
      if (res.data?.data) {
        const d = res.data.data;
        setFormData((prev) => ({
          ...prev,
          pickup_city: d.city || prev.pickup_city,
          pickup_state: d.state || prev.pickup_state,
        }));
        setAutoDetected(true);
        setErrors((prev) => ({ ...prev, pickup_city: null, pickup_state: null, pickup_pin: null }));
        return;
      }
    } catch (e) {
      // Local fallback by prefix
      const fallbackState = getStateFromPinPrefix(pin);
      if (fallbackState) {
        setFormData((prev) => ({
          ...prev,
          pickup_state: fallbackState,
        }));
        setAutoDetected(true);
        setErrors((prev) => ({ ...prev, pickup_state: null }));
      }
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'parcel_id' ? parseInt(value, 10) : value,
    }));

    if (name === 'pickup_state') {
      setErrors((prev) => ({ ...prev, pickup_state: validateName(value) }));
      if (value) {
        api.get('/postal/cities', { params: { state: value } }).then((res) => {
          const { cities = [], default_pin = '' } = res.data?.data || {};
          if (cities.length > 0 || default_pin) {
            setFormData((prev) => ({
              ...prev,
              pickup_city: cities[0] || prev.pickup_city,
              pickup_pin: default_pin || prev.pickup_pin,
            }));
            setAutoDetected(true);
            setErrors((errs) => ({ ...errs, pickup_city: null, pickup_pin: null }));
          }
        }).catch(() => {});
      }
    }
    if (name === 'pickup_pin') {
      if (value.length === 6) {
        lookupCustomPin(value);
      }
      setErrors((prev) => ({ ...prev, pickup_pin: validatePin(value) }));
    }
    if (name === 'pickup_address') setErrors((prev) => ({ ...prev, pickup_address: validateAddress(value) }));
    if (name === 'pickup_city') setErrors((prev) => ({ ...prev, pickup_city: validateName(value) }));
    if (name === 'requested_date') setErrors((prev) => ({ ...prev, requested_date: validatePickupDate(value) }));
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!formData.parcel_id) {
      setErrors((prev) => ({ ...prev, parcel_id: 'Please select a parcel for pickup.' }));
      return;
    }

    const addrErr = validateAddress(formData.pickup_address);
    const cityErr = validateName(formData.pickup_city);
    const stateErr = validateName(formData.pickup_state);
    const pinErr = validatePin(formData.pickup_pin);
    const dateErr = validatePickupDate(formData.requested_date);

    if (addrErr || cityErr || stateErr || pinErr || dateErr) {
      setErrors({
        pickup_address: addrErr,
        pickup_city: cityErr,
        pickup_state: stateErr,
        pickup_pin: pinErr,
        requested_date: dateErr,
      });
      return;
    }

    setSubmitting(true);
    const idempotencyKey = generateUUID();

    try {
      const response = await api.post('/pickups', formData, {
        headers: {
          'Idempotency-Key': idempotencyKey,
        },
      });
      setCreatedPickup(response.data.data);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to create pickup request.';
      setServerError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const activeHubInfo = hubs.find((h) => h.pin === formData.pickup_pin);

  return (
    <div className="container" style={{ maxWidth: '780px' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Schedule Doorstep Pickup</h2>
          <p className="page-subtitle">A postal delivery agent will visit your address to collect your consignment.</p>
        </div>
      </div>

      {createdPickup ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: createdPickup.status === 'ASSIGNED' ? '#dbeafe' : '#fef3c7',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            {createdPickup.status === 'ASSIGNED' ? (
              <UserCheck size={36} color="#1e40af" />
            ) : (
              <Clock size={36} color="#b45309" />
            )}
          </div>

          <h3 style={{ fontSize: '1.4rem', color: '#102a43', fontWeight: 700, marginBottom: '8px' }}>
            Pickup Request #{createdPickup.id} Registered!
          </h3>

          <div style={{ maxWidth: '500px', margin: '0 auto 24px auto' }}>
            {createdPickup.status === 'ASSIGNED' ? (
              <div className="alert alert-success">
                <CheckCircle2 size={20} />
                <div style={{ textAlign: 'left' }}>
                  <strong>Agent Assigned:</strong> Delivery Agent #{createdPickup.assigned_agent_id} has been assigned for PIN {createdPickup.pickup_pin}.
                </div>
              </div>
            ) : (
              <div className="alert alert-info">
                <Clock size={20} />
                <div style={{ textAlign: 'left' }}>
                  <strong>Status: Pending Assignment:</strong> No available delivery agent is currently serving PIN {createdPickup.pickup_pin}. Your request is registered and queued.
                </div>
              </div>
            )}
          </div>

          <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', maxWidth: '460px', margin: '0 auto 28px auto', textAlign: 'left', fontSize: '0.9rem' }}>
            <div><strong>Consignment:</strong> {createdPickup.parcel?.tracking_id}</div>
            <div><strong>Pickup Date:</strong> {createdPickup.requested_date}</div>
            <div><strong>Pickup Address:</strong> {createdPickup.pickup_address}, {createdPickup.pickup_city}, {createdPickup.pickup_state} - {createdPickup.pickup_pin}</div>
            <div><strong>Idempotency Token:</strong> <code style={{ fontSize: '0.75rem' }}>{createdPickup.idempotency_key}</code></div>
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <Link to={`/pickups/${createdPickup.id}`} className="btn btn-primary">
              View Pickup Details & History
            </Link>
            <Link to="/pickups/my" className="btn btn-outline">
              Back to My Pickups
            </Link>
          </div>
        </div>
      ) : (
        <div className="card">
          {serverError && (
            <div className="alert alert-error">
              <AlertCircle size={18} />
              <span>{serverError}</span>
            </div>
          )}

          {loadingParcels ? (
            <p style={{ color: '#64748b' }}>Loading your parcels...</p>
          ) : parcels.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 0', color: '#64748b' }}>
              <Truck size={40} style={{ opacity: 0.3, marginBottom: '8px' }} />
              <h3>No Eligible Parcels Available</h3>
              <p style={{ fontSize: '0.9rem', marginBottom: '16px' }}>You must first book a parcel before requesting doorstep collection.</p>
              <Link to="/parcels/new" className="btn btn-primary btn-sm">
                Book a Parcel Now
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <h3 className="card-title">1. Select Consignment</h3>
              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label className="form-label">
                  Choose Booked Parcel <span className="required">*</span>
                </label>
                <select
                  name="parcel_id"
                  className="form-select"
                  value={formData.parcel_id}
                  onChange={handleChange}
                  required
                >
                  {parcels.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.tracking_id} — To: {p.receiver_name} ({p.destination_city}) [{p.weight} kg, {p.parcel_type}]
                    </option>
                  ))}
                </select>
                {errors.parcel_id && <span className="form-error">{errors.parcel_id}</span>}
              </div>

              <h3 className="card-title">2. Doorstep Pickup Location</h3>

              {/* Service Hub PIN Code Dropdown */}
              <div className="form-group" style={{ marginBottom: '20px', background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <label className="form-label" style={{ fontWeight: 600, color: '#1e293b' }}>
                  Select Available Pickup Service Area (PIN Code) <span className="required">*</span>
                </label>
                <select
                  className="form-select"
                  value={selectedHub}
                  onChange={handleHubSelect}
                  style={{ background: '#ffffff', fontWeight: 500 }}
                >
                  <option value="">-- Choose a Service Hub PIN Code (Auto-fills City & State) --</option>
                  <optgroup label="⚡ Active Agent Service Hubs (Immediate Auto-Assignment)">
                    {hubs.filter((h) => h.has_active_agent).map((h) => (
                      <option key={h.pin} value={h.pin}>
                        {h.pin} — {h.city} ({h.state}) [Active Agent Ready ⚡]
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="📍 Other State Capitals & Postal Hubs">
                    {hubs.filter((h) => !h.has_active_agent).map((h) => (
                      <option key={h.pin} value={h.pin}>
                        {h.pin} — {h.city} ({h.state})
                      </option>
                    ))}
                  </optgroup>
                  <option value="custom">✏️ Enter Custom PIN Code...</option>
                </select>

                {activeHubInfo && (
                  <div style={{ marginTop: '10px', fontSize: '0.85rem' }}>
                    {activeHubInfo.has_active_agent ? (
                      <div style={{ color: '#15803d', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                        <CheckCircle2 size={16} />
                        Active Agent Coverage: An agent is stationed at {activeHubInfo.city} ({activeHubInfo.pin}) for immediate pickup dispatch.
                      </div>
                    ) : (
                      <div style={{ color: '#0369a1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={16} />
                        State Hub: Pickup will be registered in {activeHubInfo.city} ({activeHubInfo.pin}) and queued for agent dispatch.
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label">
                  Sender Pickup Address <span className="required">*</span>
                </label>
                <textarea
                  name="pickup_address"
                  className="form-textarea"
                  rows={2}
                  value={formData.pickup_address}
                  onChange={handleChange}
                  placeholder="Door 10, South End Road, Anna Nagar"
                  required
                />
                {errors.pickup_address && <span className="form-error">{errors.pickup_address}</span>}
              </div>

              <div className="form-grid" style={{ marginBottom: '24px' }}>
                <div className="form-group">
                  <label className="form-label">
                    Pickup PIN Code <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    name="pickup_pin"
                    className="form-input"
                    value={formData.pickup_pin}
                    onChange={handleChange}
                    placeholder="e.g. 600001"
                    maxLength={6}
                    required
                  />
                  {errors.pickup_pin && <span className="form-error">{errors.pickup_pin}</span>}
                  {autoDetected && (
                    <span style={{ fontSize: '0.75rem', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                      <Sparkles size={12} /> Auto-detected details for PIN {formData.pickup_pin}
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">
                    City <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    name="pickup_city"
                    className="form-input"
                    value={formData.pickup_city}
                    onChange={handleChange}
                    placeholder="e.g. Chennai"
                    required
                  />
                  {errors.pickup_city && <span className="form-error">{errors.pickup_city}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">
                    State (Auto-Selected) <span className="required">*</span>
                  </label>
                  <select
                    name="pickup_state"
                    className="form-select"
                    value={formData.pickup_state}
                    onChange={handleChange}
                    required
                  >
                    <option value="">-- Select State --</option>
                    {INDIAN_STATES_AND_UTS.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                  {errors.pickup_state && <span className="form-error">{errors.pickup_state}</span>}
                </div>
              </div>

              <h3 className="card-title">3. Schedule Date</h3>
              <div className="form-group" style={{ maxWidth: '300px', marginBottom: '32px' }}>
                <label className="form-label">
                  Requested Collection Date <span className="required">*</span>
                </label>
                <input
                  type="date"
                  name="requested_date"
                  className="form-input"
                  value={formData.requested_date}
                  onChange={handleChange}
                  min={new Date().toISOString().split('T')[0]}
                  required
                />
                {errors.requested_date && <span className="form-error">{errors.requested_date}</span>}
                <span className="form-hint">Available for scheduling up to 14 days in advance</span>
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => navigate('/dashboard')}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-accent"
                  disabled={submitting}
                >
                  <Truck size={16} /> {submitting ? 'Submitting & Dispatching...' : 'Request Doorstep Collection'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
