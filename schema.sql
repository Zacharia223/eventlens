-- EventLens database schema.
-- Applied automatically by db.init_db() at startup; kept here for reference
-- and for manual setup (e.g. `mysql -u root -p < schema.sql`).

CREATE DATABASE IF NOT EXISTS eventlens
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE eventlens;

CREATE TABLE IF NOT EXISTS reports (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    filename     VARCHAR(255) NOT NULL,
    uploaded_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_count    INT NOT NULL,
    column_count INT NOT NULL,
    report_json  LONGTEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
