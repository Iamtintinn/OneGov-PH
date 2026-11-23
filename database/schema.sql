-- OneGov PH database schema (MySQL / MariaDB / TiDB Cloud compatible).
--
-- Run this on a fresh database when you prefer SQL over `python database/migrate.py`.
-- Every statement uses CREATE TABLE IF NOT EXISTS and never drops data.
-- `python database/migrate.py` is the recommended path because it builds the
-- same tables from the SQLAlchemy models (single source of truth).
--
-- Reference data lives in database/seed.sql. The eight in-scope services are:
--   PSA Birth Certificate, PSA CENOMAR, PhilSys National ID, NBI Clearance,
--   SSS SS Number Registration, LGU Barangay Clearance,
--   LGU Certificate of Residency, LGU Senior Citizen ID.
--
-- Notes:
--   * JSON columns use TiDB/MySQL JSON (no longtext + json_valid CHECK needed).
--   * Legacy local-only tables `appointments` and `barangay_deliveries` are not
--     created here because no Python code reads or writes them.
--   * application_status values are OneGov PH monitoring labels. `for_biometrics`
--     and `with_hit` are not a live NBI/DFA connection.

-- ---------------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `departments` (
  `department_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `department_name` VARCHAR(150) NOT NULL,
  `department_description` TEXT DEFAULT NULL,
  `department_status` ENUM('active','inactive') NOT NULL DEFAULT 'active',
  PRIMARY KEY (`department_id`),
  UNIQUE KEY `uq_departments_name` (`department_name`),
  KEY `idx_departments_status` (`department_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `services` (
  `service_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `department_id` INT UNSIGNED NOT NULL,
  `service_name` VARCHAR(200) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `processing_fee` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `estimated_processing_time` VARCHAR(100) DEFAULT NULL,
  `service_requirements` TEXT DEFAULT NULL,
  `service_status` ENUM('active','inactive') NOT NULL DEFAULT 'active',
  PRIMARY KEY (`service_id`),
  UNIQUE KEY `uq_services_department_name` (`department_id`,`service_name`),
  UNIQUE KEY `uq_services_department_pair` (`service_id`,`department_id`),
  CONSTRAINT `fk_services_department` FOREIGN KEY (`department_id`)
    REFERENCES `departments` (`department_id`) ON UPDATE CASCADE,
  CONSTRAINT `chk_services_processing_fee` CHECK (`processing_fee` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Accounts
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `first_name` VARCHAR(80) NOT NULL,
  `middle_name` VARCHAR(80) DEFAULT NULL,
  `last_name` VARCHAR(80) NOT NULL,
  `full_name` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'Password hash only. Never store a plaintext password.',
  `contact_number` VARCHAR(20) DEFAULT NULL,
  `address` VARCHAR(500) DEFAULT NULL COMMENT 'Applicant address. Do not copy this into logs.',
  `account_status` ENUM('active','inactive','suspended') NOT NULL DEFAULT 'active',
  `role` ENUM('citizen','department_staff','department_supervisor','system_admin') NOT NULL DEFAULT 'citizen',
  `email_verification_status` ENUM('unverified','verified') NOT NULL DEFAULT 'unverified',
  `otp_login_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `department_id` INT UNSIGNED DEFAULT NULL,
  `admin_permissions` JSON DEFAULT NULL,
  `date_registered` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_email` (`email`),
  KEY `idx_users_account_status` (`account_status`),
  KEY `idx_users_role` (`role`),
  KEY `fk_users_department` (`department_id`),
  CONSTRAINT `fk_users_department` FOREIGN KEY (`department_id`)
    REFERENCES `departments` (`department_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `account_activity_logs` (
  `activity_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `target_user_id` INT UNSIGNED NOT NULL,
  `actor_user_id` INT UNSIGNED NOT NULL,
  `action` VARCHAR(80) NOT NULL,
  `description` VARCHAR(500) NOT NULL,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`activity_id`),
  KEY `idx_account_activity_target` (`target_user_id`),
  KEY `idx_account_activity_actor` (`actor_user_id`),
  KEY `idx_account_activity_recorded_at` (`recorded_at`),
  CONSTRAINT `fk_account_activity_target` FOREIGN KEY (`target_user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_account_activity_actor` FOREIGN KEY (`actor_user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `email_otps` (
  `otp_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `purpose` ENUM('login','register') NOT NULL,
  `user_id` INT UNSIGNED DEFAULT NULL,
  `email` VARCHAR(255) NOT NULL,
  `code_hash` VARCHAR(255) NOT NULL,
  `payload` JSON DEFAULT NULL,
  `attempts` INT NOT NULL DEFAULT 0,
  `max_attempts` INT NOT NULL DEFAULT 5,
  `expires_at` DATETIME NOT NULL,
  `last_sent_at` DATETIME NOT NULL,
  `resend_available_at` DATETIME NOT NULL,
  `consumed_at` DATETIME DEFAULT NULL,
  `invalidated_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`otp_id`),
  KEY `idx_email_otps_purpose` (`purpose`),
  KEY `idx_email_otps_email` (`email`),
  KEY `idx_email_otps_user_id` (`user_id`),
  KEY `idx_email_otps_expires_at` (`expires_at`),
  KEY `idx_email_otps_active_lookup` (`purpose`,`email`,`consumed_at`,`invalidated_at`),
  CONSTRAINT `fk_email_otps_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `session_token` VARCHAR(128) NOT NULL,
  `ip_address` VARCHAR(64) DEFAULT NULL,
  `user_agent` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `revoked_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_sessions_token` (`session_token`),
  KEY `idx_user_sessions_user` (`user_id`),
  KEY `idx_user_sessions_revoked` (`revoked_at`),
  CONSTRAINT `fk_user_sessions_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `account_requests` (
  `request_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `request_type` ENUM('deactivation','deletion') NOT NULL,
  `reason` VARCHAR(500) DEFAULT NULL,
  `status` ENUM('pending','reviewed','approved','rejected','cancelled') NOT NULL DEFAULT 'pending',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`request_id`),
  KEY `idx_account_requests_user` (`user_id`),
  KEY `idx_account_requests_status` (`status`),
  CONSTRAINT `fk_account_requests_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Applications
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `applications` (
  `application_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tracking_number` VARCHAR(30) NOT NULL,
  `applicant_id` INT UNSIGNED NOT NULL,
  `service_id` INT UNSIGNED NOT NULL,
  `application_status` ENUM('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') NOT NULL DEFAULT 'submitted',
  `submission_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_updated` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `assigned_department_id` INT UNSIGNED NOT NULL,
  `application_details` JSON DEFAULT NULL,
  `cancellation_reason` VARCHAR(500) DEFAULT NULL,
  PRIMARY KEY (`application_id`),
  UNIQUE KEY `uq_applications_tracking_number` (`tracking_number`),
  KEY `idx_applications_applicant` (`applicant_id`),
  KEY `idx_applications_service` (`service_id`),
  KEY `idx_applications_department` (`assigned_department_id`),
  KEY `idx_applications_status` (`application_status`),
  KEY `idx_applications_submission_date` (`submission_date`),
  KEY `idx_applications_service_department` (`service_id`,`assigned_department_id`),
  CONSTRAINT `fk_applications_applicant` FOREIGN KEY (`applicant_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_department` FOREIGN KEY (`assigned_department_id`)
    REFERENCES `departments` (`department_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_service` FOREIGN KEY (`service_id`)
    REFERENCES `services` (`service_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_service_department` FOREIGN KEY (`service_id`,`assigned_department_id`)
    REFERENCES `services` (`service_id`,`department_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `application_requirements` (
  `requirement_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `requirement_name` VARCHAR(200) NOT NULL,
  `uploaded_file` VARCHAR(255) DEFAULT NULL COMMENT 'Stored file path only. File contents stay outside the database.',
  `verification_status` ENUM('pending','verified','rejected') NOT NULL DEFAULT 'pending',
  `remarks` VARCHAR(500) DEFAULT NULL,
  PRIMARY KEY (`requirement_id`),
  KEY `idx_application_requirements_application` (`application_id`),
  KEY `idx_application_requirements_status` (`verification_status`),
  CONSTRAINT `fk_application_requirements_application` FOREIGN KEY (`application_id`)
    REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `application_tracking` (
  `tracking_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `previous_status` ENUM('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') DEFAULT NULL,
  `new_status` ENUM('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') NOT NULL,
  `update_description` VARCHAR(500) NOT NULL,
  `updated_by` INT UNSIGNED DEFAULT NULL,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`tracking_id`),
  KEY `idx_application_tracking_application` (`application_id`),
  KEY `idx_application_tracking_recorded_at` (`recorded_at`),
  KEY `idx_application_tracking_updated_by` (`updated_by`),
  CONSTRAINT `fk_application_tracking_application` FOREIGN KEY (`application_id`)
    REFERENCES `applications` (`application_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_application_tracking_updated_by` FOREIGN KEY (`updated_by`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `payments` (
  `payment_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `payment_reference` VARCHAR(64) NOT NULL COMMENT 'Merchant/provider reference. Do not store card numbers or CVV.',
  `payment_method` ENUM('gcash','maya','bank_transfer','over_the_counter','online_banking') NOT NULL,
  `payment_status` ENUM('pending','paid','failed','refunded','cancelled') NOT NULL DEFAULT 'pending',
  `transaction_date` DATETIME DEFAULT NULL,
  `provider_checkout_id` VARCHAR(64) DEFAULT NULL COMMENT 'Maya checkoutId. Nullable for non-gateway payments.',
  `provider_status` VARCHAR(40) DEFAULT NULL COMMENT 'Latest Maya paymentStatus string.',
  PRIMARY KEY (`payment_id`),
  UNIQUE KEY `uq_payments_reference` (`payment_reference`),
  UNIQUE KEY `uq_payments_provider_checkout` (`provider_checkout_id`),
  KEY `idx_payments_application` (`application_id`),
  KEY `idx_payments_status` (`payment_status`),
  CONSTRAINT `fk_payments_application` FOREIGN KEY (`application_id`)
    REFERENCES `applications` (`application_id`) ON UPDATE CASCADE,
  CONSTRAINT `chk_payments_amount` CHECK (`amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `passport_appointments` (
  `appointment_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `location_code` VARCHAR(40) NOT NULL,
  `location_label` VARCHAR(200) NOT NULL,
  `appointment_date` DATE NOT NULL,
  `appointment_time` VARCHAR(5) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`appointment_id`),
  UNIQUE KEY `uq_passport_appointments_application` (`application_id`),
  UNIQUE KEY `uq_passport_appointments_slot` (`location_code`,`appointment_date`,`appointment_time`),
  KEY `idx_passport_appointments_date` (`appointment_date`),
  CONSTRAINT `fk_passport_appointments_application` FOREIGN KEY (`application_id`)
    REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `nbi_appointments` (
  `appointment_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `location_code` VARCHAR(40) NOT NULL,
  `location_label` VARCHAR(200) NOT NULL,
  `appointment_date` DATE NOT NULL,
  `appointment_time` VARCHAR(5) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`appointment_id`),
  UNIQUE KEY `uq_nbi_appointments_application` (`application_id`),
  UNIQUE KEY `uq_nbi_appointments_slot` (`location_code`,`appointment_date`,`appointment_time`),
  KEY `idx_nbi_appointments_date` (`appointment_date`),
  CONSTRAINT `fk_nbi_appointments_application` FOREIGN KEY (`application_id`)
    REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Notifications and audit trail
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `notifications` (
  `notification_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `notification_title` VARCHAR(200) NOT NULL,
  `notification_message` TEXT NOT NULL,
  `notification_type` ENUM('application','payment','appointment','account','system') NOT NULL DEFAULT 'system',
  `read_status` ENUM('unread','read') NOT NULL DEFAULT 'unread',
  `created_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  KEY `idx_notifications_user` (`user_id`),
  KEY `idx_notifications_read_status` (`read_status`),
  KEY `idx_notifications_created_date` (`created_date`),
  CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `activity_id` VARCHAR(40) NOT NULL,
  `user_id` INT UNSIGNED DEFAULT NULL,
  `department_id` INT UNSIGNED DEFAULT NULL,
  `user_name_snapshot` VARCHAR(200) NOT NULL DEFAULT '',
  `user_role` VARCHAR(60) NOT NULL DEFAULT '',
  `activity_type` VARCHAR(120) NOT NULL,
  `module` VARCHAR(80) NOT NULL,
  `description` VARCHAR(600) NOT NULL,
  `record_id` VARCHAR(120) DEFAULT NULL,
  `previous_value` JSON DEFAULT NULL,
  `new_value` JSON DEFAULT NULL,
  `ip_address` VARCHAR(64) DEFAULT NULL,
  `user_agent` VARCHAR(500) DEFAULT NULL,
  `activity_status` VARCHAR(20) NOT NULL DEFAULT 'Success',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_audit_logs_activity_id` (`activity_id`),
  KEY `ix_audit_logs_user_id` (`user_id`),
  KEY `ix_audit_logs_department_id` (`department_id`),
  KEY `ix_audit_logs_user_role` (`user_role`),
  KEY `ix_audit_logs_activity_type` (`activity_type`),
  KEY `ix_audit_logs_module` (`module`),
  KEY `ix_audit_logs_record_id` (`record_id`),
  KEY `ix_audit_logs_ip_address` (`ip_address`),
  KEY `ix_audit_logs_activity_status` (`activity_status`),
  KEY `ix_audit_logs_created_at` (`created_at`),
  CONSTRAINT `fk_audit_logs_user_id` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_audit_logs_department_id` FOREIGN KEY (`department_id`)
    REFERENCES `departments` (`department_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
