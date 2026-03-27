# Order-to-Cash (O2C) Architecture

This document outlines the standard Order-to-Cash process within NexusERP, demonstrating the integration between Commerce (CRM/Sales), Logistics (Inventory), and Finance (Accounting).

## 1. Macro Process (Level 1: General Flow)
The macro process maps the user journey from an Opportunity to a Paid Invoice. It features cross-module boundaries and conditional logic for order fulfillment.

### Process Description:
1. **Commerce:** The cycle begins when an Opportunity is won. A Sales Order is drafted and lines are added.
2. **Logistics Hand-off:** Upon order confirmation, the system automatically checks `on_hand` inventory and reserves the required stock.
3. **Fulfillment:** Warehouse staff ship the goods. If rejected, an RMA (Return) is processed.
4. **Finance Hand-off:** Once delivered, Finance drafts an Outbound Invoice.
5. **Accounting:** Posting the invoice triggers the core GL engine, and the cycle ends when the payment is registered.

### Macro Flowchart (Mermaid)
```mermaid
flowchart TD
    classDef systemTask stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Commerce ["Commerce (Sales)"]
        direction TB
        Start((Opportunity Won)):::startEvent --> Draft[Create Sales Order]
        Draft --> Lines[Add Material & Qty]
        Lines --> GateConfirm{Confirm Sale?}:::gateway
        GateConfirm -- No --> Cancelled(((Cancelled))):::endEvent
        GateConfirm -- Yes --> Confirm[Confirm Order]
    end

    subgraph Logistics ["Logistics (Warehouse)"]
        direction TB
        Confirm --> Reserve[System: Auto-Reserve Stock]:::systemTask
        Reserve --> Ship[Ship Goods to Customer]
        Ship --> GateDelivery{Accepted?}:::gateway
        GateDelivery -- No --> Return[Process Return]
        Return --> RMA(((RMA Logged))):::endEvent
    end

    subgraph Finance ["Finance (Accounting)"]
        direction TB
        GateDelivery -- Yes --> Invoice[Create Outbound Invoice]
        Invoice --> Post[Post to Ledger]
        Post --> Journal[System: Double-Entry GL Posting]:::systemTask
        Journal --> Payment[Register Bank/Cash Payment]
        Payment --> Paid(((Order Paid))):::endEvent
    end
```        
## 2. Micro Process (Level 2: Automated GL Posting)
This micro-process details the exact system logic that executes during the Post to Ledger step in the Finance swimlane. It demonstrates the transactional integrity of the Double-Entry Accounting engine.

### Process Description:
When a user clicks "Post Invoice," the system must guarantee that Debits equal Credits before committing to the PostgreSQL database.
1. The `invoice.post()` method is called.
2. A Database Transaction `transaction.atomic` is opened to prevent partial data writes if a failure occurs.
3. The system queries the `financial_reports` logic to identify the correct Revenue (Credit) and Accounts Receivable (Debit) accounts.
4. The engine verifies `Total Debits == Total Credits`.
5. If unbalanced, a `ValidationError` triggers a rollback. If balanced, the commit succeeds.

### Micro System Sequence (Mermaid)
```mermaid
sequenceDiagram
    participant User
    participant View as views.py
    participant Model as Invoice Model
    participant DB as Database
    participant GL as JournalItem Engine

    User->>View: Clicks "Post Invoice"
    View->>Model: Call invoice.post()
    
    rect rgba(128, 128, 128, 0.15)
        Note over Model, GL: Atomic Database Transaction
        Model->>Model: Change state to 'Posted'
        Model->>GL: Trigger GL Generation
        GL->>GL: Calculate Subtotal & Tax
        GL->>DB: Insert Credit Line (Revenue Account)
        GL->>DB: Insert Debit Line (Account Receivable)
        
        GL-->>GL: Verify: Total Debits == Total Credits?
        opt If Unbalanced
            GL-->>View: Raise ValidationError (Rollback)
        end
    end
    
    Model->>DB: Commit Transaction
    DB-->>View: Return HTTP 302 Redirect
    View-->>User: Refresh Page (Status: Posted)
```