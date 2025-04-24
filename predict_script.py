
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from numpy.linalg import inv
import random

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

# Diagnosis and procedure code pools used for simulation
DX_CODES = ['R73.03', 'Z00.00', 'E11.9', 'I10', 'Z13.1', 'Z12.83', 'E78.0', 'F32.9']
CPT_CODES = ['82947', '99284', '99396', '83036', '99281', '99283', '80050', '11102', '80061', '96127']

# Manually defined members with known diabetes outcomes (for grounding predictions)
MANUAL_MEMBERS = [
    {'member_id': 'M1', 'age': 57, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '99284'], 'outcome_diabetes': 1},
    {'member_id': 'M2', 'age': 45, 'dx_codes': ['Z00.00'], 'cpt_codes': ['99396'], 'outcome_diabetes': 0},
    {'member_id': 'M3', 'age': 62, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '83036', '99283'], 'outcome_diabetes': 1},
    {'member_id': 'M4', 'age': 60, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '99284'], 'outcome_diabetes': 1},
    {'member_id': 'M5', 'age': 50, 'dx_codes': ['Z00.00'], 'cpt_codes': ['99396', '99281'], 'outcome_diabetes': 0}
]

# -----------------------------------------
# STEP 1: Generate synthetic member data
# -----------------------------------------

try:
    n = int(input("How many random members to generate (besides the 5 manual ones)? "))
except:
    n = 50

# Randomly generate n new members with placeholder outcomes
random_members = []
for i in range(n):
    random_members.append({
        'member_id': f'R{i+1}',
        'age': random.randint(30, 80),
        'dx_codes': random.sample(DX_CODES, k=random.randint(1, 2)),
        'cpt_codes': random.sample(CPT_CODES, k=random.randint(1, 3)),
        'outcome_diabetes': 0
    })

# Combine manual and generated members into a single DataFrame
data = pd.DataFrame(MANUAL_MEMBERS + random_members)

# -----------------------------------------
# STEP 2: Feature engineering
# -----------------------------------------

# Utility functions to extract signals from claims
def has_code(codes, target): return int(target in (codes or []))
def count_er_visits(cpts): return sum(1 for code in (cpts or []) if code in {'99281', '99282', '99283', '99284', '99285'})
def medication_adherence(cpts): return 0.5 if '82947' in (cpts or []) else 0.9

# Define features and their extraction logic using lambda row access
feature_functions = {
    'has_prediabetes': lambda row: has_code(row['dx_codes'], 'R73.03'),
    'has_htn': lambda row: has_code(row['dx_codes'], 'I10'),
    'has_lipid_disorder': lambda row: has_code(row['dx_codes'], 'E78.0'),
    'has_depression': lambda row: has_code(row['dx_codes'], 'F32.9'),
    'screened_skin_cancer': lambda row: has_code(row['dx_codes'], 'Z12.83'),
    'cholesterol_tested': lambda row: has_code(row['cpt_codes'], '80061'),
    'mental_health_screen': lambda row: has_code(row['cpt_codes'], '96127'),
    'medication_adherence': lambda row: medication_adherence(row['cpt_codes']),
    'er_visits': lambda row: count_er_visits(row['cpt_codes'])
}

# Apply feature functions to data
for feature, func in feature_functions.items():
    data[feature] = data.apply(func, axis=1)

# Final list of features including demographics
FEATURES = list(feature_functions.keys()) + ['age']

# -----------------------------------------
# STEP 3: Clean feature matrix
# -----------------------------------------

# Drop constant features and add slight noise to numeric fields
X = data[FEATURES].copy()
cleaned_features = []

for col in FEATURES:
    if X[col].nunique() <= 1:
        print(f"Dropped constant feature: {col}")
        X.drop(columns=col, inplace=True)
    else:
        X[col] += np.random.normal(0, 1e-4, size=len(X))
        cleaned_features.append(col)

# -----------------------------------------
# STEP 4: Relevance-based prediction
# -----------------------------------------

outcomes = data['outcome_diabetes'].values

if len(X) < 2 or X.shape[1] < 1:
    print("Not enough data to perform prediction.")
    exit()

# Compute Mahalanobis-based similarity
cov = np.cov(X, rowvar=False) + np.eye(X.shape[1]) * 1e-6
rel = 1 / (1 + cdist(X, X, metric='mahalanobis', VI=inv(cov)))
np.fill_diagonal(rel, 0)

# Normalize and weight outcomes by relevance
rel_norm = rel / rel.sum(axis=1, keepdims=True)
predicted = rel_norm @ outcomes

# Compute fit score (a measure of prediction confidence)
z_rel = (rel_norm - rel_norm.mean(axis=1, keepdims=True)) / rel_norm.std(axis=1, keepdims=True)
z_out = (outcomes - outcomes.mean()) / outcomes.std()
fit_scores = (z_rel @ z_out) ** 2 / (len(X) ** 2)

# -----------------------------------------
# STEP 5: Output predictions
# -----------------------------------------

results = pd.DataFrame({
    'member_id': data['member_id'],
    'predicted_diabetes_risk': np.round(predicted, 3),
    'fit_score': np.round(fit_scores, 3)
})

print("\nRelevance-Based Prediction Results:")
print(results.to_string(index=False))
