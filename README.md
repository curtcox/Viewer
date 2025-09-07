# SecureApp - Multi-Layered Access Control Flask Application

SecureApp is a comprehensive Flask-based web application that demonstrates advanced access control through user authentication, payment verification, and terms acceptance tracking. The application features detailed HTTP request analysis, personal content management systems, and secure file handling.

## Features

- **Multi-tier Access Control**: Authentication, payment verification, and terms acceptance
- **Personal Management Systems**: Servers, variables, and secrets with URL-safe naming
- **File Upload & Tracking**: Complete audit trail of user uploads with storage analytics
- **Navigation History**: Detailed browsing history with analytics and pagination
- **Invitation System**: Invitation-only platform with referral tracking
- **Content Analysis**: Comprehensive HTTP request information display
- **Replit Authentication**: Seamless integration with Replit's OAuth system

## Quick Start

For a streamlined setup experience, use the provided scripts:

```bash
# 1. Install all dependencies
./install

# 2. Copy and configure environment variables
cp .env.sample .env
# Edit .env with your configuration

# 3. Check if everything is ready
./doctor

# 4. Run the application
./run
```

## Prerequisites

Before running the application locally, ensure you have the following installed:

- Python 3.8 or higher
- PostgreSQL database (or use Replit's built-in database)
- Git (for cloning the repository)

## Installation & Setup

### Option 1: Automated Setup (Recommended)

Use the provided installation script for Mac and Linux:

```bash
# Clone the repository
git clone <repository-url>
cd secureapp

# Run the automated installer
./install

# Configure your environment
cp .env.sample .env
# Edit .env with your actual values

# Verify everything is working
./doctor

# Start the application
./run
```

### Option 2: Manual Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd secureapp
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Required packages:
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- Flask-Dance
- WTForms
- Werkzeug
- psycopg2-binary
- PyJWT
- OAuthLib
- Gunicorn
- email-validator

### 3. Database Setup

#### Option A: PostgreSQL (Recommended)

1. Install PostgreSQL on your system
2. Create a new database:
```sql
CREATE DATABASE secureapp;
```

3. Create a database user (optional but recommended):
```sql
CREATE USER secureapp_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE secureapp TO secureapp_user;
```

#### Option B: Use Replit's Built-in Database

If running on Replit, the PostgreSQL database is automatically configured and available via environment variables.

### 4. Environment Variables

Copy the sample environment file and configure it:

```bash
cp .env.sample .env
```

Then edit `.env` with your actual values. The sample file includes:

- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Secure session key (generate with the provided command)
- `REPL_ID` - Replit OAuth application ID
- Optional configurations for development

#### Generating Environment Variables

**Session Secret**: Generate a secure random string:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Replit App Configuration**:
1. Go to your Replit account settings
2. Navigate to the "Applications" section
3. Create a new OAuth application
4. Use the provided `REPL_ID` in your environment

### 5. Database Migration

Initialize the database tables:

```bash
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"
```

This will create all necessary tables:
- `users` - User accounts and authentication
- `payment` - Payment tracking and subscriptions
- `terms_acceptance` - Terms acceptance tracking
- `invitation` - Invitation system management
- `cid` - File content and CID mapping
- `page_view` - Navigation history tracking
- `server` - Personal server definitions
- `variable` - Personal variable definitions
- `secret` - Personal secret definitions
- `oauth` - OAuth token storage

## Running the Application

### Using the Run Script (Recommended)

The provided run script handles environment setup and health checks:

```bash
# Development mode (default)
./run

# Production mode
./run production

# Test mode
./run test
```

### Manual Execution

#### Development Mode

```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Run the Flask development server
python main.py
```

The application will be available at `http://localhost:5000`

#### Production Mode

```bash
# Using Gunicorn for production
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Helper Scripts

The repository includes three helper scripts for Mac and Linux:

### `./install` - Dependency Installation
- Checks system requirements (Python 3, pip, PostgreSQL)
- Creates virtual environment
- Installs Python dependencies
- Creates `.env` from `.env.sample`
- Makes all scripts executable

### `./doctor` - Health Check
- Verifies Python and pip installation
- Checks all required Python packages
- Validates environment configuration
- Tests database connectivity
- Ensures all core files are present
- Provides detailed diagnostics and recommendations

### `./run` - Application Runner
- Loads environment variables
- Activates virtual environment
- Performs quick health check
- Creates database tables if needed
- Starts application in specified mode (development/production/test)

## Application Structure

```
secureapp/
├── app.py                 # Flask application factory
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Application routes
├── forms.py              # WTForms form definitions
├── replit_auth.py        # Replit OAuth integration
├── templates/            # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   ├── servers.html
│   ├── variables.html
│   ├── secrets.html
│   ├── settings.html
│   └── ...
└── static/              # Static assets (if any)
```

## Key Features Guide

### 1. Authentication System

The application uses Replit's OAuth for authentication:
- Users must authenticate with their Replit account
- Session management via Flask-Login
- Automatic token refresh handling

### 2. Access Control Layers

Users must satisfy three conditions for full access:
- **Authentication**: Valid Replit login
- **Payment**: Active subscription (configurable plans)
- **Terms**: Acceptance of current terms version

### 3. Personal Management Systems

#### Servers (`/servers`)
- Create named server definitions with multi-line configurations
- URL-safe naming (letters, numbers, dots, hyphens, underscores)
- Access via `/servers/{name}`

#### Variables (`/variables`)
- Manage named variables with text definitions
- Similar URL-safe naming conventions
- Access via `/variables/{name}`

#### Secrets (`/secrets`)
- Secure storage of sensitive information
- Same naming and access patterns
- Access via `/secrets/{name}`

### 4. File Management (`/uploads`)
- Upload files with optional titles and descriptions
- Automatic storage analytics
- Complete audit trail with timestamps

### 5. Navigation Tracking (`/history`)
- Automatic page view tracking
- Detailed analytics and statistics
- Pagination and search capabilities

### 6. Invitation System
- Invitation-only registration
- Referral tracking and analytics
- Admin invitation management

## Configuration Options

### Payment Plans

Modify payment plans in `forms.py`:
```python
plan = SelectField('Plan', choices=[
    ('free', 'Free Plan - $0/year'),
    ('annual', 'Annual Plan - $50/year'),
    # Add more plans as needed
])
```

### Terms Management

Update terms version in `models.py`:
```python
CURRENT_TERMS_VERSION = "1.0"  # Update when terms change
```

### URL Validation

Server, variable, and secret names are validated using regex:
```python
Regexp(r'^[a-zA-Z0-9._-]+$')
```

## Security Considerations

1. **Environment Variables**: Never commit secrets to version control
2. **Session Management**: Uses secure session storage with database backing
3. **CSRF Protection**: All forms include CSRF tokens via Flask-WTF
4. **Password Security**: Werkzeug password hashing with salt
5. **OAuth Integration**: Secure token handling and automatic refresh

## Troubleshooting

### Quick Diagnostics

Run the doctor script for comprehensive health checks:

```bash
./doctor
```

This will check:
- Python and pip installation
- Virtual environment setup
- Python package dependencies
- Environment variable configuration
- Database connectivity
- File permissions
- Core application files

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format in `.env`
   - Ensure database exists and user has permissions
   - Run `./doctor` to test connectivity

2. **Authentication Issues**
   - Verify REPL_ID is correctly configured in `.env`
   - Check Replit OAuth application settings
   - Ensure redirect URLs match

3. **Missing Dependencies**
   - Run `./install` to install all dependencies
   - Check `./doctor` output for missing packages
   - Ensure virtual environment is activated

4. **Permission Errors**
   - Run `chmod +x install doctor run` to fix script permissions
   - Verify database user privileges
   - Check file system permissions

5. **Environment Configuration**
   - Ensure `.env` file exists (copy from `.env.sample`)
   - Verify all required variables are set
   - Use `./doctor` to validate configuration

### Logs and Debugging

The run script provides detailed startup information and error messages.

For development debugging:
```bash
./run development  # Enables Flask debug mode
```

View detailed health information:
```bash
./doctor  # Comprehensive system check
```

## API Endpoints

### Public Routes
- `/` - Landing page (redirects based on auth status)
- `/auth/login` - Replit OAuth login
- `/auth/logout` - User logout

### Protected Routes
- `/content` - Main protected content (requires full access)
- `/profile` - User profile and payment history
- `/uploads` - File upload and management
- `/history` - Navigation history
- `/settings` - Central settings dashboard
- `/servers/*` - Server management routes
- `/variables/*` - Variable management routes  
- `/secrets/*` - Secret management routes

### Error Handlers
- `404` - Custom 404 with CID lookup functionality
- `500` - Server error handling

## Contributing

When contributing to this project:

1. Follow the existing code style and patterns
2. Ensure all new routes include proper authentication
3. Add appropriate validation for user inputs
4. Update this README for any new features
5. Test thoroughly before submitting changes

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review application logs for error details
3. Ensure all prerequisites are properly installed
4. Verify environment variable configuration

---

*This application demonstrates advanced Flask patterns including OAuth integration, multi-layered security, and comprehensive user management systems.*