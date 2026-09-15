# Nexora B2B SupplyFlow

**B2B Supply Chain & Business Operations Management Platform**

Nexora B2B SupplyFlow is a modular backend platform designed to centralize and automate core B2B business operations, including customer management, orders, invoices, payments, pricing, analytics, authentication, and audit tracking.

The project is built with a focus on **clean architecture, modularity, security, scalability, and maintainability**, making it suitable for small and medium-sized businesses that need a centralized system for managing their commercial workflow.

---

##  Key Features

###  Authentication & Authorization

* Secure user authentication
* JWT-based access tokens
* Company-based authentication
* Role-based access control
* User and company context
* Password validation and security rules

###  Customer Management

* Create and manage customers
* Customer contact information
* Tax and business information
* Credit limit management
* Payment terms
* Customer activation/deactivation
* Customer search and listing

###  Order Management

* Create and manage B2B orders
* Order status management
* Customer-order relationships
* Order lifecycle tracking
* Business validation

###  Invoice Management

* Invoice creation and management
* Customer and order association
* Invoice status tracking
* Payment status integration

###  Payment Management

* Payment recording
* Payment tracking
* Invoice-payment relationships
* Payment status management

###  Pricing

* Centralized pricing management
* Product/service pricing rules
* Customer-oriented pricing logic
* Extensible pricing architecture

###  Analytics & Dashboard

* Business analytics endpoints
* Dashboard data aggregation
* KPI-oriented backend services
* Sales and business performance insights

###  Audit & Activity Tracking

* Audit logging
* Business activity tracking
* User action monitoring
* Traceability of important operations

---

##  Architecture

Nexora follows a modular backend architecture where each business domain is isolated into its own module.

```text
Nexora_B2B_SupplyFlow/
│
├── app/
│   ├── auth/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── customers/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── orders/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── invoices/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── payments/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── pricing/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── ...
│   │
│   ├── analytics/
│   │   ├── dashboard_router.py
│   │   ├── dashboard_schemas.py
│   │   └── ...
│   │
│   ├── web/
│   │   └── ...
│   │
│   ├── core/
│   │   ├── audit.py
│   │   └── ...
│   │
│   └── main.py
│
├── scripts/
│
├── requirements.txt
├── README.md
└── ...
```

The modular structure makes it easier to:

* Add new business domains
* Maintain existing features
* Test individual modules
* Scale the application
* Apply domain-specific business logic
* Collaborate efficiently in a team

---

##  Technology Stack

| Technology       | Purpose                     |
| ---------------- | --------------------------- |
| **Python**       | Backend development         |
| **FastAPI**      | REST API framework          |
| **Pydantic**     | Data validation and schemas |
| **JWT**          | Authentication              |
| **SQL Database** | Persistent business data    |
| **Docker**       | Containerization            |
| **Git & GitHub** | Version control             |
| **REST API**     | Client-server communication |

---

##  Business Workflow

Nexora is designed around a typical B2B commercial workflow:

```text
Company
   │
   ├── Users
   │
   └── Customers
          │
          ▼
        Orders
          │
          ▼
       Invoices
          │
          ▼
       Payments
          │
          ▼
       Analytics
```

This structure allows the platform to connect commercial operations from customer acquisition through payment and business analysis.

---

##  Authentication Flow

The authentication system follows a token-based architecture:

```text
Client
  │
  ▼
Login
  │
  ▼
Authentication API
  │
  ▼
JWT Access Token
  │
  ▼
Protected API Endpoints
  │
  ├── Customers
  ├── Orders
  ├── Invoices
  ├── Payments
  ├── Pricing
  └── Analytics
```

Protected endpoints require a valid access token.

---

##  Installation

### 1. Clone the repository

```bash
git clone https://github.com/hedijlail/Nexora_B2B_SupplyFlow.git
cd Nexora_B2B_SupplyFlow
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

##  Environment Variables

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=your_database_url

SECRET_KEY=your_secret_key

ACCESS_TOKEN_EXPIRE_MINUTES=30

ENVIRONMENT=development
```

> Never commit sensitive credentials, API keys, database passwords, or secret keys to GitHub.

---

##  Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

### API Documentation

FastAPI automatically provides interactive API documentation.

**Swagger UI**

```text
http://localhost:8000/docs
```

**ReDoc**

```text
http://localhost:8000/redoc
```

---

##  Docker

The project is designed to support containerized development and deployment.

Build the application:

```bash
docker build -t nexora-supplyflow .
```

Run the container:

```bash
docker run -p 8000:8000 nexora-supplyflow
```

For multi-container environments, Docker Compose can be used to orchestrate the API, database, and supporting services.

---

##  API Testing

The API can be tested using:

* Swagger UI
* Postman
* cURL
* Automated tests

Example:

```bash
curl http://localhost:8000/
```

Protected endpoints should be tested using a valid JWT access token.

---

##  Development Roadmap

The project is actively evolving toward a complete B2B business management platform.

### Completed / In Progress

* [x] Modular FastAPI backend
* [x] Authentication foundation
* [x] JWT authentication
* [x] Customer management
* [x] Orders module
* [x] Invoices module
* [x] Payments module
* [x] Pricing module
* [x] Audit logging
* [x] Analytics foundation
* [ ] Automated testing
* [ ] Advanced dashboard
* [ ] Inventory management
* [ ] Product management
* [ ] Notifications
* [ ] CI/CD pipeline
* [ ] Production deployment
* [ ] Advanced reporting

---

##  Future Improvements

Planned improvements include:

* Advanced inventory and warehouse management
* Product catalog
* Supplier management
* Purchase orders
* Advanced financial reporting
* Real-time notifications
* Role and permission management
* Frontend dashboard
* Automated testing and coverage
* CI/CD automation
* Production monitoring
* Cloud deployment
* API versioning
* Performance optimization

---

##  Security

Security is an important part of the project architecture.

The application is designed to support:

* JWT-based authentication
* Password validation
* Role-based authorization
* Protected API endpoints
* Input validation using Pydantic
* Audit logging
* Environment-based secret management

Sensitive configuration should always be stored using environment variables or a secure secret-management solution.

---

##  Project Goals

Nexora aims to provide a scalable foundation for B2B companies that need to manage:

**Customers → Orders → Invoices → Payments → Analytics**

The long-term goal is to evolve the platform into a complete **B2B supply chain and business operations management solution**.

---

##  Author

**Hedi Jlail**

Computer Science Student | AI & Software Development

GitHub: [@hedijlail](https://github.com/hedijlail)

---

##  License

This project is currently under development.

License information will be added when the project reaches its first stable release.

---

⭐ If you find this project interesting, consider giving the repository a star.
