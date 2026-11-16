-- Apply once to an existing OneGov PH database before using Admin > Accounts.
-- Adds administrator-managed department/permission assignments and account audit history.
ALTER TABLE `users`
  ADD COLUMN `department_id` int(10) unsigned DEFAULT NULL,
  ADD COLUMN `admin_permissions` JSON DEFAULT NULL,
  ADD CONSTRAINT `fk_users_department`
    FOREIGN KEY (`department_id`) REFERENCES `departments` (`department_id`)
    ON UPDATE CASCADE;

CREATE TABLE IF NOT EXISTS `account_activity_logs` (
  `activity_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `target_user_id` int(10) unsigned NOT NULL,
  `actor_user_id` int(10) unsigned NOT NULL,
  `action` varchar(80) NOT NULL,
  `description` varchar(500) NOT NULL,
  `recorded_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`activity_id`),
  KEY `idx_account_activity_target` (`target_user_id`),
  KEY `idx_account_activity_actor` (`actor_user_id`),
  KEY `idx_account_activity_recorded_at` (`recorded_at`),
  CONSTRAINT `fk_account_activity_target`
    FOREIGN KEY (`target_user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_account_activity_actor`
    FOREIGN KEY (`actor_user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
