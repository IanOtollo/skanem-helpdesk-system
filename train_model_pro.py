"""
ML Model Training Script - PRODUCTION VERSION
Aligned with Project Requirements Document
Features:
- Confidence threshold checking (60%)
- Model versioning and logging
- Performance metrics tracking
- CRISP-DM methodology implementation
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, precision_recall_fscore_support
import joblib
import os
import json
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================
CONFIDENCE_THRESHOLD = 0.60  # 60% - Manual review required below this
MODEL_VERSION = datetime.now().strftime("v%Y%m%d_%H%M%S")
DATA_PATH = 'data/training_data.csv'
MODEL_DIR = 'models/'
LOGS_DIR = 'logs/'

# Create directories
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

class TicketClassifierPro:
    """
    Professional Ticket Classifier with Confidence Scoring
    Implements requirements: Reliability, Maintainability, Scalability
    """
    
    def __init__(self, confidence_threshold=CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            stop_words='english',
            lowercase=True
        )
        self.models = {
            'naive_bayes': MultinomialNB(),
            'logistic_regression': LogisticRegression(
                max_iter=1000, 
                random_state=42
                # LogisticRegression automatically supports predict_proba()
            ),
            'svm': SVC(
                kernel='linear', 
                random_state=42,
                probability=True  # Enable probability for confidence scores
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100, 
                random_state=42
            )
        }
        self.best_model = None
        self.best_model_name = None
        self.model_metadata = {}
        
    def preprocess_text(self, text):
        """Clean and normalize text"""
        return text.lower().strip()
    
    def load_data(self, filepath):
        """
        Load and prepare training data
        CRISP-DM Phase 2: Data Understanding
        """
        print(f"\n{'='*70}")
        print("CRISP-DM PHASE 2: DATA UNDERSTANDING")
        print(f"{'='*70}")
        print(f"\nLoading data from {filepath}...")
        
        df = pd.read_csv(filepath)
        
        # Combine subject and description
        df['text'] = df['subject'] + ' ' + df['description']
        df['text'] = df['text'].apply(self.preprocess_text)
        
        print(f"✓ Loaded {len(df)} tickets")
        print(f"✓ Categories: {list(df['category'].unique())}")
        print(f"\nCategory distribution:")
        print(df['category'].value_counts())
        
        return df
    
    def prepare_data(self, df):
        """
        Prepare features and split data
        CRISP-DM Phase 3: Data Preparation
        """
        print(f"\n{'='*70}")
        print("CRISP-DM PHASE 3: DATA PREPARATION")
        print(f"{'='*70}")
        
        X = df['text']
        y = df['category']
        
        # Split data (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"\n✓ Training set: {len(X_train)} samples")
        print(f"✓ Testing set: {len(X_test)} samples")
        print(f"✓ Split ratio: 80/20")
        
        # Vectorize text
        print(f"\n✓ Applying TF-IDF vectorization...")
        X_train_vec = self.vectorizer.fit_transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)
        
        print(f"✓ Feature dimensions: {X_train_vec.shape[1]} features")
        
        return X_train_vec, X_test_vec, y_train, y_test
    
    def train_models(self, X_train, y_train):
        """
        Train multiple models and select best
        CRISP-DM Phase 4: Modeling
        """
        print(f"\n{'='*70}")
        print("CRISP-DM PHASE 4: MODELING")
        print(f"{'='*70}")
        
        results = {}
        
        for name, model in self.models.items():
            print(f"\nTraining {name.replace('_', ' ').title()}...")
            
            # Train model
            model.fit(X_train, y_train)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            
            results[name] = {
                'model': model,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            print(f"  ✓ Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        # Select best model
        best_name = max(results, key=lambda x: results[x]['cv_mean'])
        self.best_model = results[best_name]['model']
        self.best_model_name = best_name
        
        print(f"\n{'='*70}")
        print(f"✓ BEST MODEL: {best_name.replace('_', ' ').title()}")
        print(f"✓ CV Accuracy: {results[best_name]['cv_mean']:.4f}")
        print(f"{'='*70}")
        
        return results
    
    def evaluate_model(self, X_test, y_test):
        """
        Evaluate model performance
        CRISP-DM Phase 5: Evaluation
        """
        print(f"\n{'='*70}")
        print("CRISP-DM PHASE 5: EVALUATION")
        print(f"{'='*70}")
        
        # Predictions
        y_pred = self.best_model.predict(X_test)
        y_pred_proba = self.best_model.predict_proba(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average='weighted'
        )
        
        print(f"\nOVERALL PERFORMANCE:")
        print(f"  • Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"  • Precision: {precision:.4f}")
        print(f"  • Recall:    {recall:.4f}")
        print(f"  • F1-Score:  {f1:.4f}")
        
        # Per-category metrics
        print(f"\nPER-CATEGORY PERFORMANCE:")
        report = classification_report(y_test, y_pred, output_dict=True)
        
        category_metrics = {}
        for category in self.best_model.classes_:
            if category in report:
                metrics = report[category]
                category_metrics[category] = {
                    'precision': round(metrics['precision'], 4),
                    'recall': round(metrics['recall'], 4),
                    'f1-score': round(metrics['f1-score'], 4),
                    'support': int(metrics['support'])
                }
                print(f"  • {category:12} - P: {metrics['precision']:.4f}, R: {metrics['recall']:.4f}, F1: {metrics['f1-score']:.4f}")
        
        # Confidence analysis
        print(f"\nCONFIDENCE ANALYSIS:")
        max_confidences = y_pred_proba.max(axis=1)
        low_confidence_count = (max_confidences < self.confidence_threshold).sum()
        low_confidence_pct = (low_confidence_count / len(max_confidences)) * 100
        
        print(f"  • Confidence threshold: {self.confidence_threshold*100:.0f}%")
        print(f"  • Average confidence: {max_confidences.mean()*100:.2f}%")
        print(f"  • Low confidence predictions: {low_confidence_count}/{len(max_confidences)} ({low_confidence_pct:.2f}%)")
        print(f"  • These would be flagged for manual review")
        
        # Store metadata
        self.model_metadata = {
            'model_version': MODEL_VERSION,
            'model_type': self.best_model_name,
            'training_date': datetime.now().isoformat(),
            'confidence_threshold': self.confidence_threshold,
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'category_metrics': category_metrics,
            'categories': list(self.best_model.classes_),
            'feature_count': X_test.shape[1],
            'training_samples': len(y_test) * 5,  # Approximate from 80/20 split
            'testing_samples': len(y_test)
        }
        
        return accuracy, category_metrics
    
    def predict_with_confidence(self, text):
        """
        Predict category with confidence score
        Returns: (category, confidence_score, needs_manual_review)
        """
        # Preprocess
        text_clean = self.preprocess_text(text)
        text_vec = self.vectorizer.transform([text_clean])
        
        # Predict
        category = self.best_model.predict(text_vec)[0]
        confidence_proba = self.best_model.predict_proba(text_vec)[0]
        confidence_score = confidence_proba.max()
        
        # Check if manual review needed
        needs_manual_review = confidence_score < self.confidence_threshold
        
        return category, round(confidence_score * 100, 2), needs_manual_review
    
    def save_model(self):
        """
        Save model, vectorizer, and metadata
        CRISP-DM Phase 6: Deployment
        """
        print(f"\n{'='*70}")
        print("CRISP-DM PHASE 6: DEPLOYMENT")
        print(f"{'='*70}")
        
        # Save model
        model_path = os.path.join(MODEL_DIR, 'ticket_classifier.pkl')
        joblib.dump(self.best_model, model_path)
        print(f"\n✓ Model saved: {model_path}")
        
        # Save vectorizer
        vectorizer_path = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
        joblib.dump(self.vectorizer, vectorizer_path)
        print(f"✓ Vectorizer saved: {vectorizer_path}")
        
        # Save metadata
        metadata_path = os.path.join(MODEL_DIR, 'model_metadata.pkl')
        joblib.dump(self.model_metadata, metadata_path)
        print(f"✓ Metadata saved: {metadata_path}")
        
        # Save metadata as JSON for easy reading
        json_path = os.path.join(LOGS_DIR, f'model_{MODEL_VERSION}.json')
        with open(json_path, 'w') as f:
            json.dump(self.model_metadata, f, indent=2)
        print(f"✓ Training log saved: {json_path}")
        
        print(f"\n{'='*70}")
        print("✓ MODEL DEPLOYMENT COMPLETE")
        print(f"{'='*70}")
        
        return model_path, vectorizer_path, metadata_path


def main():
    """Main training pipeline"""
    
    print("\n" + "="*70)
    print("HELPDESK ML SYSTEM - MODEL TRAINING")
    print("CRISP-DM Methodology Implementation")
    print("="*70)
    
    # Phase 1: Business Understanding (already done in proposal)
    print(f"\n{'='*70}")
    print("CRISP-DM PHASE 1: BUSINESS UNDERSTANDING")
    print(f"{'='*70}")
    print("\n✓ Objective: Automate ticket classification")
    print("✓ Categories: Hardware, Software, Network, Database")
    print("✓ Success criteria: >60% accuracy with confidence scoring")
    print(f"✓ Confidence threshold: {CONFIDENCE_THRESHOLD*100:.0f}%")
    
    # Initialize classifier
    classifier = TicketClassifierPro(confidence_threshold=CONFIDENCE_THRESHOLD)
    
    # Load data (Phase 2)
    df = classifier.load_data(DATA_PATH)
    
    # Prepare data (Phase 3)
    X_train, X_test, y_train, y_test = classifier.prepare_data(df)
    
    # Train models (Phase 4)
    results = classifier.train_models(X_train, y_train)
    
    # Evaluate (Phase 5)
    accuracy, category_metrics = classifier.evaluate_model(X_test, y_test)
    
    # Deploy (Phase 6)
    model_path, vectorizer_path, metadata_path = classifier.save_model()
    
    # Test confidence scoring
    print(f"\n{'='*70}")
    print("CONFIDENCE SCORING TEST")
    print(f"{'='*70}")
    
    test_cases = [
        "Computer won't turn on and screen is black",
        "Cannot connect to WiFi network",
        "Microsoft Word keeps crashing when opening documents",
        "Database query running very slow"
    ]
    
    print("\nTesting predictions with confidence scores:\n")
    for test_text in test_cases:
        category, confidence, needs_review = classifier.predict_with_confidence(test_text)
        review_flag = "⚠️  MANUAL REVIEW" if needs_review else "✓ AUTO-ASSIGN"
        print(f"Text: {test_text[:50]}...")
        print(f"  → Category: {category}")
        print(f"  → Confidence: {confidence}%")
        print(f"  → Action: {review_flag}\n")
    
    # Final summary
    print(f"{'='*70}")
    print("TRAINING COMPLETE - SUMMARY")
    print(f"{'='*70}")
    print(f"\nModel Version: {MODEL_VERSION}")
    print(f"Best Algorithm: {classifier.best_model_name.replace('_', ' ').title()}")
    print(f"Accuracy: {accuracy*100:.2f}%")
    print(f"Confidence Threshold: {CONFIDENCE_THRESHOLD*100:.0f}%")
    print(f"\nFiles created:")
    print(f"  • {model_path}")
    print(f"  • {vectorizer_path}")
    print(f"  • {metadata_path}")
    print(f"\nReady for production deployment!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
