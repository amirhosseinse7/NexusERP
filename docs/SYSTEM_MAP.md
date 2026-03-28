# NexusERP: Master System Map & Module Architecture

This document provides the Level 0 and Level 1 architectural mapping of the NexusERP platform. It illustrates how the multi-tenant SaaS layer controls access, how the major operational modules interact, and how foundational master data is managed.

## 1. Level 0: Master Module Interaction Map
This diagram illustrates the macro-level data flow across the entire ERP platform. It shows how a business event in the CRM triggers a cascade of automated actions through the Supply Chain, Manufacturing, and ultimately ends in the Finance General Ledger.

```mermaid
flowchart TD
    classDef systemTask stroke-width:2px,stroke-dasharray: 5 5;

    subgraph SaaS ["Global SaaS Control Layer"]
        direction TB
        SuperAdmin[SaaS Super-Admin] -->|Provisions| TenantDB[(Isolated Tenant Workspace)]:::saas
    end

    subgraph TenantDB
        direction TB
        
        %% Core Modules
        CRM[🛒CRM & Sales]:::module
        Logistics[Logistics & Inventory]:::module
        MRP[Manufacturing]:::module
        HR[Directory & HR]:::module
        Finance[Finance & Accounting]:::finance

        %% Relationships
        HR -.->|Provides Users/Roles| CRM
        HR -.->|Provides Users/Roles| Logistics
        
        CRM -->|Generates Demand| Logistics
        CRM -->|Triggers Outbound Invoices| Finance
        
        Logistics -->|Triggers Stock Shortage| MRP
        Logistics -->|Triggers Purchase Bills| Finance
        
        MRP -->|Consumes/Produces Stock| Logistics
    end
```
## 2. SaaS Provisioning & Access Control (Administrative Flow)
This process maps the strict boundary between Global SaaS Administrators and Workspace Tenant Administrators. It demonstrates the RBAC (Role-Based Access Control) lifecycle.

### Process Description:
1. Global SaaS: The system owner provisions a new Workspace and creates an initial Tenant Admin.
2. enant Configuration: The Tenant Admin logs into their isolated workspace and configures company profiles and document sequences.
3. RBAC: The Tenant Admin creates granular roles (mapping directly to Django permissions).
4. Onboarding: The Tenant Admin invites employees, assigns roles, and grants system access.

```mermaid
flowchart TD
    classDef startEvent stroke-width:2px,stroke:#28a745;
    classDef endEvent stroke-width:2px,stroke:#dc3545;
    classDef systemTask stroke-width:2px,stroke-dasharray: 5 5;

    subgraph GlobalAdmin ["SaaS Control Center (Superuser)"]
        direction TB
        Start((Client Signs Up)) --> ProvTenant[Provision New Workspace]
        ProvTenant --> GenAdmin[Generate Initial Tenant Admin]
        GenAdmin --> Isolate[System: Isolate Tenant Database Context]:::systemTask
    end

    subgraph TenantAdmin ["Workspace Admin (Tenant Level)"]
        direction TB
        Isolate --> ConfigCorp[Configure Company Profile & Domain]
        ConfigCorp --> ConfigSeq[Define Document Sequences]
        ConfigSeq --> CreateRoles[Create Custom System Roles]
        CreateRoles --> MapPerms[System: Map Django Permissions]:::systemTask
        MapPerms --> AddUsers[Invite Employees & Assign Roles]
        AddUsers --> Active(((Workspace Active)))
    end
```
## 3. Master Data & Human Resources Flow
This maps the foundational directory processes required before transactional operations (like sales or manufacturing) can occur.

### Process Description:
1. Partner Directory: Customers and Suppliers must be registered before Commerce and Logistics can operate.
2. HR Organization: Departments are established, and Employees are mapped to those departments.
3. Time-Off Management: Employees submit leave requests which route to managers for approval, impacting operational capacity.

```mermaid
flowchart TD
    classDef systemTask stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Directory ["Master Data Management"]
        direction TB
        CreatePartner[Register Business Partner]
        CreatePartner --> CheckType{Partner Type?}
        CheckType -- Customer --> CRMReady[Available for CRM/Sales]:::systemTask
        CheckType -- Supplier --> POReady[Available for Purchasing]:::systemTask
    end

    subgraph HRModule ["Human Resources"]
        direction TB
        CreateDept[Establish Departments] --> AddEmp[Onboard Employee]
        AddEmp --> LeaveReq[Employee Submits Time-Off]
        LeaveReq --> Approve{Manager Approves?}
        Approve -- No --> Reject[Notify Employee]
        Approve -- Yes --> LogLeave[System: Update Capacity Calendar]:::systemTask
    end
```

### 4. Transactional Engines
For detailed, system-level documentation of the core operational engines, please refer to the following architectural mappings:
## . [Order-to-Cash (O2C) & GL Engine](docs/O2C_ARCHITECTURE.md): Details the sales pipeline, stock reservation, and double-entry accounting execution.
## . [Procure-to-Pay (P2P) & AI Replenishment](docs/P2P_ARCHITECTURE.md): Details the purchasing lifecycle and the automated background CRON worker.
## . [Make-to-Stock (MRP)](docs/MRP_ARCHITECTURE.md):Details the Bill of Materials expansion and atomic multi-stage inventory transactions. Details the Bill of Materials expansion and atomic multi-stage inventory transactions.
