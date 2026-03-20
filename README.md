# NexusERP: Enterprise Multi-Tenant SaaS Platform

NexusERP is a comprehensive, production-ready Enterprise Resource Planning (ERP) system built with Django. It features a complete Multi-Tenant SaaS architecture, Double-Entry Accounting, Background Task Queues, and a secure RESTful API.

<img width="1919" height="993" alt="NexusERP" src="https://github.com/user-attachments/assets/418c74a9-c263-409b-8bf4-039f9b4c31af" />



## 🚀 Core Architecture & Features

### 1. Multi-Tenant SaaS Engine (Row-Level Security)
Built to host hundreds of isolated companies within a single database instance.
* Custom `TenantAwareModel` abstract classes and overridden `Manager` querysets ensure data is strictly partitioned by the active user's company context.
* Thread-local middleware safely injects tenant IDs across all HTTP requests and API calls.
* Dedicated **SaaS Control Center** for global superusers to provision new workspaces.

### 2. Core ERP Modules
* **Supply Chain & Inventory:** Multi-warehouse management, dynamic stock valuation, and automated reordering rules based on predictive AI/churn-rate formulas.
* **Manufacturing (MRP):** Bill of Materials (BOM) logic with multi-level component consumption and real-time stock deduction.
* **Commerce (CRM & Logistics):** Lead-to-Order pipelines, Sales/Purchase Orders, and shipment tracking.
* **Human Resources:** Granular employee org charts, reporting structures, and time-off tracking.

### 3. Double-Entry Accounting Engine
* Fully compliant General Ledger that dynamically responds to state changes across the ERP (e.g., confirming a Sales Order automatically reserves stock, but creating the Invoice triggers the Debit/Credit journal entries).
* Automated calculation of Income Statements (P&L) and Balance Sheets with accurate point-in-time Date Filtering.

### 4. Asynchronous Message Broker (Celery + Redis)
* Background task queues handle heavy computational operations (e.g., `xhtml2pdf` generation) without blocking the main web thread.
* Features automated PDF invoice and PO generation directly emailed to client/supplier inboxes.

### 5. Enterprise Security & Integrations
* **Granular RBAC:** Custom Workspace Roles map directly to Django's native permission framework dynamically.
* **RESTful API:** Developed with Django REST Framework (DRF) featuring Token Authentication and tenant-isolated endpoints for external integrations.
* **Automated Sequences:** Custom sequence generator ensures customizable, auto-incrementing document IDs (e.g., `SO-0001`) with row-level database locking.

## 🛠️ Technology Stack
* **Backend:** Python, Django 5.x, Django REST Framework
* **Database:** SQLite (Dev) / PostgreSQL (Production ready)
* **Message Broker:** Celery, Redis (Eventlet pool for Windows)
* **Frontend:** TailwindCSS, Alpine.js, FontAwesome
* **Reporting:** xhtml2pdf, CSV exporters

## ⚙️ Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/NexusERP.git](https://github.com/amirhosseinse7/NexusERP.git)
   cd NexusERP

    Set up the virtual environment:
    Bash

    python -m venv venv
    source venv/Scripts/activate # Windows: venv\Scripts\activate

    Install dependencies:
    Bash

    pip install -r requirements.txt

    Environment Variables:
    Create a .env file in the root directory and add your secret key:
    Code snippet

    SECRET_KEY=your_secret_key_here
    DEBUG=True

    Run Migrations & Start the Server:
    Bash

    python manage.py migrate
    python manage.py runserver

    Start the Celery Worker (Requires Redis):
    Bash

    celery -A config worker -l info -P eventlet

🔐 System Access (SaaS Admin)

To access the SaaS Super-Admin panel and provision your first workspace, create a global superuser:
Bash

python manage.py createsuperuser

Log in at http://127.0.0.1:8000/saas/ to launch a new tenant.


⚖️ License & Copyright

Copyright © 2026. All Rights Reserved. This repository is provided for portfolio and demonstration purposes only. No license is granted to copy, modify, distribute, or use this software for commercial or non-commercial purposes without explicit written permission.
