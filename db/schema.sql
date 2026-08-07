DROP DATABASE IF EXISTS sales_management_system;
CREATE DATABASE sales_management_system;
USE sales_management_system;

CREATE TABLE branches (
    branch_id INT AUTO_INCREMENT PRIMARY KEY,
    branch_name VARCHAR(100),
    branch_admin_name VARCHAR(100)
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(100),
    branch_id INT NULL,
    role ENUM('Super Admin','Admin'),
    email VARCHAR(255) UNIQUE,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE customer_sales (
    sale_id INT PRIMARY KEY,
    branch_id INT,
    date DATE,
    name VARCHAR(100),
    mobile_number VARCHAR(15) UNIQUE,
    product_name VARCHAR(30),
    gross_sales DECIMAL(12,2),
    received_amount DECIMAL(12,2) DEFAULT 0,
    pending_amount DECIMAL(12,2)
    GENERATED ALWAYS AS (gross_sales - received_amount) STORED,
    status ENUM('Open','Close') DEFAULT 'Open',
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE payment_splits (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT,
    payment_date DATE,
    amount_paid DECIMAL(12,2),
    payment_method VARCHAR(50),
    FOREIGN KEY (sale_id) REFERENCES customer_sales(sale_id)
);

CREATE INDEX idx_sale_id ON payment_splits(sale_id);

DELIMITER $$

CREATE TRIGGER trg_after_payment_insert
AFTER INSERT ON payment_splits
FOR EACH ROW
BEGIN
    UPDATE customer_sales
    SET received_amount = (
        SELECT IFNULL(SUM(amount_paid),0)
        FROM payment_splits
        WHERE sale_id = NEW.sale_id
    ),
    status = CASE
        WHEN (
            SELECT IFNULL(SUM(amount_paid),0)
            FROM payment_splits
            WHERE sale_id = NEW.sale_id
        ) >= gross_sales THEN 'Close'
        ELSE 'Open'
    END
    WHERE sale_id = NEW.sale_id;
END$$

DELIMITER ;

INSERT INTO branches (branch_name, branch_admin_name) VALUES
('Chennai','Arun'),
('Bangalore','Ravi'),
('Delhi','Suresh'),
('Mumbai','Kiran');

INSERT INTO users (username, password, branch_id, role, email) VALUES
('chennai_admin','admin123',1,'Admin','chennai@gmail.com'),
('bangalore_admin','admin123',2,'Admin','bangalore@gmail.com'),
('delhi_admin','admin123',3,'Admin','delhi@gmail.com'),
('mumbai_admin','admin123',4,'Admin','mumbai@gmail.com');

-- PROCEDURES WITHOUT EMOJI
DELIMITER $$

CREATE PROCEDURE generate_sales()
BEGIN
    DECLARE i INT DEFAULT 1;

    WHILE i <= 1000 DO
        INSERT INTO customer_sales
        (sale_id, branch_id, date, name, mobile_number, product_name, gross_sales)
        VALUES
        (
            i,
            (i % 4) + 1,
            DATE_ADD('2024-01-01', INTERVAL i DAY),
            CONCAT('Customer', i),
            CONCAT('900000', LPAD(i,4,'0')),
            CASE 
                WHEN i % 4 = 0 THEN 'DS'
                WHEN i % 4 = 1 THEN 'FSD'
                WHEN i % 4 = 2 THEN 'DA'
                ELSE 'BA'
            END,
            50000
        );

        SET i = i + 1;
    END WHILE;
END$$

CREATE PROCEDURE generate_payments()
BEGIN
    DECLARE i INT DEFAULT 1;

    WHILE i <= 1000 DO

        -- Only 1 payment for some (Pending case)
        IF i % 3 = 0 THEN

            INSERT INTO payment_splits
            (sale_id, payment_date, amount_paid, payment_method)
            VALUES
            (i, DATE_ADD('2024-01-01', INTERVAL i DAY), 30000, 'UPI');

        ELSE

            -- Full payment
            INSERT INTO payment_splits
            (sale_id, payment_date, amount_paid, payment_method)
            VALUES
            (i, DATE_ADD('2024-01-01', INTERVAL i DAY), 30000, 'UPI');

            INSERT INTO payment_splits
            (sale_id, payment_date, amount_paid, payment_method)
            VALUES
            (i, DATE_ADD('2024-01-02', INTERVAL i DAY), 20000, 'Cash');

        END IF;

        SET i = i + 1;

    END WHILE;

END$$
DELIMITER ;

CALL generate_sales();
CALL generate_payments();
DESC customer_sales;
select*from customer_sales
DELETE FROM payment_splits 
WHERE sale_id = 1001;