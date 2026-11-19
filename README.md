# PointsTrack - Supermarket Loyalty Points Management System

A web application for managing a supermarket loyalty programme. Cashiers record purchases to award points, members redeem points for discounts, and managers handle disputes and view reports.

## Features

- **Login / Register** - Secure login with sessions. Different users (admin, cashier, manager).
- **Dashboard** - Total members, purchases, points issued, points redeemed, open disputes.
- **Members** - Enrol new members with unique phone + card number (LC-0001, LC-0002...). Search by name, card or phone.
- **Record Purchase** - Every KES 100 spent = 1 point. A receipt can only be rewarded once (duplicate check).
- **Redeem Points** - 1 point = KES 1 discount. Cannot redeem more than balance.
- **Disputes** - Log customer complaints about missing/incorrect points.
- **Activity Log** - Every action (login, purchase, redeem, dispute) is recorded with user, date and details.
- **Reports** - Total sales, points issued, outstanding points, points awarded by cashier, balance reconciliation.

## Tech Used

- Python + Flask
- SQLite (built into Python, no setup needed)
- HTML + CSS (no framework)
- Jinja2 templates (Flask's `{{ }}` and `{% for %}`)

## Folder Structure

## How to Run

1. Install Flask (only once):

2. Run the app:

3. Open in your browser:

## Login Details

Demo account created automatically on first run:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |

You can also click **Register here** on the login page to create a new account (e.g. cashier1 / manager1).

## Business Rules

1. **Points Earning:** `points = amount // 100` - e.g. KES 450 = 4 points, KES 99 = 0 points.
2. **Duplicate Receipt:** Same receipt number cannot be used twice. System shows an error.
3. **Redemption:** Cannot redeem more than current balance.
4. **Unique Member:** Phone number must be unique. Card numbers are auto-generated (LC-0001, LC-0002...).
5. **Audit Trail:** Every purchase, redemption and dispute is saved in Activity Log.

## Testing It

1. Login as `admin` / `admin123`
2. Go to Members -> Enrol `Jane Wanjiku` / `0712345601` -> Gets card `LC-0001`
3. Go to Record Purchase -> Card `LC-0001`, Receipt `RC-100201`, Amount `4500` -> Gets 45 points
4. Try same receipt again -> Should show "Receipt already rewarded"
5. Go to Members -> View History -> Redeem 20 points -> Balance becomes 25
6. Go to Disputes -> Log a dispute -> Shows in Dispute Register
7. Go to Dashboard / Reports / Activity Log -> All numbers update automatically