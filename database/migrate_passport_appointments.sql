-- Additive migration for passport demonstration appointments.
-- Safe to run on an existing OneGov PH database. Does not delete rows.

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
