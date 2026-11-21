-- Add OTP login preference for user accounts.
-- Run once on an existing OneGov PH database.

ALTER TABLE `users`
  ADD COLUMN `otp_login_enabled` TINYINT(1) NOT NULL DEFAULT 1;
