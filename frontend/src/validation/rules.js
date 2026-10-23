// Name: Unicode letters, spaces, optional periods for initials
const NAME_REGEX = /^[A-Za-z\u00C0-\u024F\u0900-\u097F]+(?:\.?\s+[A-Za-z\u00C0-\u024F\u0900-\u097F]+)*\.?$/;
const PHONE_REGEX = /^[6-9]\d{9}$/;
const PIN_REGEX = /^[1-9][0-9]{5}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateName(name) {
  if (!name || !name.trim()) return 'Name is required.';
  const trimmed = name.trim();
  if (trimmed.length < 2) return 'Name must contain at least 2 characters.';
  if (trimmed.length > 100) return 'Name cannot exceed 100 characters.';
  if (!NAME_REGEX.test(trimmed)) {
    return 'Name can only contain alphabetic characters, spaces, and optional periods for initials.';
  }
  return null;
}

export function validatePhone(phone) {
  if (!phone || !phone.trim()) return 'Phone number is required.';
  const cleaned = phone.trim().replace(/[\s-]/g, '').replace(/^\+91|^91|^0/, '');
  if (!PHONE_REGEX.test(cleaned)) {
    return 'Phone number must contain exactly 10 digits starting with 6, 7, 8, or 9.';
  }
  return null;
}

export function validatePin(pin) {
  if (!pin || !pin.trim()) return 'PIN code is required.';
  const trimmed = pin.trim();
  if (!PIN_REGEX.test(trimmed)) {
    return 'PIN code must contain exactly 6 digits and cannot start with 0.';
  }
  return null;
}

export function validateEmail(email) {
  if (!email || !email.trim()) return 'Email address is required.';
  if (!EMAIL_REGEX.test(email.trim().toLowerCase())) {
    return 'Please enter a valid email address (e.g. user@example.com).';
  }
  return null;
}

export function validateWeight(weight) {
  if (weight === '' || weight === null || weight === undefined) return 'Weight is required.';
  const num = parseFloat(weight);
  if (isNaN(num)) return 'Weight must be a valid number.';
  if (num <= 0) return 'Weight must be greater than 0 kg.';
  if (num > 50) return 'Maximum weight for this prototype is 50 kg.';
  return null;
}

export function validateAddress(address) {
  if (!address || !address.trim()) return 'Address is required.';
  const trimmed = address.trim();
  if (trimmed.length < 10) return 'Please enter a meaningful address (at least 10 characters).';
  if (trimmed.length > 300) return 'Address cannot exceed 300 characters.';
  return null;
}

export function validateCity(city) {
  if (!city || !city.trim()) return 'City / District is required.';
  const trimmed = city.trim();
  if (trimmed.length < 2) return 'City must contain at least 2 characters.';
  if (trimmed.length > 100) return 'City cannot exceed 100 characters.';
  if (!NAME_REGEX.test(trimmed)) {
    return 'City can only contain alphabetic characters and spaces.';
  }
  return null;
}

export function validateState(state) {
  if (!state || !state.trim()) return 'State / UT is required. Please select your state.';
  const trimmed = state.trim();
  if (trimmed.length < 2) return 'State must contain at least 2 characters.';
  if (trimmed.length > 100) return 'State cannot exceed 100 characters.';
  return null;
}

export function validatePickupDate(dateStr) {
  if (!dateStr) return 'Pickup date is required.';
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const selected = new Date(dateStr);
  selected.setHours(0, 0, 0, 0);

  if (selected < today) return 'Pickup date cannot be in the past.';

  const maxDate = new Date(today);
  maxDate.setDate(maxDate.getDate() + 14);

  if (selected > maxDate) {
    return `Pickup date cannot be more than 14 days in the future (max: ${maxDate.toISOString().split('T')[0]}).`;
  }
  return null;
}
