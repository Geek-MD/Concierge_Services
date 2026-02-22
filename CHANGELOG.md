# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2026-02-22

### Added
- **Service-Type Constants** (`const.py`): Added `SERVICE_TYPE_WATER`, `SERVICE_TYPE_GAS`,
  `SERVICE_TYPE_ELECTRICITY`, `SERVICE_TYPE_TELECOM`, and `SERVICE_TYPE_UNKNOWN` constants
  to classify detected services.

- **Modular Type-Specific Extractors** (`attribute_extractor.py`): Extraction tools are
  now organised by service type so each utility category can use patterns tuned to its
  own email format:

  | Service type  | Extra attributes extracted |
  |---|---|
  | `water`       | `consumption_m3`, `meter_reading`, `meter_number` |
  | `gas`         | `total_amount` (plain-number override), `metropuntos`, `consumption_m3` (label-based only) |
  | `electricity` | `consumption_kwh`, `contracted_power_kw` *(skeleton — patterns refined once email samples arrive)* |

  The water extractor is tuned for Aguas Andinas.
  The gas extractor is tuned for Metrogas (January 2026 reference email).
  The electricity extractor uses generic patterns as placeholders.

- **`due_date` extraction** (`attribute_extractor.py`): New generic extractor
  (`_extract_due_date`) searches for `Fecha de vencimiento` label, adding a
  `due_date` attribute to all service types.  Confirmed present in Metrogas emails.

- **`_extract_type_specific_attributes` routing helper** (`attribute_extractor.py`):
  Dispatches to the correct type-specific extractor based on `service_type`.

- **`classify_service_type` utility** (`service_detector.py`): Public function that
  infers the service type from the email `From` address and `Subject` line.  Used as
  a fallback for services whose metadata pre-dates this release.

### Changed
- **`_CUSTOMER_LABELS`** (`attribute_extractor.py`): Made `de` optional in
  `Número de Cliente` / `Número Cliente` so both forms are matched
  (Metrogas uses `Número Cliente:` without `de`).

- **`_extract_from_subject` folio patterns** (`attribute_extractor.py`): Added
  `r"nro\.?\s+([0-9]{6,})"` to capture Metrogas subject format
  `Boleta Metrogas Nro. 0000000061778648`.

- **`SERVICE_PATTERNS`** (`service_detector.py`): Each tuple now carries a third element —
  the service type — so the type is known at detection time rather than being inferred
  later.  Generic company patterns split by utility type for accurate classification.

- **`DetectedService` dataclass** (`service_detector.py`): Added `service_type` field.

- **`_extract_service_name`** (`service_detector.py`): Returns a 3-tuple
  `(service_name, service_id, service_type)` instead of a 2-tuple.

- **`extract_attributes_from_email_body`** (`attribute_extractor.py`): Accepts an
  optional `service_type` parameter (default `"unknown"`).  When provided, the
  appropriate type-specific extractor runs and its results are merged into the output.

- **`ConciergeServiceSensor.extra_state_attributes`** (`sensor.py`): Now exposes
  `service_type` as a state attribute so it is visible in the Home Assistant UI.

- **`ConciergeServicesCoordinator._find_latest_email_for_service`** (`sensor.py`):
  Reads `service_type` from stored metadata; falls back to `classify_service_type` for
  legacy entries that were configured before this release.

- **Config flow `async_step_detect_services`** (`config_flow.py`): Stores `service_type`
  in `services_metadata` alongside the existing name and sample headers.

### Gas extractor details (Metrogas reference email)
The Metrogas HTML-only email (`pagoenlinea@emailmetrogas.cl`) carries:
- Folio in subject as `Boleta Metrogas Nro. <number>` (no `$` sign on totals)
- `Número Cliente:` label (without `de`)
- `Dirección:` address
- `Período de consumo: dd/mm/yyyy al dd/mm/yyyy`
- `Total a pagar: <plain number>` — no `$` prefix
- `Fecha de vencimiento: dd/mm/yyyy`
- `Metropuntos: <number>` — loyalty points balance
- Gas consumption (m³) is **not** in the email body; it lives only in the PDF

## [0.3.2] - 2026-02-22

### Changed
- **Targeted Attribute Extraction**: Replaced broad heuristic email parsing with a
  focused extractor that produces exactly the fields needed before PDF analysis:

  | Attribute | Description |
  |---|---|
  | `service_name` | Utility company name (from sensor metadata) |
  | `folio` | Invoice/folio number (extracted from subject; confirmed later by PDF) |
  | `billing_period_start` | Start date of the billing period |
  | `billing_period_end` | End date of the billing period |
  | `total_amount` | Total amount due |
  | `customer_number` | Customer / account number |
  | `address` | Service address |
  | `last_updated_datetime` | Date the company sent the email (from `Date` header) |

- **HTML Body Handling**: Email body extractor now prefers `text/plain` parts;
  falls back to `text/html` only after stripping tags via stdlib `html.parser`.

### Removed
- Generic heuristic extractors (`_extract_key_value_pairs`, `_extract_currency_amounts`,
  `_extract_ids`, `FIELD_INDICATORS`, `KEY_VALUE_PATTERNS`, etc.) — replaced by
  targeted extractors (`_extract_total_amount`, `_extract_customer_number`, `_extract_address`).
- Redundant `empresa` attribute (covered by `service_name`).

### Fixed
- `mypy` errors: added `assert config_entry is not None` guards in
  `_fetch_service_data` and `ConciergeServicesConnectionSensor.extra_state_attributes`.

## [0.3.0] - 2026-02-21

### Added
- **Service Detection Flow**: Integration now automatically detects service accounts from inbox during setup
- **Service Selection**: Users can now select which detected services to configure as devices
- **MQTT-Style Architecture**: Following Home Assistant's MQTT integration pattern:
  - Email account acts as the "service" (hub)
  - Service accounts act as "devices" linked to the hub
- **Multi-Step Configuration**: Enhanced setup flow with service detection and selection
- **Service Metadata Storage**: Detected services are stored with metadata for future updates

### Changed
- **Configuration Flow**: Added two new steps after email setup:
  1. Service detection (automatic scan of inbox)
  2. Service selection (choose which services to configure)
- **Device Creation**: Devices are now created for all selected services during initial setup
- **Sensor Platform**: Updated to properly handle configured services from config entry

### Fixed
- **Service Detection Issue**: Previously detected services were not being converted into devices
- **Device Creation**: Service devices are now properly created during integration setup

## [0.2.0] - 2026-02-18

### Added
- **Device Architecture**: Each service is now represented as a separate device in Home Assistant
- **Friendly Name Configuration**: Users can set a custom friendly name for the integration
- **Area Assignment**: Integration can be associated with a specific area during setup
- **Automatic Service Detection**: Services are detected automatically from email inbox
- **Heuristic Attribute Extraction**: Automatically extracts billing attributes from email content
  - Account numbers, invoice numbers (folio)
  - Total amounts, due dates, billing periods
  - Consumption data, addresses, RUT
  - Company names from email subject
  - Any structured data in email body
- **Device-per-Service**: Each detected service appears as its own device with sensors
- **Status Sensor**: Renamed to "Concierge Services - Status" for consistency
- **Two-Step Configuration Flow**:
  1. IMAP credentials (server, port, email, password)
  2. Finalize (friendly name and area selection)

### Changed
- **Config Flow Simplified**: Service selection removed from initial setup
- **Device Names**: Uses friendly name instead of email address
- **Sensor Naming**: Connection sensor now called "Concierge Services - Status"
- **Device Info**: All sensors now include proper device_info for grouping
- **Architecture**: Prepared for automatic service discovery and notifications

### Technical
- Added `DeviceInfo` to all sensor entities
- Device hierarchy with `via_device` linking service devices to main device
- Area assignment using Home Assistant's area registry
- Services metadata stored in config entry for future use
- Heuristic pattern matching for attribute extraction (40+ field indicators)
- Multi-language support for attribute detection (Spanish and English)

## [0.1.5] - 2026-02-18

### Added
- Mail server connection status sensor that displays "OK" or "Problem"
- Sensor checks IMAP connection every 30 minutes and reports status
- Sensor includes email, server, and port as attributes
- Enhanced configuration form with helpful placeholder text and examples
- Added data_description fields in strings.json and translations for better UX
- Suggested values for IMAP server (e.g., "imap.gmail.com") and email (e.g., "user@gmail.com")

## [0.1.0] - 2026-02-18

### Added
- Initial release of Concierge Services integration
- IMAP email account configuration through Home Assistant UI
- Real-time IMAP credential validation
- Secure credential storage using Home Assistant's storage system
- Multi-language support (English and Spanish)
- HACS compatibility for easy installation
- Configuration flow with user-friendly interface
- Support for major email providers (Gmail, Outlook, Yahoo)
- Basic integration structure and manifest


### Documentation
- Created comprehensive README with installation and configuration instructions
- Created CHANGELOG.md to track project changes
- Added MIT License
- Created HACS configuration file
- Added Spanish translations for the integration UI

### Technical Details
- Integration domain: `concierge_services`
- Configuration flow implementation using Home Assistant's config_flow
- Supports IMAP SSL/TLS connection on port 993
- IoT class: cloud_polling
