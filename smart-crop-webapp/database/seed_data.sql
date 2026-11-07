-- ============================================================
-- seed_data.sql
-- Master data for Disease + Treatment.
-- IMPORTANT: Disease_Name + Crop_Name values here MUST match
-- the disease/crop labels produced by the Milvus search in
-- DA1 (generate_dataset.py), so a Milvus diagnosis result can
-- be looked up in this table by name and logged into Diagnosis.
-- ============================================================

USE SmartCropDB;

INSERT INTO Disease (Disease_Name, Crop_Name, Symptoms, Severity) VALUES
('Healthy',       'Tomato', 'No visible lesions or discoloration.',                 'Low'),
('Early Blight',  'Tomato', 'Small brown concentric-ring spots on older leaves.',   'Moderate'),
('Late Blight',   'Tomato', 'Large irregular water-soaked dark lesions, rapid spread.', 'High'),
('Healthy',       'Potato', 'No visible lesions or discoloration.',                 'Low'),
('Early Blight',  'Potato', 'Dark concentric spots, yellowing around lesions.',     'Moderate'),
('Late Blight',   'Potato', 'Dark, water-soaked patches, white mold on undersides.', 'High'),
('Healthy',       'Rice',   'No visible lesions or discoloration.',                 'Low'),
('Brown Spot',    'Rice',   'Small oval brown lesions across the leaf blade.',      'High');

INSERT INTO Treatment (Disease_ID, Treatment_Name, Dosage) VALUES
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Healthy' AND Crop_Name='Tomato'),
    'No treatment needed', 'Continue regular monitoring'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Early Blight' AND Crop_Name='Tomato'),
    'Fungicide (Chlorothalonil)', 'Spray every 7-10 days'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Late Blight' AND Crop_Name='Tomato'),
    'Copper-based fungicide', 'Apply immediately, repeat every 5-7 days'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Healthy' AND Crop_Name='Potato'),
    'No treatment needed', 'Continue regular monitoring'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Early Blight' AND Crop_Name='Potato'),
    'Fungicide + crop rotation', 'Spray every 7-10 days, rotate next season'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Late Blight' AND Crop_Name='Potato'),
    'Systemic fungicide', 'Apply immediately; remove severely infected plants'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Healthy' AND Crop_Name='Rice'),
    'No treatment needed', 'Continue regular monitoring'),
((SELECT Disease_ID FROM Disease WHERE Disease_Name='Brown Spot' AND Crop_Name='Rice'),
    'Fungicide + potassium fertilizer', 'Apply as per soil test recommendation');
