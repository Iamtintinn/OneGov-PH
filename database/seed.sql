-- OneGov PH reference data only.
--
-- Safe to run more than once: INSERT IGNORE relies on the unique keys
--   departments.uq_departments_name
--   services.uq_services_department_name
-- and never updates or deletes existing rows.
--
-- This file intentionally seeds NO citizen accounts, staff accounts, payments,
-- applications, appointments, or notifications.
--
-- Scope is the eight OneGov PH services. Passport and Pag-IBIG are not seeded.

INSERT IGNORE INTO `departments`
  (`department_name`, `department_description`, `department_status`)
VALUES
  ('PSA', 'Philippine Statistics Authority', 'active'),
  ('PhilSys', 'Philippine Identification System', 'active'),
  ('NBI', 'National Bureau of Investigation', 'active'),
  ('LGU', 'Local Government Unit', 'active'),
  ('SSS', 'Social Security System', 'active');

-- PSA
INSERT IGNORE INTO `services`
  (`department_id`, `service_name`, `description`, `processing_fee`,
   `estimated_processing_time`, `service_requirements`, `service_status`)
VALUES
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'PSA'),
    'Birth Certificate',
    'Request and track a PSA birth certificate.',
    155.00,
    '3-7 business days',
    'Valid government ID of the requester, complete name of the document owner, date and place of birth, and complete names of the parents.',
    'active'
  ),
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'PSA'),
    'CENOMAR',
    'Request and track a PSA Certificate of No Marriage.',
    210.00,
    '3-7 business days',
    'Valid government ID, complete name, and date and place of birth.',
    'active'
  );

-- PhilSys (National ID registration is handled by PSA personnel)
INSERT IGNORE INTO `services`
  (`department_id`, `service_name`, `description`, `processing_fee`,
   `estimated_processing_time`, `service_requirements`, `service_status`)
VALUES
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'PhilSys'),
    'PhilSys National ID Registration Assistance',
    'Prepare your National ID registration requirements, submit your preliminary information, receive registration instructions, and monitor your registration progress through OneGov PH.',
    0.00,
    'Completed at an authorized PSA registration center',
    'Bring an original primary supporting document, or one secondary document if you have no primary document. PSA publishes the accepted list. Registration is free, and biometrics are taken only at an authorized PSA center.',
    'active'
  );

-- NBI
INSERT IGNORE INTO `services`
  (`department_id`, `service_name`, `description`, `processing_fee`,
   `estimated_processing_time`, `service_requirements`, `service_status`)
VALUES
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'NBI'),
    'NBI Clearance Application Monitoring',
    'Monitor the status of an NBI clearance application.',
    130.00,
    'Same day when there is no record hit',
    'Clearance or appointment reference, full name, and date of birth.',
    'active'
  );

-- LGU
INSERT IGNORE INTO `services`
  (`department_id`, `service_name`, `description`, `processing_fee`,
   `estimated_processing_time`, `service_requirements`, `service_status`)
VALUES
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'LGU'),
    'Barangay Clearance',
    'Request and track a barangay clearance.',
    50.00,
    '1 business day',
    'Valid ID and proof of residency in the barangay. The local fee may differ by LGU.',
    'active'
  ),
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'LGU'),
    'Certificate of Residency',
    'Request and track a certificate of residency.',
    50.00,
    '1 business day',
    'Valid ID and current address. The local fee may differ by LGU.',
    'active'
  ),
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'LGU'),
    'Senior Citizen ID',
    'Request and track a senior citizen identification card.',
    0.00,
    '3-7 business days',
    'Proof of age and a valid ID. Issuance follows the LGU Office of Senior Citizens Affairs.',
    'active'
  );

-- SSS
INSERT IGNORE INTO `services`
  (`department_id`, `service_name`, `description`, `processing_fee`,
   `estimated_processing_time`, `service_requirements`, `service_status`)
VALUES
  (
    (SELECT `department_id` FROM `departments` WHERE `department_name` = 'SSS'),
    'SS Number Registration Assistance and Tracking',
    'The Social Security System (SSS) issues a unique lifetime Social Security Number to individuals registering for SSS for the first time. OneGov PH helps citizens understand the registration requirements, organize their information, and monitor their registration progress.',
    0.00,
    '5-10 business days',
    'SSS transaction reference and the full name of the applicant.',
    'active'
  );
