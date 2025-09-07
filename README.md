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

## Prerequisites

Before running the application locally, ensure you have the following installed:

- Python 3.8 or higher
- PostgreSQL database
- Git (for cloning the repository)

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd secureapp
```

### 2. Install Python Dependencies

```bash
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

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/secureapp

# Session Secret (generate a random string)
SESSION_SECRET=your-super-secret-session-key-here

# Replit OAuth Configuration (for authentication)
REPL_ID=your-replit-app-id

# Optional: Custom issuer URL (defaults to Replit's)
ISSUER_URL=https://replit.com/oidc
```

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

### Development Mode

Run the Flask development server:

```bash
python main.py
```

The application will be available at `http://localhost:5000`

### Production Mode

Use Gunicorn for production deployment:

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

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

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database exists and user has permissions

2. **Authentication Issues**
   - Verify REPL_ID is correctly configured
   - Check Replit OAuth application settings
   - Ensure redirect URLs match

3. **Missing Tables**
   - Run the database creation script
   - Check for migration errors in logs

4. **Permission Errors**
   - Verify file upload directory permissions
   - Check database user privileges

### Logs and Debugging

Enable debug mode for detailed error information:
```python
app.debug = True  # Only for development
```

View application logs:
```bash
tail -f logs/app.log  # If logging to file
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