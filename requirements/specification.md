# Asset Inventory Web Application

## 1. Document Information

- **Document:** Product and Functional Specification
- **Application:** Asset Inventory Web Application
- **Document version:** 1.0
- **Status:** Initial user requirements
- **Primary audience:** Product owner, solution architect, frontend developer, backend developer, QA tester, system administrator, and business stakeholders

## 2. Purpose

The organization requires a secure, responsive, and easy-to-use web application for maintaining an accurate inventory of company assets throughout their lifecycle. The application must provide a single source of truth for asset identity, ownership, assignment, location, condition, status, financial information, supporting documents, and change history.

The application must allow authorized users to register assets, find them quickly, assign them to people or locations, transfer them, record maintenance, perform stock checks, and retire or dispose of them. Managers must have dashboards and reports that help identify missing, unassigned, overdue, under-maintenance, warranty-expiring, and end-of-life assets.

## 3. Business Goals

The application must support the following goals:

1. Maintain one reliable and searchable asset inventory.
2. Reduce spreadsheet-based and duplicate asset records.
3. Improve accountability by showing the current custodian, department, and location of every asset.
4. Preserve a complete lifecycle and audit history for each asset.
5. Accelerate asset registration, assignment, transfer, return, maintenance, verification, and disposal.
6. Support regular physical inventory checks using asset tags, barcodes, or QR codes.
7. Notify responsible users about important dates, overdue actions, and data-quality issues.
8. Provide management reports and exportable data for operational and audit purposes.
9. Enforce role-based access and protect confidential asset and employee information.
10. Make routine inventory tasks usable from desktop, tablet, and mobile browsers.

## 4. Scope

### 4.1 In Scope

The first production release must include:

- User authentication and role-based authorization
- Asset registration and editing
- Unique asset tags
- Asset categories and configurable reference data
- Employee, department, location, supplier, and cost-center references
- Asset assignment, transfer, return, reservation, and checkout history
- Asset status and condition management
- Maintenance and repair records
- Warranty, contract, and expiry tracking
- Asset retirement, loss, theft, and disposal workflows
- Attachments, notes, and asset images
- Powerful search, filtering, sorting, and pagination
- Barcode or QR-code representation and scanning support where the device/browser permits it
- Bulk import and export through CSV
- Dashboard, operational reports, and saved views
- Physical inventory or stocktake sessions
- Notifications and reminders
- Full audit history for important actions
- Data validation and duplicate detection
- Responsive and accessible web experience

### 4.2 Out of Scope for the Initial Release

The following are not mandatory for the first release unless separately approved:

- Native iOS or Android applications
- Automated discovery of network devices
- Remote device control or software deployment
- Procurement approval and purchase-order processing
- Full accounting, depreciation calculation, or general-ledger posting
- Advanced contract management
- GPS tracking of assets
- RFID hardware integration
- External customer asset management
- Predictive maintenance using machine learning

The design should allow these capabilities to be added later without requiring a complete rewrite.

## 5. Users and Roles

### 5.1 System Administrator

The System Administrator can:

- Manage users, roles, permissions, and application configuration
- Manage categories, statuses, conditions, locations, departments, cost centers, suppliers, and other reference data
- View all assets and audit records
- Configure numbering rules, notification rules, retention settings, and import templates
- Correct data when authorized, without deleting audit history
- Lock or deactivate users and reference records

### 5.2 Asset Manager

The Asset Manager can:

- Create, edit, import, assign, transfer, return, maintain, retire, and dispose of assets
- Start and close stocktake sessions
- Review exceptions and approve controlled lifecycle actions
- View organization-wide dashboards and reports within the manager's permitted organizational scope
- Resolve duplicate or incomplete records

### 5.3 Department Manager

The Department Manager can:

- View assets belonging to the manager's permitted department or departments
- Review assignments and exceptions
- Approve transfers, returns, or disposal requests when approval is configured
- View department reports and export permitted data
- Confirm assets during a stocktake

### 5.4 Inventory Operator or Technician

The Inventory Operator can:

- Register and update assets within an assigned scope
- Scan asset tags
- Perform assignments, transfers, returns, maintenance updates, and stocktake counts as permitted
- Upload supporting evidence and record condition notes
- View operational work queues

### 5.5 Employee or Asset Custodian

The Employee can:

- View assets currently assigned to the employee
- Acknowledge receipt or return when required
- Report an asset as damaged, missing, lost, or stolen
- Request a transfer, return, or service action
- View permitted history for the employee's own assigned assets

### 5.6 Auditor or Read-Only User

The Auditor can:

- View permitted assets, lifecycle history, stocktake results, and audit logs
- Run and export permitted reports
- Not create, modify, approve, or delete operational records

### 5.7 Permission Rules

- Access must follow least-privilege principles.
- Permissions must support both role and organizational scope, such as department, business unit, or location.
- The application must deny unauthorized actions in both the user interface and backend API.
- Sensitive fields such as purchase price, residual value, personal assignment data, and disposal evidence must be individually restrictable.
- A user must not approve the user's own controlled request when separation of duties is enabled.

## 6. Core Concepts

### 6.1 Asset

An asset is a uniquely identifiable physical or logical item owned, leased, managed, or tracked by the organization.

Examples include:

- Laptop, desktop, monitor, mobile phone, printer, or network equipment
- Office furniture or appliances
- Machinery, tools, or laboratory equipment
- Vehicle-related equipment
- Software license or other logical asset, if enabled

### 6.2 Asset Tag

Every asset must have a unique, human-readable asset tag. The system may generate a tag automatically or accept an authorized manually supplied tag. The tag must remain unique even after the asset is retired.

### 6.3 Assignment

An assignment links an asset to a custodian, location, department, project, or other accountable destination for a defined period.

### 6.4 Lifecycle Event

A lifecycle event records a meaningful change such as registration, receipt, assignment, transfer, return, maintenance, verification, loss, retirement, or disposal.

### 6.5 Stocktake

A stocktake is a controlled physical inventory session used to compare expected assets with assets actually observed at one or more locations.

## 7. Asset Data Requirements

### 7.1 Required Fields at Asset Creation

The minimum required information must be configurable by asset category. The default required fields are:

- Asset tag
- Asset name or short description
- Asset category
- Lifecycle status
- Condition
- Owning department or business unit
- Current location
- Acquisition type, such as purchased, leased, rented, or donated
- Record created by and creation timestamp

### 7.2 Standard Asset Fields

The system must support the following asset attributes:

#### Identification

- Internal asset ID, generated by the system and immutable
- Asset tag, unique and human-readable
- Serial number
- Manufacturer
- Brand
- Model
- Asset name
- Description
- Category and subcategory
- Parent asset or asset bundle
- Barcode or QR-code value
- External system reference IDs

#### Ownership and Responsibility

- Legal owner
- Owning company or business unit
- Department
- Cost center
- Current custodian
- Responsible manager
- Project or program

#### Location

- Site
- Building
- Floor
- Room or area
- Storage location
- Free-text location notes

#### Lifecycle and Condition

- Lifecycle status
- Physical condition
- Operational state
- Date received
- Date placed in service
- Expected useful-life end date
- Retirement date
- Disposal date
- Disposal method
- Disposal reason

#### Purchase and Supplier Information

- Acquisition type
- Purchase or lease date
- Purchase price and currency
- Purchase-order reference
- Invoice reference
- Supplier
- Lease or rental contract reference
- Lease end date

#### Warranty and Service Information

- Warranty provider
- Warranty start date
- Warranty end date
- Service contract reference
- Service contract end date
- Last maintenance date
- Next maintenance due date
- Maintenance interval

#### Technical and Category-Specific Information

- Hostname or device name
- MAC address
- IP address
- Operating system
- Hardware specifications
- IMEI or mobile device identifier
- License identifier
- Vehicle or equipment identifier
- Configurable category-specific attributes

#### Data Governance

- Record status, active or archived
- Source system
- Created by and created timestamp
- Last modified by and modified timestamp
- Data-quality status
- Data owner
- Retention classification

### 7.3 Field Behavior

- Administrators must be able to configure category-specific fields without changing application source code.
- Configurable fields must support text, long text, number, decimal, currency, date, date-time, Boolean, single choice, multiple choice, and reference values.
- Required, optional, read-only, unique, and restricted field rules must be configurable where practical.
- Dates must be stored consistently and displayed using the user's configured locale and time zone.
- Monetary values must always include a currency.
- Inactive reference values must remain visible on historical records but must not be available for new selections.

## 8. Asset Status and Condition

### 8.1 Default Lifecycle Statuses

The default statuses are:

- Draft
- Ordered
- In Stock
- Available
- Reserved
- Assigned
- In Transit
- Under Maintenance
- Missing
- Lost
- Stolen
- Retired
- Disposed

Administrators may configure additional statuses, labels, and allowed transitions. Historical meanings must be preserved if a status is deactivated.

### 8.2 Default Conditions

The default conditions are:

- New
- Good
- Fair
- Damaged
- Unserviceable
- Unknown

### 8.3 Transition Rules

- Status transitions must follow configurable allowed paths.
- Invalid transitions must be rejected with a clear explanation.
- Controlled transitions may require a reason, evidence, and approval.
- Disposal must be terminal by default. Reopening a disposed asset must require elevated permission and a recorded justification.
- Every status and condition change must create an audit event.

## 9. Functional Requirements

### FR-001: Authentication

The application must authenticate users before granting access, except for explicitly approved public health-check endpoints.

**Acceptance criteria:**

- Unauthenticated users are redirected to or presented with a sign-in experience.
- Invalid credentials or tokens do not reveal whether a user account exists.
- Expired sessions are handled securely and lead the user back to sign-in.
- Successful sign-in records an auditable security event according to policy.

### FR-002: Authorization

The application must enforce role-based and scope-based authorization.

**Acceptance criteria:**

- Users see only pages, actions, assets, and fields they are authorized to access.
- Direct API requests cannot bypass interface restrictions.
- Unauthorized access returns an appropriate error without exposing restricted data.
- Permission changes take effect according to the configured session policy.

### FR-003: Asset Creation

Authorized users must be able to create an individual asset.

**Acceptance criteria:**

- Required fields are clearly identified and validated.
- The asset tag is generated or validated for uniqueness.
- Duplicate serial number or identifying-data warnings are shown before saving.
- A successful save creates the asset, initial lifecycle event, and audit record.
- A user can save a draft when not all operational fields are available, if permitted.

### FR-004: Asset Viewing and Editing

Authorized users must be able to view and update permitted asset information.

**Acceptance criteria:**

- The asset detail view presents current information, assignment, lifecycle, attachments, and history.
- Field-level permissions are enforced.
- Validation errors identify the affected field and how to correct it.
- Concurrent updates must not silently overwrite another user's changes.
- Every material update records who changed what and when.

### FR-005: Search, Filter, Sort, and Pagination

Users must be able to find assets efficiently.

**Acceptance criteria:**

- Global search supports asset tag, serial number, asset name, model, custodian, and location.
- The asset list supports filters for category, status, condition, department, location, custodian, supplier, warranty state, and important dates.
- Users can combine filters, sort results, clear filters, and paginate through results.
- Search results respect permissions.
- A user can open an asset directly from a unique exact tag or scan result.

### FR-006: Saved Views

Users must be able to save frequently used search and filter configurations.

**Acceptance criteria:**

- Users can name, update, use, and delete their own saved views.
- Authorized users can publish shared views.
- A user may select a default view.

### FR-007: Asset Assignment

Authorized users must be able to assign an available asset to a custodian or accountable destination.

**Acceptance criteria:**

- The system validates that the asset is assignable.
- The assignment captures custodian, location, department, assignment date, expected return date if applicable, and notes.
- The prior active assignment is closed correctly.
- The asset status and current responsibility are updated consistently.
- Receipt acknowledgement can be required and tracked.
- The action creates lifecycle and audit records.

### FR-008: Transfer

Authorized users must be able to transfer an asset between custodians, departments, or locations.

**Acceptance criteria:**

- A transfer records origin, destination, requester, reason, date, and optional evidence.
- Approval can be required based on configurable rules.
- Assets awaiting physical receipt can use the `In Transit` status.
- Completion requires confirmation by an authorized recipient when configured.
- Assignment and location history remain intact.

### FR-009: Return and Check-In

Authorized users must be able to return an assigned asset.

**Acceptance criteria:**

- Return captures date, received by, condition, destination location, and notes.
- Damage or missing accessories can be recorded.
- The active assignment is closed.
- The resulting status is selected according to business rules, such as Available, Under Maintenance, or Retired.

### FR-010: Reservation or Checkout

The application must support temporary reservation or checkout where enabled.

**Acceptance criteria:**

- A reservation includes requester, period, purpose, and status.
- Conflicting active reservations are prevented.
- Overdue checkouts are identifiable and reportable.
- Cancellation, checkout, return, and expiration are recorded.

### FR-011: Maintenance and Repair

Authorized users must be able to record maintenance and repair activity.

**Acceptance criteria:**

- A maintenance record includes type, issue, provider or technician, dates, cost and currency when permitted, result, and notes.
- Supporting documents can be attached.
- The asset can be placed under maintenance and restored to an allowed status when completed.
- The next maintenance due date can be calculated or entered.
- Maintenance history is visible from the asset record.

### FR-012: Warranty and Expiry Tracking

The system must track warranty and contract dates.

**Acceptance criteria:**

- Assets approaching expiry can be listed by configurable time windows.
- Expired warranty and contract states are visually identifiable.
- Notifications can be sent to configured recipients before expiry.
- Reports can be exported.

### FR-013: Lost, Stolen, Missing, and Damaged Assets

Authorized users must be able to report exceptions.

**Acceptance criteria:**

- Reports capture event type, date, reporter, last known location, description, and supporting evidence.
- Required approval and security workflows can be configured.
- The asset status and availability change appropriately.
- Resolution, recovery, or write-off is recorded without erasing the original event.

### FR-014: Retirement and Disposal

Authorized users must be able to retire and dispose of assets through a controlled process.

**Acceptance criteria:**

- Retirement captures reason, date, approver when required, and disposition plan.
- Disposal captures method, vendor or recipient, date, proceeds or cost when permitted, certificate reference, and evidence.
- Assigned assets cannot be disposed of until the assignment is resolved, unless an authorized exception is recorded.
- Disposed assets remain searchable to authorized users and cannot be reused accidentally.
- The complete history remains available for the configured retention period.

### FR-015: Attachments and Images

Authorized users must be able to upload and access supporting files.

**Acceptance criteria:**

- Supported file types and maximum sizes are configurable.
- Files may include receipts, warranty documents, photographs, service reports, transfer receipts, and disposal certificates.
- Files are scanned or validated according to the security design before becoming available.
- Unauthorized users cannot access an attachment through a direct URL.
- File upload, download, replacement, and removal are audited.

### FR-016: Notes and Comments

Authorized users must be able to add operational notes to an asset or workflow record.

**Acceptance criteria:**

- Notes show author and timestamp.
- Edited notes preserve an edit history or are replaced with a corrective note according to policy.
- Notes respect visibility permissions.

### FR-017: Barcode and QR-Code Support

The application must represent each asset tag as a printable barcode or QR code and support scanning where practical.

**Acceptance criteria:**

- A generated code resolves to the correct asset within the user's permissions.
- Users can print labels for one or multiple assets.
- A supported browser and camera can scan a code to open or select an asset.
- Manual entry remains available when scanning is unavailable.
- An unknown code produces a clear, non-destructive result.

### FR-018: Bulk Import

Authorized users must be able to import assets using CSV.

**Acceptance criteria:**

- A downloadable template documents required columns and accepted values.
- Import includes file validation, column mapping where needed, and a preview before commit.
- Invalid rows are rejected with row-level and field-level messages.
- Valid rows may be committed only when the user's chosen import policy permits partial success.
- Duplicate behavior is explicit: reject, update matched record, or create new record according to authorized settings.
- A result file summarizes created, updated, skipped, and failed rows.
- The import is auditable and repeatable without accidental duplication.

### FR-019: Export

Authorized users must be able to export permitted asset and report data.

**Acceptance criteria:**

- Exports respect active filters and permission rules.
- Sensitive fields are excluded when the user lacks field permission.
- CSV export is supported using a standard, documented encoding.
- Large exports run without blocking normal interactive use and provide completion status.
- Export activity is audited where required.

### FR-020: Dashboard

The application must provide a role-appropriate dashboard.

**Acceptance criteria:**

- Dashboard information respects the user's scope and permissions.
- Default indicators include total assets, assets by status, assets by category, assigned and unassigned assets, overdue returns, maintenance due, warranty expiring, missing assets, and recent activity.
- Indicators link to the supporting filtered records.
- The dashboard identifies when its data was last refreshed.

### FR-021: Reports

The application must provide operational and audit-ready reports.

Default reports include:

- Asset register
- Assets by category
- Assets by status and condition
- Assets by department, location, and custodian
- Unassigned assets
- Assignment and transfer history
- Overdue returns
- Maintenance due and maintenance history
- Warranty and contract expiry
- Missing, lost, stolen, and damaged assets
- Retired and disposed assets
- Stocktake variance
- Data-quality exceptions
- User activity and audit events, subject to permission

**Acceptance criteria:**

- Reports support relevant date ranges and filters.
- Report totals reconcile with the underlying permitted records.
- Users can open supporting records from interactive report results.
- Reports can be exported when authorized.

### FR-022: Stocktake Session

Authorized users must be able to create and execute a physical inventory session.

**Acceptance criteria:**

- A session defines scope, locations, assigned operators, start date, due date, freeze or snapshot time, and instructions.
- The expected asset list is captured at session start or through a documented snapshot rule.
- Operators can scan tags or manually select assets.
- Each observation records time, operator, location, observed condition, and optional note or image.
- The session identifies found, not found, unexpected, duplicate-scan, moved, and condition-mismatch outcomes.
- Reconciliation actions are reviewed before updates are applied to master data.
- Closing a session requires permission and creates a final variance report.

### FR-023: Notifications

The application must provide configurable in-application notifications and support email notifications when email integration is enabled.

Notification events should include:

- Assignment or transfer awaiting acknowledgement
- Approval request and approval outcome
- Checkout becoming overdue
- Maintenance approaching or overdue
- Warranty or contract approaching expiry
- Asset reported missing, lost, stolen, or damaged
- Stocktake assignment, due date, and unresolved variance
- Bulk import completion

**Acceptance criteria:**

- Users can view unread and historical in-application notifications.
- Duplicate notifications are minimized.
- Notification links lead to an authorized, relevant record.
- Delivery failures are logged without exposing confidential content.
- Users may configure optional notifications, while mandatory compliance notifications cannot be disabled without authorization.

### FR-024: Approvals

The application must support configurable approval steps for controlled actions.

**Acceptance criteria:**

- Approval can be enabled for transfers, disposal, write-off, sensitive updates, or other configured events.
- Requests show requester, reason, affected asset, relevant changes, and evidence.
- Approvers can approve, reject, or return a request with comments.
- The requester cannot approve the request when separation of duties is enabled.
- Approval history is immutable and auditable.

### FR-025: Audit History

The system must maintain a tamper-evident application audit history for security-sensitive and business-significant actions.

**Acceptance criteria:**

- Audit records capture actor, action, timestamp, target record, relevant before-and-after values, correlation ID, and outcome.
- Read access to sensitive audit information is restricted.
- Normal application users cannot edit or delete audit records.
- Audit data can be searched and exported by authorized users.
- Automated and integration actions identify their service identity.

### FR-026: Reference Data Administration

Administrators must be able to manage controlled reference data.

**Acceptance criteria:**

- Reference data includes categories, subcategories, statuses, conditions, locations, departments, cost centers, suppliers, disposal methods, maintenance types, and configurable attribute definitions.
- Values in active use cannot be deleted in a way that breaks historical records.
- Values can be activated, deactivated, ordered, and described.
- Changes are audited.

### FR-027: User Administration

Administrators must be able to manage application access when user provisioning is not fully controlled by an external identity provider.

**Acceptance criteria:**

- Administrators can view users, assign permitted roles and scopes, and activate or deactivate access.
- The system prevents removal of the final active system administrator.
- User changes are audited.
- Authentication secrets are never displayed to administrators.

### FR-028: Data Quality

The system must help users maintain complete and consistent records.

**Acceptance criteria:**

- The system identifies missing required data, invalid references, possible duplicates, expired assignments, and inconsistent lifecycle values.
- Data-quality rules can distinguish errors from warnings.
- Authorized users can view and resolve a data-quality work queue.
- Resolution does not erase the record's audit history.

### FR-029: Activity Feed

The asset detail view must provide a chronological activity feed.

**Acceptance criteria:**

- The feed combines permitted lifecycle events, assignments, transfers, maintenance, stocktake observations, comments, and status changes.
- Events show actor, timestamp, event type, and meaningful summary.
- Sensitive event details remain hidden from unauthorized roles.

### FR-030: Archiving and Retention

The system must support controlled archiving and retention.

**Acceptance criteria:**

- Records are not physically deleted through standard operational functions.
- Authorized users can archive eligible records without breaking references or history.
- Retention rules are configurable according to organizational policy.
- Legal or audit holds prevent applicable records from being purged.

## 10. Business Rules

### BR-001: Unique Identity

- The internal asset ID must never change.
- Asset tags must be unique across active, retired, disposed, and archived assets.
- Serial-number uniqueness may be configurable by category because some asset types may not have reliable serial numbers.

### BR-002: Single Active Assignment

An asset may have only one primary active assignment at a time unless the category explicitly supports shared or pooled custody.

### BR-003: Historical Integrity

Completed lifecycle events, approvals, stocktake observations, and audit records must not be overwritten. Corrections must be represented by authorized corrective transactions or superseding records.

### BR-004: Reference Integrity

Departments, locations, suppliers, users, and other referenced records that are already in use may be deactivated but must not be hard-deleted through normal administration.

### BR-005: Date Consistency

- Warranty end must not precede warranty start.
- Disposal date must not precede acquisition or receipt date.
- Assignment end must not precede assignment start.
- Maintenance completion must not precede maintenance start.
- Expected return dates in the past must require acknowledgement or produce an overdue state.

### BR-006: Disposal Control

An asset cannot be disposed of while it has an unresolved assignment, active reservation, open transfer, or incomplete maintenance record unless an authorized exception is approved and documented.

### BR-007: Financial Data

Purchase price, maintenance cost, disposal proceeds, and similar values must include currency and must be visible only to authorized roles.

### BR-008: Duplicate Detection

Potential duplicates should be identified using asset tag, serial number, manufacturer and model, external IDs, and configurable category-specific identifiers. Duplicate detection must warn users without merging records automatically.

### BR-009: Concurrency

When two users edit the same record, the later save must not silently replace changes based on an older version. The user must be prompted to review the conflict.

### BR-010: Time and Locale

The system must store timestamps consistently, preserve the event time zone where necessary, and display dates and times according to user or organizational settings.

## 11. User Journeys

### 11.1 Register and Assign a New Laptop

1. An Inventory Operator opens the new-asset form.
2. The operator selects the laptop category and enters identifying and purchase information.
3. The application checks required fields and warns about potential duplicates.
4. The application generates a unique asset tag and label.
5. The operator assigns the laptop to an employee, department, and location.
6. The employee receives an acknowledgement request when configured.
7. The dashboard and asset history reflect the new assignment.

### 11.2 Transfer an Asset to Another Office

1. An authorized user initiates a transfer from the asset record.
2. The user selects the destination location and custodian and enters a transfer reason.
3. Required approvals are completed.
4. The asset is marked In Transit.
5. The receiving user confirms receipt and condition.
6. The application closes the prior assignment and creates the new assignment and location history.

### 11.3 Perform a Stocktake

1. An Asset Manager creates a stocktake for selected locations.
2. Operators receive assigned count lists.
3. Operators scan tags and record observed location and condition.
4. The application identifies missing, unexpected, duplicated, moved, and condition-mismatch items.
5. The Asset Manager reviews and resolves variances.
6. The session is closed and a final report is retained.

### 11.4 Record Repair and Return to Service

1. A custodian reports a damaged asset.
2. A technician creates a maintenance record and changes the asset to Under Maintenance.
3. The technician records diagnosis, repair action, cost if authorized, and evidence.
4. When service is completed, the technician records the resulting condition and next maintenance date.
5. The asset returns to an allowed status and its history shows the complete maintenance activity.

### 11.5 Retire and Dispose of an Asset

1. An Asset Manager requests retirement and enters the reason and supporting evidence.
2. The application checks for active assignments and open work.
3. The designated approver approves or rejects the request.
4. After approval, the asset is retired.
5. An authorized user records disposal details and uploads the disposal certificate.
6. The asset becomes read-only for normal operations but remains available for audit and reporting.

## 12. Dashboard and Reporting Requirements

### 12.1 Dashboard Behavior

- Dashboard cards and charts must be derived from authorized records only.
- Selecting a card or chart segment must open the corresponding filtered asset list where practical.
- Empty states must explain why no data is shown and suggest an appropriate next action.
- The dashboard must not use misleading totals caused by hidden permission scopes.

### 12.2 Report Accuracy

- Reports must use documented definitions for each metric.
- Totals must reconcile with the underlying record set for the same filters and permissions.
- Generated reports must show the report name, filters, generation time, and requesting user where appropriate.
- Exported date, time, number, and currency formats must be documented.

## 13. Import and Integration Requirements

### 13.1 CSV Import and Export

- CSV is required for the initial release.
- Import and export encoding must support international characters.
- Imports must not execute formulas or scripts embedded in uploaded data.
- Exported spreadsheet-compatible content must mitigate formula-injection risks.

### 13.2 External Identity Provider

The application should support integration with an organizational identity provider using a standard protocol such as OpenID Connect or SAML when defined by the technical design. A local development authentication mode may be supplied for non-production use.

### 13.3 Employee and Organization Data

The design should allow employee, department, location, and cost-center records to be synchronized from an authoritative source. The initial release may use CSV import or administrator maintenance if a live integration is not available.

### 13.4 API Capability

The backend must expose documented APIs needed by the web application. The technical design should also make controlled future integration possible for procurement, finance, service-management, and discovery systems.

### 13.5 Integration Principles

- Integrations must use authenticated service identities.
- Requests must be idempotent where retries could otherwise create duplicates.
- Integration failures must be logged and recoverable.
- External IDs and source systems must be retained for traceability.
- API versioning and deprecation behavior must be documented.

## 14. Non-Functional Requirements

### NFR-001: Usability

- Common actions must be understandable without specialist training.
- Forms must group related information and provide clear validation and recovery guidance.
- Destructive or irreversible actions must require explicit confirmation.
- The system must use consistent terminology across pages, reports, notifications, and exports.
- Users must receive clear success, warning, error, loading, and empty-state feedback.

### NFR-002: Responsive Design

- The application must support current desktop, tablet, and mobile browser layouts.
- High-frequency mobile tasks, including search, scanning, stocktake, assignment, transfer, and condition updates, must be usable without horizontal page scrolling.
- Large data tables may use responsive alternatives while preserving essential actions and information.

### NFR-003: Accessibility

- The application should target WCAG 2.2 Level AA.
- All functionality must be operable by keyboard where applicable.
- Focus indicators, semantic labels, headings, error associations, and sufficient color contrast are required.
- Information must not be communicated by color alone.
- Dynamic changes and notifications must be exposed appropriately to assistive technology.

### NFR-004: Performance

Under normal supported load and excluding external-provider delays:

- The application should display the primary dashboard within 3 seconds for typical users.
- A normal filtered asset search should return within 2 seconds for typical data volumes.
- Opening a standard asset detail page should complete within 2 seconds.
- User actions must show visible feedback within 500 milliseconds when the final operation takes longer.
- Long-running imports, exports, and reports must run asynchronously with visible progress or status.

The detailed design must define the assumed data volume, concurrent users, test environment, and exact percentile-based performance targets.

### NFR-005: Availability and Reliability

- The production design should target at least 99.5 percent monthly availability, excluding approved maintenance windows.
- Failed transactions must not leave partially updated assignment, status, or stocktake data.
- Background jobs must be retryable without creating duplicate business events.
- Health checks and operational readiness checks must be available to authorized infrastructure.

### NFR-006: Scalability

The initial architecture must support at least the following planning baseline without redesign:

- 100,000 asset records
- 5,000 user records
- 250 concurrent authenticated users
- 1,000,000 lifecycle and audit events
- Bulk import files containing 25,000 asset rows

These values are planning assumptions and must be confirmed during detailed design and performance testing.

### NFR-007: Security

- All production communication must use encrypted transport.
- Password handling, when local passwords are enabled, must use established secure hashing and reset practices.
- Sessions and tokens must be protected against theft, replay, and inappropriate lifetime.
- Server-side validation is mandatory for all untrusted input.
- The application must mitigate common web risks including injection, cross-site scripting, cross-site request forgery where applicable, broken access control, insecure file upload, and unsafe redirects.
- Security-sensitive actions must be audited.
- Secrets must not be stored in source code, logs, browser storage, or exported reports.
- Error responses must not expose stack traces, credentials, internal paths, or confidential data.
- Dependency and container vulnerability scanning should be incorporated into delivery pipelines.

### NFR-008: Privacy

- Only information necessary for asset accountability should be processed.
- Employee information must be visible only to authorized users.
- Reports and exports must avoid unnecessary personal data.
- Retention, correction, access, and deletion handling must follow applicable organizational and legal requirements.
- Production data must not be copied into non-production environments without approved masking or anonymization.

### NFR-009: Auditability

- Important business and administrative actions must be traceable to an authenticated user or service identity.
- Audit timestamps must be reliable and consistently recorded.
- Audit records must be protected from ordinary modification and deletion.
- Correlation IDs must allow related frontend, backend, and background-job activity to be traced.

### NFR-010: Maintainability

- Business rules, status transitions, category attributes, and notification timing should be configurable where practical.
- The implementation must use modular components, documented interfaces, automated tests, and reproducible setup.
- Database changes must use version-controlled migrations.
- Operational configuration must be externalized from source code.

### NFR-011: Observability

- The system must produce structured application logs, metrics, and error information suitable for production support.
- Logs must include timestamps, severity, service or component name, and correlation IDs.
- Logs must not contain authentication secrets or unnecessarily expose personal or financial data.
- Critical failures and repeated background-job failures must be detectable through alerting integrations.

### NFR-012: Backup and Recovery

- Asset, configuration, attachment metadata, workflow, and audit data must be included in the backup strategy.
- The production design must document recovery time and recovery point objectives.
- As an initial target, recovery time should not exceed 8 hours and recoverable data loss should not exceed 24 hours, subject to business approval.
- Restore procedures must be tested periodically.

### NFR-013: Browser Support

The application must support the latest two stable major versions of Microsoft Edge, Google Chrome, Mozilla Firefox, and Safari at the time of release, subject to the organization's browser policy.

### NFR-014: Localization

- The first release must support English.
- User-visible text must be designed so additional languages can be added later.
- Date, time, number, and currency presentation must use configurable locale rules.
- Data storage must support Unicode.

## 15. Validation and Error Handling

- Validation must occur in both the user interface and backend.
- Error messages must explain what failed and what the user can do next.
- A single invalid field must not erase other valid form entries.
- Business-rule violations must use stable error codes suitable for testing and client handling.
- Unexpected errors must provide a support reference or correlation ID.
- Retryable and non-retryable failures must be distinguishable.
- Partial failure in bulk operations must produce a detailed result without misrepresenting failed rows as successful.

## 16. Data Migration Requirements

If legacy asset data exists:

1. The project must define a data-mapping document.
2. Source records must be profiled for completeness, duplicates, and invalid references.
3. Migration must include validation and reconciliation totals.
4. Trial migrations must occur before production cutover.
5. Rejected records must be reported with correctable reasons.
6. Migrated records must preserve source-system identifiers.
7. Migration scripts and results must be repeatable and auditable.

## 17. Test Expectations

Testing must include:

- Unit tests for business and validation rules
- API and service integration tests
- Database and migration tests
- Frontend component and interaction tests
- End-to-end tests for critical user journeys
- Role and permission tests, including direct API attempts
- Accessibility tests and keyboard checks
- Responsive layout checks
- Import and export tests with valid, invalid, duplicate, Unicode, and large files
- Attachment security tests
- Concurrency and conflict tests
- Audit-record completeness tests
- Stocktake reconciliation tests
- Performance tests against agreed data volumes
- Backup and restore verification in an appropriate environment
- Browser compatibility tests
- Security scanning and focused penetration testing before production release

No test may be marked as passed unless it was executed and evidence was captured.

## 18. Definition of Done

A feature is complete when:

- Its approved requirements and acceptance criteria are implemented.
- Authorization is enforced in the UI and backend.
- Validation, error handling, loading, success, and empty states are implemented.
- Required audit events are recorded.
- Automated tests are added and pass.
- Accessibility and responsive behavior are verified.
- Relevant documentation is updated.
- There are no unresolved critical or high-severity defects accepted without a documented risk decision.

The initial application release is complete when:

- All mandatory in-scope requirements are delivered or formally deferred.
- Critical user journeys pass end-to-end testing.
- Data migration or initial data loading is reconciled.
- Security, performance, backup, and recovery checks meet approved targets.
- Operational monitoring and support documentation are ready.
- Authorized business owners approve release acceptance.

## 19. Success Measures

The organization should measure:

- Percentage of active assets with complete required information
- Percentage of assets with a known custodian and location
- Duplicate asset rate
- Average time to register and assign an asset
- Overdue return count and duration
- Maintenance completed by due date
- Warranty-expiry actions completed on time
- Stocktake completion and variance rates
- Missing or unverified asset count
- Import error rate
- User adoption and task-completion success
- Number and age of unresolved data-quality issues

Exact baseline values and target improvements must be agreed with the business owner before production measurement begins.

## 20. Assumptions Requiring Confirmation

The following assumptions must be reviewed during detailed design:

1. The application is for internal organizational use.
2. English is the initial user-interface language.
3. An organizational identity provider is preferred for production authentication.
4. CSV is sufficient for initial bulk data exchange.
5. Barcode or QR scanning will use supported browser and device capabilities rather than dedicated hardware integration in the first release.
6. Financial depreciation and accounting postings are handled outside this application.
7. Asset data may include employee assignment information but should not store unnecessary personal information.
8. Approval workflows are configurable and may be disabled for simpler organizations.
9. The initial planning volume is 100,000 assets and 250 concurrent users.
10. The organization will define its final retention, recovery, notification, and data-classification policies.

## 21. Open Business Decisions

The product owner must decide or provide the following before final production design:

- Final organization and site structure
- Required identity provider and single sign-on rules
- Exact user roles, permission matrix, and organizational scopes
- Required approval workflows and approval thresholds
- Asset-tag format and label specification
- Categories and category-specific fields
- Supported currencies and financial-field visibility
- Required notification channels and timing
- Required reports and executive metrics
- Retention periods and legal-hold requirements
- Exact recovery time and recovery point objectives
- Final performance and availability service levels
- Whether software licenses or other logical assets are included
- Whether purchase, HR, finance, or service-management integrations are required in the first release
- Whether offline stocktake operation is required
- Whether attachments require malware scanning through an existing organizational service

## 22. Requirement Priority

Unless the product owner states otherwise:

- Authentication, authorization, asset registration, asset search, assignment, transfer, return, lifecycle status, audit history, responsive use, import/export, and core reporting are **Must Have**.
- Maintenance, stocktake, configurable approvals, notifications, label printing, and configurable category fields are **Should Have** for the initial release.
- Advanced external integrations, logical asset management, and offline operation are **Could Have** and may be scheduled after the initial release.
- Out-of-scope capabilities listed in Section 4.2 are **Not Planned** for the initial release.

## 23. Final Product Expectation

The finished web application must provide authorized users with a reliable, secure, and understandable way to manage assets from registration through disposal. It must prioritize accurate data, fast retrieval, strong accountability, transparent history, and efficient daily operation. The detailed design may refine implementation details, but it must not weaken the business controls, traceability, authorization, or acceptance criteria in this specification without an explicitly recorded product-owner decision.
