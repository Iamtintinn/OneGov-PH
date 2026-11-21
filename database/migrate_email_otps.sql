-- Email OTP verification storage for registration and login.
-- Run once on an existing OneGov PH database. Does not delete existing records.

CREATE TABLE IF NOT EXISTS `email_otps` (
  `otp_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `purpose` enum('login','register') NOT NULL,
  `user_id` int(10) unsigned DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `code_hash` varchar(255) NOT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payload`)),
  `attempts` int(11) NOT NULL DEFAULT 0,
  `max_attempts` int(11) NOT NULL DEFAULT 5,
  `expires_at` datetime NOT NULL,
  `last_sent_at` datetime NOT NULL,
  `resend_available_at` datetime NOT NULL,
  `consumed_at` datetime DEFAULT NULL,
  `invalidated_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`otp_id`),
  KEY `idx_email_otps_purpose` (`purpose`),
  KEY `idx_email_otps_email` (`email`),
  KEY `idx_email_otps_user_id` (`user_id`),
  KEY `idx_email_otps_expires_at` (`expires_at`),
  KEY `idx_email_otps_active_lookup` (`purpose`,`email`,`consumed_at`,`invalidated_at`),
  CONSTRAINT `fk_email_otps_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
