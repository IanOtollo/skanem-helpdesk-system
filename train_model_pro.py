"""
SKANEM INTERLABELS AFRICA - ML MODEL TRAINING
Trains classifier to predict BOTH category AND priority
"""

import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import os
from datetime import datetime

# Create models directory
MODEL_DIR = 'models/'
os.makedirs(MODEL_DIR, exist_ok=True)

print("\n" + "="*70)
print("SKANEM HELPDESK - ML MODEL TRAINING")
print("Training models to predict: CATEGORY + PRIORITY")
print("="*70 + "\n")

# =============================================================================
# TRAINING DATA - EXPANDED WITH PRIORITY
# =============================================================================

training_data = [
    # HARDWARE - CRITICAL
    ("Server down", "Production server not responding", "Hardware", "Critical"),
    ("Network switch failure", "Main network switch stopped working", "Hardware", "Critical"),
    ("Data center outage", "Primary data center offline", "Hardware", "Critical"),
    
    # HARDWARE - HIGH
    ("Computer won't start", "My laptop won't power on at all", "Hardware", "High"),
    ("Laptop not booting", "Screen stays black when I press power", "Hardware", "High"),
    ("Monitor not working", "Monitor shows no display", "Hardware", "High"),
    ("Printer offline", "Office printer not responding", "Hardware", "High"),
    ("Keyboard broken", "Several keys not working on keyboard", "Hardware", "High"),
    
    # HARDWARE - MEDIUM
    ("Mouse not working", "Wireless mouse disconnecting frequently", "Hardware", "Medium"),
    ("Headset issue", "Audio cutting out on headset", "Hardware", "Medium"),
    ("USB port problem", "USB device not recognized", "Hardware", "Medium"),
    ("Webcam not detected", "Camera not showing in video calls", "Hardware", "Medium"),
    
    # HARDWARE - LOW
    ("Need new mouse pad", "Old mouse pad worn out", "Hardware", "Low"),
    ("Request ergonomic keyboard", "Want to upgrade keyboard", "Hardware", "Low"),
    ("Cable management", "Need cable organizers for desk", "Hardware", "Low"),
    
    # SOFTWARE - CRITICAL
    ("Production system crash", "Critical business application crashed", "Software", "Critical"),
    ("Database corruption", "Cannot access production database", "Software", "Critical"),
    ("System-wide software failure", "All workstations affected", "Software", "Critical"),
    
    # SOFTWARE - HIGH
    ("Excel keeps crashing", "Excel closes unexpectedly when working", "Software", "High"),
    ("Cannot open Word documents", "Word files won't open", "Software", "High"),
    ("Outlook not receiving emails", "Haven't received emails since morning", "Software", "High"),
    ("Software won't install", "Installation keeps failing", "Software", "High"),
    ("Application error", "Getting error message when launching app", "Software", "High"),
    
    # SOFTWARE - MEDIUM
    ("PowerPoint slow", "Presentation runs slowly", "Software", "Medium"),
    ("PDF reader issues", "Cannot annotate PDFs", "Software", "Medium"),
    ("Browser running slow", "Chrome takes long to load pages", "Software", "Medium"),
    ("Teams audio problem", "Microphone not working in Teams", "Software", "Medium"),
    
    # SOFTWARE - LOW
    ("Need software update", "Want latest version of Adobe", "Software", "Low"),
    ("Desktop icon missing", "Lost shortcut to application", "Software", "Low"),
    ("Change default browser", "Want to set Firefox as default", "Software", "Low"),
    
    # NETWORK - CRITICAL
    ("Internet down company-wide", "No internet access anywhere", "Network", "Critical"),
    ("VPN server offline", "Remote workers cannot connect", "Network", "Critical"),
    ("Email server down", "Cannot send or receive any emails", "Network", "Critical"),
    
    # NETWORK - HIGH
    ("Cannot connect to wifi", "Laptop won't connect to network", "Network", "High"),
    ("No internet access", "Connected to wifi but no internet", "Network", "High"),
    ("VPN not connecting", "Cannot establish VPN connection", "Network", "High"),
    ("Network very slow", "Internet extremely slow today", "Network", "High"),
    ("Connection keeps dropping", "Wifi disconnects every few minutes", "Network", "High"),
    
    # NETWORK - MEDIUM
    ("Slow file transfer", "Takes long to access network drives", "Network", "Medium"),
    ("WiFi weak signal", "Poor connection in meeting room", "Network", "Medium"),
    ("Cannot access shared folder", "Network drive not appearing", "Network", "Medium"),
    
    # NETWORK - LOW
    ("Request wifi password", "Need guest network password", "Network", "Low"),
    ("Network printer setup", "Help setting up network printer", "Network", "Low"),
    
    # DATABASE - CRITICAL
    ("Database server crashed", "Production database not responding", "Database", "Critical"),
    ("Data loss incident", "Critical data appears to be missing", "Database", "Critical"),
    ("Cannot access customer database", "All customer data inaccessible", "Database", "Critical"),
    
    # DATABASE - HIGH
    ("Database query timeout", "Queries taking too long to run", "Database", "High"),
    ("Cannot connect to database", "Getting connection error", "Database", "High"),
    ("SQL error", "Getting SQL syntax error", "Database", "High"),
    ("Report not generating", "Database report failing to run", "Database", "High"),
    
    # DATABASE - MEDIUM
    ("Slow database query", "Query takes 5 minutes to complete", "Database", "Medium"),
    ("Need database access", "Require permissions for new table", "Database", "Medium"),
    ("Data export issue", "Cannot export data to Excel", "Database", "Medium"),
    
    # DATABASE - LOW
    ("Database training request", "Want to learn SQL basics", "Database", "Low"),
    ("Request new database view", "Need custom view created", "Database", "Low"),
]

# Convert to DataFrame
df = pd.DataFrame(training_data, columns=['subject', 'description', 'category', 'priority'])

print(f"✓ Training dataset created: {len(df)} samples")
print(f"✓ Categories: {df['category'].unique().tolist()}")
print(f"✓ Priority levels: {df['priority'].unique().tolist()}")

# =============================================================================
# PREPARE DATA
# =============================================================================

# Combine subject + description
df['text'] = df['subject'] + ' ' + df['description']

# Split data
X_train, X_test, y_cat_train, y_cat_test, y_pri_train, y_pri_test = train_test_split(
    df['text'], 
    df['category'],
    df['priority'],
    test_size=0.2, 
    random_state=42
)

print(f"\n✓ Data split:")
print(f"  Training: {len(X_train)} samples")
print(f"  Testing: {len(X_test)} samples")

# =============================================================================
# VECTORIZE TEXT
# =============================================================================

vectorizer = TfidfVectorizer(
    max_features=500,
    ngram_range=(1, 2),
    min_df=1
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

print(f"\n✓ TF-IDF vectorization complete")
print(f"  Features: {X_train_vec.shape[1]}")

# =============================================================================
# TRAIN CATEGORY MODEL
# =============================================================================

print("\n" + "-"*70)
print("TRAINING CATEGORY CLASSIFIER")
print("-"*70)

category_model = LogisticRegression(
    max_iter=1000,
    multi_class='multinomial',
    random_state=42
)

category_model.fit(X_train_vec, y_cat_train)

# Evaluate category model
y_cat_pred = category_model.predict(X_test_vec)
cat_accuracy = accuracy_score(y_cat_test, y_cat_pred)

print(f"\n✓ Category Model Accuracy: {cat_accuracy*100:.2f}%")
print("\nCategory Classification Report:")
print(classification_report(y_cat_test, y_cat_pred))

# =============================================================================
# TRAIN PRIORITY MODEL
# =============================================================================

print("\n" + "-"*70)
print("TRAINING PRIORITY CLASSIFIER")
print("-"*70)

priority_model = LogisticRegression(
    max_iter=1000,
    multi_class='multinomial',
    random_state=42
)

priority_model.fit(X_train_vec, y_pri_train)

# Evaluate priority model
y_pri_pred = priority_model.predict(X_test_vec)
pri_accuracy = accuracy_score(y_pri_test, y_pri_pred)

print(f"\n✓ Priority Model Accuracy: {pri_accuracy*100:.2f}%")
print("\nPriority Classification Report:")
print(classification_report(y_pri_test, y_pri_pred))

# =============================================================================
# SAVE MODELS
# =============================================================================

print("\n" + "-"*70)
print("SAVING MODELS")
print("-"*70)

# Save vectorizer
vectorizer_path = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
joblib.dump(vectorizer, vectorizer_path)
print(f"✓ Saved: {vectorizer_path}")

# Save category model
category_model_path = os.path.join(MODEL_DIR, 'ticket_classifier.pkl')
joblib.dump(category_model, category_model_path)
print(f"✓ Saved: {category_model_path}")

# Save priority model
priority_model_path = os.path.join(MODEL_DIR, 'priority_classifier.pkl')
joblib.dump(priority_model, priority_model_path)
print(f"✓ Saved: {priority_model_path}")

# Save metadata
metadata = {
    'model_version': 'v2.0',
    'model_type': 'LogisticRegression',
    'training_date': datetime.now().isoformat(),
    'training_samples': len(X_train),
    'testing_samples': len(X_test),
    'category_accuracy': cat_accuracy,
    'priority_accuracy': pri_accuracy,
    'categories': df['category'].unique().tolist(),
    'priorities': df['priority'].unique().tolist(),
    'features': X_train_vec.shape[1]
}

metadata_path = os.path.join(MODEL_DIR, 'model_metadata.pkl')
joblib.dump(metadata, metadata_path)
print(f"✓ Saved: {metadata_path}")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "="*70)
print("TRAINING COMPLETE")
print("="*70)
print(f"\n✓ Category Accuracy: {cat_accuracy*100:.2f}%")
print(f"✓ Priority Accuracy: {pri_accuracy*100:.2f}%")
print(f"✓ Total samples: {len(df)}")
print(f"✓ Categories: {len(df['category'].unique())}")
print(f"✓ Priority levels: {len(df['priority'].unique())}")
print(f"\nModels saved in: {MODEL_DIR}")
print("="*70 + "\n")
