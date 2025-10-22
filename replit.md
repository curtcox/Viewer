# Overview

Viewer is a Flask-based web application focused on analysing HTTP requests and presenting rich diagnostics. User authentication, subscription management, and terms acceptance now live in external services; this application assumes an already-authenticated user context and concentrates on content tooling and observability features.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
The application is built on Flask with SQLAlchemy ORM for database operations. The architecture follows a traditional MVC pattern with clear separation of concerns:
- **Models**: User plus supporting entities for aliases, servers, variables, secrets, and analytics
- **Views**: Jinja2 templates with Bootstrap 5 for responsive UI
- **Controllers**: Route handlers managing authentication, payments, and content access

## Authentication & Authorization
Flask-Login provides session management for the default application user. External identity and billing providers determine who may access the tool, allowing this service to focus on product functionality rather than subscription logic.

## Database Design
SQLAlchemy with declarative base provides the ORM layer:
- **User Model**: Core user data plus helper methods for request analysis features
- **Supporting Models**: Records for servers, aliases, variables, secrets, page views, and historical invocations
- **Relationships**: One-to-many relationships with cascade delete for data integrity

## Form Handling
WTForms provides server-side validation with CSRF protection:
- **Custom Validators**: Username and email uniqueness validation
- **Security**: Password strength requirements and confirmation matching
- **User Experience**: Field-level error display with Bootstrap styling

## Frontend Architecture
Bootstrap 5 with custom CSS provides a responsive, accessible interface:
- **Component-Based**: Reusable card layouts and navigation components
- **Icon Integration**: Font Awesome icons for visual consistency
- **Responsive Design**: Mobile-first approach with grid system

## Security Features
- **Password Security**: Werkzeug password hashing with salt
- **Session Management**: Secure session handling with configurable secrets
- **Access Guards**: Decorator-based route protection with redirect handling
- **CSRF Protection**: Form token validation on all POST requests

# External Dependencies

## Frontend Libraries
- **Bootstrap 5.3.0**: CSS framework for responsive design and components
- **Font Awesome 6.4.0**: Icon library for UI elements
- **CDN Delivery**: External hosting for faster load times and caching

## Python Packages
- **Flask**: Web framework for routing and request handling
- **Flask-SQLAlchemy**: ORM for database operations and model relationships
- **Flask-Login**: User session management and authentication
- **Flask-WTF**: Form handling with CSRF protection and validation
- **WTForms**: Form field validation and rendering
- **Werkzeug**: WSGI utilities and password hashing

## Database
- **SQLAlchemy**: Database abstraction layer supporting multiple backends
- **Connection Pooling**: Configured with pool recycling and health checks
- **Environment Configuration**: Database URL from environment variables

## Deployment Infrastructure
- **ProxyFix**: Werkzeug middleware for handling proxy headers
- **Environment Variables**: Configuration through DATABASE_URL and SESSION_SECRET
- **WSGI Ready**: Production deployment compatibility