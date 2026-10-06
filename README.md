# TableKeeper

TableKeeper is a restaurant reservation service developed for the **Dark Factory Challenge**.

It allows diners to search for available tables, make reservations, receive confirmations, and cancel or modify existing reservations.

## Project Overview

Restaurants have tables with different capacities, opening hours, and cancellation policies.

TableKeeper manages these rules and ensures that reservations are handled safely, including concurrent booking attempts and repeated requests.

The project was developed using a multi-agent software engineering workflow through the **TableOps Factory**.

## Problem Statement

Restaurant reservation systems must handle several important problems:

- Finding suitable available tables
- Preventing double bookings
- Handling simultaneous booking requests
- Maintaining consistent reservation state
- Supporting cancellation and modification
- Applying restaurant opening hours and policies
- Handling repeated or duplicate requests safely

TableKeeper addresses these requirements through a structured domain and verification process.

## Key Features

- Restaurant and table management
- Table availability checking
- Reservation creation
- Reservation cancellation
- Reservation modification
- Prevention of conflicting reservations
- Atomic booking operations
- Idempotent booking requests
- Validation of reservation rules
- Automated testing

## Architecture

The project separates the core reservation domain from validation, state management, and time-related rules.

Main components include:

text
stage-1/
├── app/
│   ├── domain.py
│   ├── security.py
│   ├── state.py
│   ├── time_rules.py
│   └── validation.py
│
└── tests/
    └── test_domain_core.py
