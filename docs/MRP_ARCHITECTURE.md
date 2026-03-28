# Make-to-Stock (MRP) Architecture

This document outlines the Manufacturing Resource Planning (MRP) process within NexusERP, demonstrating the integration between Production Planning and Shop Floor Inventory Management.

## 1. Macro Process (Level 1: General Flow)
The macro process maps the lifecycle of a Manufacturing Order (MO). It demonstrates how raw materials are staged, consumed, and converted into finished goods.

### Process Description:
1. **Planning:** Production demand triggers the creation of a Manufacturing Order. A specific Bill of Materials (BOM) is linked to the order.
2. **Component Validation:** The system evaluates current warehouse stock against the BOM requirements. If materials are short, procurement is triggered.
3. **Reservation & Production:** If stock is available, it is hard-reserved. Production begins, locking the components.
4. **Completion:** When the user marks the MO as 'Done', the system simultaneously deducts the consumed raw materials and adds the finished good to available inventory.

### Macro Flowchart (Mermaid)
```mermaid
flowchart TD
    classDef systemTask stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Planning ["📋 Production Planning"]
        direction TB
        Start((Production Demand)) --> CreateMO[Create Manufacturing Order]
        CreateMO --> SelectBOM[Select Bill of Materials]
    end

    subgraph Warehouse ["🏭 Shop Floor & Inventory"]
        direction TB
        SelectBOM --> CheckStock{Components Available?}
        CheckStock -- No --> Shortage(((Trigger P2P Process)))
        CheckStock -- Yes --> Reserve[System: Reserve Components]:::systemTask
        Reserve --> StartProd[Start Production]
        StartProd --> Consume[System: Deduct Components]:::systemTask
        Consume --> FinishProd[Mark as Done]
        FinishProd --> AddFG[System: Add Finished Good to Stock]:::systemTask
        AddFG --> Done(((MO Complete)))
    end

```
2. Micro Process (Level 2: Inventory Transaction Engine)

This micro-process details the exact system logic that executes during the `Mark as Done` step in the Manufacturing swimlane. It demonstrates the engine's ability to handle multi-line inventory transactions atomically.

### Process Description:
When an MO is completed, the system must execute multiple inventory adjustments simultaneously. If one component fails to deduct, the entire production run must roll back to prevent ghost inventory.
1. The `mo.finish()` method is called.
2. A Database Transaction `(transaction.atomic)` is opened.
3. The engine iterates through every component listed in the BOM.
4. For each component, a negative `StockMove` is generated, deducting the raw material from the warehouse.
5. Finally, a positive `StockMove` is generated, adding the finished good to the warehouse.
6. The database transaction commits all moves simultaneously.

### Micro System Sequence (Mermaid)
```mermaid
sequenceDiagram
    participant User
    participant View as views.py
    participant MO as Manufacturing Order
    participant Move as StockMove Engine
    participant DB as Database

    User->>View: Clicks "Mark as Done"
    View->>MO: Call mo.finish()
    
    rect rgba(128, 128, 128, 0.15)
        Note over MO, Move: Atomic Database Transaction
        MO->>MO: Change state to 'Done'
        loop For Each BOM Component
            MO->>Move: Create Outbound Move (Consume)
            Move->>DB: Deduct Raw Material On-Hand
        end
        MO->>Move: Create Inbound Move (Produce)
        Move->>DB: Increase Finished Good On-Hand
    end
    
    MO->>DB: Commit Transaction
    DB-->>View: Return HTTP 302 Redirect
    View-->>User: Refresh Page (Status: Done)
```