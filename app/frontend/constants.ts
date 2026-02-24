export const DIAGRAM_TYPES = [
	'Sequence',
	'Use Case',
	'Class',
	'Object',
	'Activity',
	'Component',
	'Deployment',
	'State',
	'Timing',
]

export const DEFAULT_DIAGRAM_TYPE = DIAGRAM_TYPES[0]

export const DIAGRAM_TEMPLATES: Record<string, string> = {
	Sequence: `@startuml
actor User
participant "Web App" as A
participant "API Server" as B
database "Database" as C

User -> A: Login Request
A -> B: Authenticate
B -> C: Query User
C --> B: Return User Data
B --> A: Authentication Response
A --> User: Login Result
@enduml`,
	'Use Case': `@startuml
left to right direction
actor User
actor System
User --> (Submit Request)
(Submit Request) --> System
System --> (Process Request)
System --> (Send Response)
@enduml`,
	Class: `@startuml
class User {
-String username
-String email
+login()
+logout()
}

class Post {
-String title
-String content
-Date createdAt
+publish()
}

User "1" -- "many" Post : creates
@enduml`,
	'Object': `@startuml
object "Order #42" as Order
object "Customer" as Customer
object "Payment" as Payment

Customer : name = "Alice"
Order : status = "Pending"
Payment : method = "Credit Card"

Customer --> Order : places
Order --> Payment : uses
@enduml`,
	Activity: `@startuml
|User|
start
:Open application;
:Enter credentials;
if (Credentials valid?) then (yes)
  :Show dashboard;
else (no)
  :Show error message;
endif
:Proceed with task;
stop
@enduml`,
	'Component': `@startuml
[Web Client] --> [REST API]
[REST API] --> [Service Layer]
[Service Layer] --> [Database]
[Service Layer] --> [Queue]
@enduml`,
	'Deployment': `@startuml
node "Client" {
  component "Web App"
}

node "Server" {
  component "API"
  database "DB"
}

"Web App" --> "API"
"API" --> "DB"
@enduml`,
	State: `@startuml
[*] --> Idle
Idle --> Processing : start
Processing --> Idle : success
Processing --> Error : failure
Error --> Idle : reset
@enduml`,
	Timing: `@startuml
robust "Sensor" as Sensor
concise "Controller" as Controller

Sensor is Idle
Controller is Idle
@0
Sensor -> Controller: heartbeat
@100
Controller -> Sensor: ack
@enduml`,
}

export const MINDMAP_TEMPLATE = `@startmindmap
* Central Topic
** Branch A
*** Detail A1
*** Detail A2
** Branch B
*** Detail B1
*** Detail B2
@endmindmap`

export const UI_MOCKUP_TEMPLATE = `@startsalt
{
  Just plain text
  [This is my button]
  ()  Unchecked radio
  (X) Checked radio
  []  Unchecked box
  [X] Checked box
  "Enter text here   "
  ^This is a droplist^
}
@endsalt`

export const GANTT_TEMPLATE = `@startgantt
Project starts 2026-01-01
[Discovery] lasts 5 days
[Design] lasts 10 days
[Build] lasts 15 days
[QA] lasts 7 days
[Launch] happens at 2026-02-07
[Design] starts at [Discovery]'s end
[Build] starts at [Design]'s end
[QA] starts at [Build]'s end
@endgantt`

export const ERD_TEMPLATE = `@startchen

entity "Customer" as CUSTOMER {
  "customer number" as Number <<key>>
  "member bonus" as Bonus <<derived>>
  "first and last names" as Name <<multi>>
}

entity "Movie" as MOVIE {
  "barcode" as Code
}

relationship "was-rented-to" as RENTED_TO {
  "date rented" as Date
}

RENTED_TO -1- CUSTOMER
RENTED_TO -N- MOVIE

@endchen
`
