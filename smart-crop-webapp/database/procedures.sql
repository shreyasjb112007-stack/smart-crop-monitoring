-- ============================================================
-- procedures.sql
-- The 4 PL/SQL-style items assigned for DA2:
--   1. Disease report
--   2. Treatment recommendation
--   3. Crop statistics
--   4. Inspection history
--
-- Written as MySQL stored procedures/functions (DELIMITER blocks,
-- variables, cursors, conditionals) -- the procedural-SQL
-- equivalent of Oracle PL/SQL, since the department's lab
-- (Experiments 1-6) is MySQL-based.
-- ============================================================

USE SmartCropDB;

-- ------------------------------------------------------------
-- 1. DISEASE REPORT
-- For a given farmer: every diagnosis ever recorded across all
-- their crops, plus a running severity-level tally built with a
-- CURSOR + LOOP (demonstrates procedural control flow, not just
-- a bare SELECT).
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS GetDiseaseReport;
DELIMITER $$
CREATE PROCEDURE GetDiseaseReport(IN p_farmer_id INT)
BEGIN
    DECLARE v_done INT DEFAULT 0;
    DECLARE v_severity VARCHAR(20);
    DECLARE v_low INT DEFAULT 0;
    DECLARE v_moderate INT DEFAULT 0;
    DECLARE v_high INT DEFAULT 0;

    DECLARE sev_cursor CURSOR FOR
        SELECT d.Severity
        FROM Diagnosis diag
        JOIN Image i ON diag.Image_ID = i.Image_ID
        JOIN Crop c ON i.Crop_ID = c.Crop_ID
        JOIN Farm f ON c.Farm_ID = f.Farm_ID
        JOIN Disease d ON diag.Disease_ID = d.Disease_ID
        WHERE f.Farmer_ID = p_farmer_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    -- detailed row-level report
    SELECT
        f.Farmer_ID, fr.Location AS Farm_Location, c.Crop_Name,
        d.Disease_Name, d.Severity, diag.Similarity_Score, diag.Diagnosed_On
    FROM Diagnosis diag
    JOIN Image i ON diag.Image_ID = i.Image_ID
    JOIN Crop c ON i.Crop_ID = c.Crop_ID
    JOIN Farm fr ON c.Farm_ID = fr.Farm_ID
    JOIN Farmer f ON fr.Farmer_ID = f.Farmer_ID
    JOIN Disease d ON diag.Disease_ID = d.Disease_ID
    WHERE f.Farmer_ID = p_farmer_id
    ORDER BY diag.Diagnosed_On DESC;

    -- severity tally via cursor loop
    OPEN sev_cursor;
    sev_loop: LOOP
        FETCH sev_cursor INTO v_severity;
        IF v_done = 1 THEN
            LEAVE sev_loop;
        END IF;
        IF v_severity = 'Low' THEN
            SET v_low = v_low + 1;
        ELSEIF v_severity = 'Moderate' THEN
            SET v_moderate = v_moderate + 1;
        ELSE
            SET v_high = v_high + 1;
        END IF;
    END LOOP;
    CLOSE sev_cursor;

    SELECT v_low AS Low_Count, v_moderate AS Moderate_Count, v_high AS High_Count;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 2. TREATMENT RECOMMENDATION
-- Given a crop name + disease name (as returned by the Milvus
-- search), look up the matching Disease row and return its
-- treatment(s). Uses an IF to handle the "not found" case
-- explicitly rather than returning an empty result silently.
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS GetTreatmentRecommendation;
DELIMITER $$
CREATE PROCEDURE GetTreatmentRecommendation(
    IN p_crop_name VARCHAR(50),
    IN p_disease_name VARCHAR(50)
)
BEGIN
    DECLARE v_disease_id INT;

    SELECT Disease_ID INTO v_disease_id
    FROM Disease
    WHERE Crop_Name = p_crop_name AND Disease_Name = p_disease_name
    LIMIT 1;

    IF v_disease_id IS NULL THEN
        SELECT CONCAT('No treatment record found for ', p_disease_name,
                       ' on ', p_crop_name) AS Message;
    ELSE
        SELECT d.Disease_Name, d.Severity, t.Treatment_Name, t.Dosage
        FROM Treatment t
        JOIN Disease d ON t.Disease_ID = d.Disease_ID
        WHERE t.Disease_ID = v_disease_id;
    END IF;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 3. CROP STATISTICS
-- Per-crop summary for a farmer: how many inspections (images),
-- how many came back diseased vs healthy, and the most recent
-- diagnosis. Aggregate query, no cursor needed here.
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS GetCropStatistics;
DELIMITER $$
CREATE PROCEDURE GetCropStatistics(IN p_farmer_id INT)
BEGIN
    SELECT
        c.Crop_ID,
        c.Crop_Name,
        c.Variety,
        c.Planting_Date,
        COUNT(DISTINCT i.Image_ID) AS Total_Inspections,
        SUM(CASE WHEN d.Disease_Name <> 'Healthy' THEN 1 ELSE 0 END) AS Diseased_Inspections,
        MAX(diag.Diagnosed_On) AS Last_Diagnosis_Date
    FROM Crop c
    JOIN Farm f ON c.Farm_ID = f.Farm_ID
    LEFT JOIN Image i ON i.Crop_ID = c.Crop_ID
    LEFT JOIN Diagnosis diag ON diag.Image_ID = i.Image_ID
    LEFT JOIN Disease d ON diag.Disease_ID = d.Disease_ID
    WHERE f.Farmer_ID = p_farmer_id
    GROUP BY c.Crop_ID, c.Crop_Name, c.Variety, c.Planting_Date
    ORDER BY c.Planting_Date DESC;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 4. INSPECTION HISTORY
-- Full chronological history of every image + diagnosis for one
-- specific crop (what the farmer sees on a "crop detail" page).
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS GetInspectionHistory;
DELIMITER $$
CREATE PROCEDURE GetInspectionHistory(IN p_crop_id INT)
BEGIN
    SELECT
        i.Image_ID,
        i.Image_Path,
        i.Capture_Date,
        d.Disease_Name,
        d.Severity,
        diag.Similarity_Score,
        diag.Diagnosed_On
    FROM Image i
    LEFT JOIN Diagnosis diag ON diag.Image_ID = i.Image_ID
    LEFT JOIN Disease d ON diag.Disease_ID = d.Disease_ID
    WHERE i.Crop_ID = p_crop_id
    ORDER BY i.Capture_Date DESC;
END$$
DELIMITER ;
