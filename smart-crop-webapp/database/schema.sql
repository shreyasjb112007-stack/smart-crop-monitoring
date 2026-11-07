-- ============================================================
-- schema.sql
-- SmartCropDB - matches the exact schema from your DBMS lab
-- Experiments 1-6, with ONE addition: Farmer.Password (needed
-- for login/signup) and ONE new table: Diagnosis (links a
-- Milvus vector-search result back to the relational side).
-- ============================================================

CREATE DATABASE IF NOT EXISTS SmartCropDB;
USE SmartCropDB;

-- --------------------------------------------------------
-- Farmer  (same as lab Experiment 1, + Password for login)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Farmer (
    Farmer_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(50) NOT NULL,
    Phone VARCHAR(15) UNIQUE NOT NULL,
    Address VARCHAR(100),
    Password VARCHAR(255) NOT NULL   -- stored as a hash, never plaintext
);

-- --------------------------------------------------------
-- Farm  (same as lab)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Farm (
    Farm_ID INT AUTO_INCREMENT PRIMARY KEY,
    Farmer_ID INT NOT NULL,
    Location VARCHAR(100),
    Area DECIMAL(5,2),
    FOREIGN KEY (Farmer_ID) REFERENCES Farmer(Farmer_ID) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Crop  (same as lab)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Crop (
    Crop_ID INT AUTO_INCREMENT PRIMARY KEY,
    Farm_ID INT NOT NULL,
    Crop_Name VARCHAR(50),
    Variety VARCHAR(50),
    Planting_Date DATE,
    FOREIGN KEY (Farm_ID) REFERENCES Farm(Farm_ID) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Disease  (same as lab) - master list, seeded once
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Disease (
    Disease_ID INT AUTO_INCREMENT PRIMARY KEY,
    Disease_Name VARCHAR(50),
    Crop_Name VARCHAR(50),        -- same disease name can behave differently per crop
    Symptoms VARCHAR(150),
    Severity VARCHAR(20)
);

-- --------------------------------------------------------
-- Treatment  (same as lab)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Treatment (
    Treatment_ID INT AUTO_INCREMENT PRIMARY KEY,
    Disease_ID INT,
    Treatment_Name VARCHAR(100),
    Dosage VARCHAR(50),
    FOREIGN KEY (Disease_ID) REFERENCES Disease(Disease_ID) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Image  (same as lab) - one row per uploaded/captured photo
-- Milvus_Vector_ID = the image_id used as the primary key
-- inside the Milvus CropDiseaseImages collection (DA1).
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Image (
    Image_ID INT AUTO_INCREMENT PRIMARY KEY,
    Crop_ID INT NOT NULL,
    Image_Path VARCHAR(150),
    Capture_Date DATE,
    Milvus_Vector_ID VARCHAR(50),
    FOREIGN KEY (Crop_ID) REFERENCES Crop(Crop_ID) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Diagnosis  (NEW) - the logged RESULT of a Milvus similarity
-- search for a given Image: which disease it matched, with
-- what similarity score. This is what "diagnosed_as" from the
-- EER model becomes as a real relation.
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS Diagnosis (
    Image_ID INT NOT NULL,
    Disease_ID INT NOT NULL,
    Similarity_Score DECIMAL(5,2),
    Diagnosed_On DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Image_ID, Disease_ID),
    FOREIGN KEY (Image_ID) REFERENCES Image(Image_ID) ON DELETE CASCADE,
    FOREIGN KEY (Disease_ID) REFERENCES Disease(Disease_ID) ON DELETE CASCADE
);

-- --------------------------------------------------------
-- Indexes (from lab Experiment 6, kept consistent)
-- --------------------------------------------------------
CREATE INDEX idx_crop_name ON Crop(Crop_Name);
CREATE UNIQUE INDEX idx_farmer_phone ON Farmer(Phone);
CREATE INDEX idx_farm_loc_area ON Farm(Location, Area);
