# Society Management System

**Deployment URL:** https://harsh9702.pythonanywhere.com  
[SMTP Email for user credentials are blocked on free tier Pythonanywhere account but the code is perfect]<!-- Update this with the actual deployment UrL once hosted -->
## Default Credentials
Email: admin1@gmail.com  
Password: admin123 

## Overview

The Society Management System is a web-based application designed to streamline the management of residential societies. It facilitates efficient handling of user roles, property assignments, maintenance billing, and tenant management. This system ensures secure authentication, role-based access control, and automated email notifications for credential distribution.

This project demonstrates proficiency in Django fundamentals, including models, views, templates, authentication, signals, and database relationships. It uses SQLite as the database for simplicity in development and testing.

## Key Features

### User Roles and Authentication
- **Roles**: Admin, Owner, Tenant.
- Single login page with redirection based on user role.
- Only active users can log in.
- Custom decorators for role-based access control.

### Admin Functionalities
- Create and manage Owner accounts (with automatic email sending of credentials).
- Activate/deactivate Owner accounts.
- Create and manage Societies and Flats.
- Assign Owners to Flats.
- Generate and manage Maintenance Bills (PAID/UNPAID status).
- Dashboard with statistics (e.g., total societies, flats, owners, tenants, unpaid bills).

### Owner Functionalities
- View assigned flats and society information.
- View maintenance bills and their status.
- Create and manage Tenants for their flats (with automatic email sending of credentials).
- Dashboard with personal statistics (e.g., flats, tenants, unpaid bills).

### Tenant Functionalities
- View assigned flat details, society information, and owner contact.
- Dashboard for personal overview.

### Additional Features
- Automated email notifications for new Owner and Tenant accounts using Django signals.
- Validation and error handling for all forms and models (e.g., unique constraints, regex validators).
- Responsive UI using Django templates with basic HTML/CSS.
- No self-registration for Owners; only Admins can create them.
- No payment gateway integration.

## Technology Stack

- **Backend**: Python 3.x, Django 6.0.2
- **Database**: SQLite (default Django configuration)
- **Frontend**: Django Templates (HTML5, CSS3)
- **Authentication**: Django's built-in authentication system with custom User model
- **Email**: SMTP integration (configured for Gmail in development; console backend acceptable)
- **Other**: Django signals for post-save actions, validators for data integrity

## Prerequisites

Before setting up the project, ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)
- Virtualenv (recommended for isolated environments)

## Installation and Setup

Follow these steps to set up the project locally:

1. **Clone the Repository**:
git clone https://github.com/h-iori/society-management-system.git
cd society-management-system

2. **Create and Activate a Virtual Environment**:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install Dependencies**:
pip install -r requirements.txt

4. **Configure Environment Variables**:
- Create a `.env` file in the project root.
- Add the following (replace with your Gmail credentials for email functionality):
EMAIL_HOST_USER=your.email@gmail.com  
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your.email@gmail.com
- Note: For production, use secure app passwords and avoid committing `.env` to version control.

5. **Apply Database Migrations**:
python manage.py makemigrations
python manage.py migrate

6. **Create Superuser (Admin Account)**:
python manage.py createsuperuser
- Follow prompts to set username, email, and password. This admin will have the 'ADMIN' role.


## Running the Project

1. **Start the Development Server**:
python manage.py runserver

2. **Access the Application**:
- Open your browser and navigate to `http://127.0.0.1:8000/`.
- Login page: `/login/` (or directly from index if not logged in).
- Admin Dashboard: Redirected after login as Admin.
- Use the superuser credentials created in setup.

## Admin Login Credentials

For testing purposes:
- **Username/Email**: Use the superuser credentials created during setup (e.g., admin@example.com).
- **Password**: As set during `createsuperuser`.
- Note: In a production environment, change these immediately and use secure practices.

## Assumptions Made

- **Email Backend**: Configured for SMTP (Gmail) in development. For testing without real emails, switch to console backend by setting `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` in `settings.py`.
- **No Self-Registration for Owners/Tenants**: Owners are created by Admins, and Tenants by Owners.
- **Flat Assignment**: Flats can be created without owners initially but require owners for bill generation.
- **Tenant Management**: Only one active tenant per flat assumed (enforced via model validation).
- **UI Simplicity**: Basic HTML/CSS used; no advanced frontend frameworks like Bootstrap (can be added as enhancement).
- **Security**: Development mode (DEBUG=True); for production, set DEBUG=False, configure ALLOWED_HOSTS, and use a robust database like PostgreSQL.

## Contributing

This project is open for contributions. If you'd like to contribute, fork the repository and submit a pull request with detailed changes.


## Contact

For any queries, reach out via the repository's issues section or email.

---