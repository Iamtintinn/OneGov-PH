-- Additive Maya Checkout fields for passport payments.
-- Run once against onegov_ph (XAMPP MySQL / MariaDB).

ALTER TABLE `payments`
  ADD COLUMN `provider_checkout_id` varchar(64) DEFAULT NULL COMMENT 'Maya checkoutId';

ALTER TABLE `payments`
  ADD COLUMN `provider_status` varchar(40) DEFAULT NULL COMMENT 'Latest Maya paymentStatus';

ALTER TABLE `payments`
  ADD UNIQUE KEY `uq_payments_provider_checkout` (`provider_checkout_id`);
