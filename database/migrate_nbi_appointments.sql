-- Demonstration NBI appointment slots for OneGov PH monitoring requests.
CREATE TABLE IF NOT EXISTS `nbi_appointments` (
  `appointment_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `application_id` INT UNSIGNED NOT NULL,
  `location_code` VARCHAR(40) NOT NULL,
  `location_label` VARCHAR(200) NOT NULL,
  `appointment_date` DATE NOT NULL,
  `appointment_time` VARCHAR(5) NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`appointment_id`),
  UNIQUE KEY `uq_nbi_appointments_application` (`application_id`),
  UNIQUE KEY `uq_nbi_appointments_slot` (`location_code`,`appointment_date`,`appointment_time`),
  KEY `idx_nbi_appointments_date` (`appointment_date`),
  CONSTRAINT `fk_nbi_appointments_application` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
