
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from numpy.linalg import inv

# -----------------------------
# Step 1: Simulated Claims Data
# -----------------------------
# This represents member-level data extracted from claims (like 837 files),
# with each member having diagnosis and procedure codes.

claims_data = pd.DataFrame([
    {'member_id': 'M1', 'age': 57, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '99284']},
    {'member_id': 'M2', 'age': 45, 'dx_codes': ['Z00.00'], 'cpt_codes': ['99396']},
    {'member_id': 'M3', 'age': 62, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '83036', '99283']},
    {'member_id': 'M4', 'age': 60, 'dx_codes': ['R73.03'], 'cpt_codes': ['82947', '99284']},
    {'member_id': 'M5', 'age': 50, 'dx_codes': ['Z00.00'], 'cpt_codes': ['99396', '99281']}
])

# Simulated outcome data indicating whether member developed diabetes
outcomes = {'M1': 1, 'M2': 0, 'M3': 1, 'M4': 1, 'M5': 0}

# -----------------------------------
# Step 2: Parse Claims to Features
# -----------------------------------
# We simulate diagnosis and medication adherence, and extract ER visits from CPT codes.

def has_prediabetes(dxs):
    return int('R73.03' in dxs)

def medication_adherence_stub(cpts):
    return 0.5 if '82947' in cpts else 0.9  # simulate lower adherence if tested

def count_er_visits(cpts):
    er_cpts = {'99281', '99282', '99283', '99284', '99285'}
    return sum(1 for code in cpts if code in er_cpts)

# Apply parsing logic
claims_data['has_prediabetes'] = claims_data['dx_codes'].apply(has_prediabetes)
claims_data['medication_adherence'] = claims_data['cpt_codes'].apply(medication_adherence_stub)
claims_data['er_visits'] = claims_data['cpt_codes'].apply(count_er_visits)
claims_data['outcome_diabetes'] = claims_data['member_id'].map(outcomes)

# ---------------------------------------------
# Step 3: Feature Matrix and Outcome Vector
# ---------------------------------------------
# These are the numeric inputs to our relevance-based model.

features = ['age', 'has_prediabetes', 'medication_adherence', 'er_visits']
X = claims_data[features].values
outcome_vector = claims_data['outcome_diabetes'].values

# ------------------------------------------------------
# Step 4: Mahalanobis Distance + Relevance (Vectorized)
# ------------------------------------------------------
# This calculates how similar each member is to every other member.

cov_matrix = np.cov(X, rowvar=False)
cov_matrix += np.eye(cov_matrix.shape[0]) * 1e-6  # regularize for stability
inv_cov = inv(cov_matrix)

# Pairwise Mahalanobis distance
distance_matrix = cdist(X, X, metric='mahalanobis', VI=inv_cov)

# Convert distance to similarity
relevance_matrix = 1 / (1 + distance_matrix)

# Avoid self-comparison
np.fill_diagonal(relevance_matrix, 0)

# Normalize weights so each row sums to 1
relevance_norm = relevance_matrix / relevance_matrix.sum(axis=1, keepdims=True)

# ---------------------------------------------
# Step 5: Predict Outcomes from Relevant Members
# ---------------------------------------------
# Weighted average of outcomes from similar (relevant) members.

weighted_outcomes = relevance_norm @ outcome_vector

# ----------------------------------------------------
# Step 6: Calculate Fit Score (Prediction Confidence)
# ----------------------------------------------------
# Fit is the squared correlation between relevance weights and actual outcomes.

z_relevance = (relevance_norm - relevance_norm.mean(axis=1, keepdims=True)) / relevance_norm.std(axis=1, keepdims=True)
z_outcomes = (outcome_vector - outcome_vector.mean()) / outcome_vector.std()
fit_scores = (z_relevance @ z_outcomes) ** 2 / (X.shape[0] ** 2)

# --------------------------------------
# Step 7: Output Result for All Members
# --------------------------------------
results_df = pd.DataFrame({
    'member_id': claims_data['member_id'],
    'predicted_diabetes_risk': np.round(weighted_outcomes, 3),
    'fit_score': np.round(fit_scores, 3)
})

# Pretty print the result
print("Batch Relevance-Based Prediction Results:")
print(results_df.to_string(index=False))
