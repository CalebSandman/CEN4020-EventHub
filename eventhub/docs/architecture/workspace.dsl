workspace "EventHub | Part 3 C4 Architecture" "Revised design after Call 3" {
    model {
        buyer = person "Buyer" "Registers, browses, searches, and purchases tickets worldwide."
        admin = person "Administrator" "Authorized finance and operations staff who update exchange rates and view audit logs."

        updated = softwareSystem "EventHub" "Revised single-application ticketing system incorporating Call 3." {
            app = container "Flask Web Application" "Responsive buyer and administrator routes; one deployable modular monolith." "Python / Flask" {
                boundary = component "HTTP Boundary" "Flask routes, input validation, response rendering and safe text escaping." "Flask blueprints"
                identity = component "Identity & Authorization" "Password hashes, buyer/admin roles, login, safe return URL, session policy and route guards." "Python service"
                catalog = component "Event Catalog" "Browse/search by artist or venue, event details and no-match fallback to all events." "Python service"
                purchasing = component "Purchasing & Orders" "Coordinates mock checkout, order history, confirmation, abandoned-checkout handling and purchase transaction." "Python service"
                pricing = component "Pricing" "Single place for base price, quantity, USF discount eligibility, exchange rate and currency-aware rounding." "Python Decimal service"
                inventory = component "Inventory Repository" "Atomic guarded inventory decrement in the purchase database transaction." "SQL repository"
                audit = component "Audit Trail" "Captures success and failure with timestamp, user, event, quantity, currency and outcome." "Python service"
                administration = component "Administration" "Authorized exchange-rate editing and audit-log viewing, inaccessible from buyer flows." "Flask blueprint + service"
            }
            database = container "EventHub Database" "Users/roles, events, inventory, orders, stored exchange rates, and audit attempts; transactional updates." "SQLite (proposed)" "Database"
            eventSeed = container "Event Setup Data" "Initial event catalog loaded on application setup; not an external provider." "Data file"
        }

        buyer -> app "Browses and purchases tickets" "HTTPS"
        admin -> app "Updates rates and reviews audit records" "HTTPS / restricted routes"
        app -> database "Reads and writes application state" "SQL transaction"
        app -> eventSeed "Imports initial events" "File import"
        boundary -> identity "Login, sessions, roles; protect routes"
        boundary -> catalog "Browse / search; escape user input"
        boundary -> purchasing "Validated checkout and order requests"
        boundary -> administration "Admin-only routes"
        purchasing -> identity "Requires authenticated buyer before accessing orders"
        purchasing -> catalog "Checks event and current availability"
        purchasing -> pricing "Computes one authoritative total"
        purchasing -> inventory "Atomic availability check + decrement"
        purchasing -> audit "Records outcome on all attempt paths"
        inventory -> database "Conditional decrement; same transaction as successful order" "SQL"
        purchasing -> database "Creates order and reads buyer history" "SQL"
        identity -> database "Users, role assignments, sessions as applicable" "SQL"
        catalog -> database "Queries events and inventory" "SQL"
        catalog -> eventSeed "Reads setup catalog" "File import"
        pricing -> database "Reads current rate and pricing inputs" "SQL"
        audit -> database "Writes attempt records" "SQL"
        administration -> identity "Verifies admin role on every request"
        administration -> database "Edits rates and queries audit logs" "SQL"
        administration -> audit "Reads audit history via audit interface"
    }
    views {
        systemContext updated "context-final" {
            include *
            autolayout lr
        }
        container updated "container-final" {
            include *
            autolayout lr
        }
        component app "component-final" {
            include *
            autolayout lr
        }
        styles {
            element "Person" {
                shape Person
                background #0f766e
                color #ffffff
            }
            element "Software System" {
                background #1d4ed8
                color #ffffff
            }
            element "Container" {
                background #2563eb
                color #ffffff
            }
            element "Component" {
                background #60a5fa
                color #10213a
            }
            element "Database" {
                shape Cylinder
                background #475569
                color #ffffff
            }
        }
    }
}
