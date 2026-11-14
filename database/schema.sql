-- Reference for the OneGov PH application records.
-- database/init_db.py does not run this file.
-- These statements use CREATE TABLE IF NOT EXISTS and do not remove existing rows.
-- Payment status lives on payments. Cancellation reason lives on applications.
-- for_biometrics and with_hit are OneGov PH monitoring labels. They are not a live NBI connection.

CREATE TABLE IF NOT EXISTS `applications` (
  `application_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `tracking_number` varchar(30) NOT NULL,
  `applicant_id` int(10) unsigned NOT NULL,
  `service_id` int(10) unsigned NOT NULL,
  `application_status` enum('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') NOT NULL DEFAULT 'submitted',
  `submission_date` datetime NOT NULL DEFAULT current_timestamp(),
  `last_updated` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `assigned_department_id` int(10) unsigned NOT NULL,
  `application_details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`application_details`)),
  `cancellation_reason` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`application_id`),
  UNIQUE KEY `uq_applications_tracking_number` (`tracking_number`),
  KEY `idx_applications_applicant` (`applicant_id`),
  KEY `idx_applications_service` (`service_id`),
  KEY `idx_applications_department` (`assigned_department_id`),
  KEY `idx_applications_status` (`application_status`),
  KEY `idx_applications_submission_date` (`submission_date`),
  KEY `fk_applications_service_department` (`service_id`,`assigned_department_id`),
  CONSTRAINT `fk_applications_applicant` FOREIGN KEY (`applicant_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_department` FOREIGN KEY (`assigned_department_id`) REFERENCES `departments` (`department_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_service` FOREIGN KEY (`service_id`) REFERENCES `services` (`service_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_applications_service_department` FOREIGN KEY (`service_id`, `assigned_department_id`) REFERENCES `services` (`service_id`, `department_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `application_requirements` (
  `requirement_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `application_id` int(10) unsigned NOT NULL,
  `requirement_name` varchar(200) NOT NULL,
  `uploaded_file` varchar(255) DEFAULT NULL COMMENT 'Stored file path only. File contents stay outside the database.',
  `verification_status` enum('pending','verified','rejected') NOT NULL DEFAULT 'pending',
  `remarks` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`requirement_id`),
  KEY `idx_application_requirements_application` (`application_id`),
  KEY `idx_application_requirements_status` (`verification_status`),
  CONSTRAINT `fk_application_requirements_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `application_tracking` (
  `tracking_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `application_id` int(10) unsigned NOT NULL,
  `previous_status` enum('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') DEFAULT NULL,
  `new_status` enum('draft','submitted','under_review','pending_documents','for_payment','paid','scheduled','processing','ready_for_release','completed','rejected','cancelled','approved','for_biometrics','with_hit') NOT NULL,
  `update_description` varchar(500) NOT NULL,
  `updated_by` int(10) unsigned DEFAULT NULL,
  `recorded_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`tracking_id`),
  KEY `idx_application_tracking_application` (`application_id`),
  KEY `idx_application_tracking_recorded_at` (`recorded_at`),
  KEY `idx_application_tracking_updated_by` (`updated_by`),
  CONSTRAINT `fk_application_tracking_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_application_tracking_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `payments` (
  `payment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `application_id` int(10) unsigned NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `payment_reference` varchar(64) NOT NULL COMMENT 'Merchant request reference. Do not store card numbers or CVV.',
  `payment_method` enum('gcash','maya','bank_transfer','over_the_counter','online_banking') NOT NULL,
  `payment_status` enum('pending','paid','failed','refunded','cancelled') NOT NULL DEFAULT 'pending',
  `transaction_date` datetime DEFAULT NULL,
  `provider_checkout_id` varchar(64) DEFAULT NULL COMMENT 'Maya checkoutId. Nullable for non-gateway payments.',
  `provider_status` varchar(40) DEFAULT NULL COMMENT 'Latest Maya paymentStatus string.',
  PRIMARY KEY (`payment_id`),
  UNIQUE KEY `uq_payments_reference` (`payment_reference`),
  UNIQUE KEY `uq_payments_provider_checkout` (`provider_checkout_id`),
  KEY `idx_payments_application` (`application_id`),
  KEY `idx_payments_status` (`payment_status`),
  CONSTRAINT `fk_payments_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE,
  CONSTRAINT `chk_payments_amount` CHECK (`amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `passport_appointments` (
  `appointment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `application_id` int(10) unsigned NOT NULL,
  `location_code` varchar(40) NOT NULL,
  `location_label` varchar(200) NOT NULL,
  `appointment_date` date NOT NULL,
  `appointment_time` varchar(5) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`appointment_id`),
  UNIQUE KEY `uq_passport_appointments_application` (`application_id`),
  UNIQUE KEY `uq_passport_appointments_slot` (`location_code`,`appointment_date`,`appointment_time`),
  KEY `idx_passport_appointments_date` (`appointment_date`),
  CONSTRAINT `fk_passport_appointments_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `nbi_appointments` (
  `appointment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `application_id` int(10) unsigned NOT NULL,
  `location_code` varchar(40) NOT NULL,
  `location_label` varchar(200) NOT NULL,
  `appointment_date` date NOT NULL,
  `appointment_time` varchar(5) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`appointment_id`),
  UNIQUE KEY `uq_nbi_appointments_application` (`application_id`),
  UNIQUE KEY `uq_nbi_appointments_slot` (`location_code`,`appointment_date`,`appointment_time`),
  KEY `idx_nbi_appointments_date` (`appointment_date`),
  CONSTRAINT `fk_nbi_appointments_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `notifications` (
  `notification_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL,
  `notification_title` varchar(200) NOT NULL,
  `notification_message` text NOT NULL,
  `notification_type` enum('application','payment','appointment','account','system') NOT NULL DEFAULT 'system',
  `read_status` enum('unread','read') NOT NULL DEFAULT 'unread',
  `created_date` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`notification_id`),
  KEY `idx_notifications_user` (`user_id`),
  KEY `idx_notifications_read_status` (`read_status`),
  KEY `idx_notifications_created_date` (`created_date`),
  CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
