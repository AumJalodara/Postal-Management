# Module 2 — Verification Walkthrough

---

## 1. Quick Verification Commands

From the project root (`smart-postal-system`):

### Run All Unit & Integration Tests (44 Tests)
```bash
python -m pytest backend/tests -v
```
Expected result: `44 passed, 291 warnings in ~19s`

### Run Module 2 End-to-End Test (24 Steps)
```bash
python data/synthetic/verify_module2_e2e.py
```
Expected result: `ALL 24 MODULE 2 END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY!`

### Run Module 1 Regression Verification (12 Steps)
```bash
python data/synthetic/verify_e2e.py
```
Expected result: `MODULE 1 END-TO-END VERIFICATION COMPLETED SUCCESSFULLY (100% PASS)`

### Build Frontend
```bash
cd frontend && npm run build
```
Expected result: `✓ built in ~3.8s`

---

## 2. Interactive Manual Testing Guide

1. Start Backend:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
2. Start Frontend:
   ```bash
   npm run dev
   ```
3. Open Browser at `http://localhost:3000`:
   - Click **Track Parcel** in the top navigation.
   - Enter `GPM-2026-000003` to view the full chronological timeline with privacy masking.
   - Click **Scan QR** to resolve a sample opaque token.
   - Login as Citizen (`citizen.m2.97853d@example.com` / `Password@123`) to view **My Parcels**, view and print QR labels.
   - Login as Agent (`agent.chennai@postal.gov.in` / `Agent@12345`) to view the **Delivery Queue**, advance consignments, generate OTP, and verify doorstep delivery.
