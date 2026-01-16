"""
ML Model Training Script for Helpdesk Ticket Classification
Uses TF-IDF and multiple classifiers to categorize tickets
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib
import os

class TicketClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            stop_words='english',
            lowercase=True
        )
        self.models = {
            'naive_bayes': MultinomialNB(),
            'logistic_regression': LogisticRegression(max_iter=1000, random_state=42),
            'svm': SVC(kernel='linear', random_state=42),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42)
        }
        self.best_model = None
        self.best_model_name = None
        
    def preprocess_text(self, text):
        """Combine subject and description for better classification"""
        return text.lower().strip()
    
    def load_data(self, filepath):
        """Load training data from CSV"""
        print(f"Loading data from {filepath}...")
        df = pd.read_csv(filepath)
        
        # Combine subject and description
        df['text'] = df['subject'] + ' ' + df['description']
        df['text'] = df['text'].apply(self.preprocess_text)
        
        print(f"Loaded {len(df)} tickets")
        print(f"Categories: {df['category'].unique()}")
        print(f"\nCategory distribution:")
        print(df['category'].value_counts())
        
        return df
    
    def train_models(self, X_train, y_train, X_test, y_test):
        """Train multiple models and select the best one"""
        print("\n" + "="*60)
        print("Training and Evaluating Models")
        print("="*60)
        
        best_score = 0
        
        for name, model in self.models.items():
            print(f"\n{name.upper().replace('_', ' ')}")
            print("-" * 40)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            
            # Accuracy
            accuracy = accuracy_score(y_test, y_pred)
            print(f"Accuracy: {accuracy:.4f}")
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            print(f"Cross-validation score: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
            
            # Track best model
            if accuracy > best_score:
                best_score = accuracy
                self.best_model = model
                self.best_model_name = name
        
        print("\n" + "="*60)
        print(f"BEST MODEL: {self.best_model_name.upper().replace('_', ' ')}")
        print(f"Best Accuracy: {best_score:.4f}")
        print("="*60)
        
        return self.best_model
    
    def evaluate_model(self, X_test, y_test):
        """Detailed evaluation of the best model"""
        print("\n" + "="*60)
        print("Detailed Evaluation of Best Model")
        print("="*60)
        
        y_pred = self.best_model.predict(X_test)
        
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        
    def save_model(self, model_dir='models'):
        """Save the trained model and vectorizer"""
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        # Save vectorizer
        vectorizer_path = os.path.join(model_dir, 'tfidf_vectorizer.pkl')
        joblib.dump(self.vectorizer, vectorizer_path)
        print(f"\nVectorizer saved to: {vectorizer_path}")
        
        # Save best model
        model_path = os.path.join(model_dir, 'ticket_classifier.pkl')
        joblib.dump(self.best_model, model_path)
        print(f"Model saved to: {model_path}")
        
        # Save model metadata
        metadata = {
            'model_name': self.best_model_name,
            'model_type': type(self.best_model).__name__
        }
        metadata_path = os.path.join(model_dir, 'model_metadata.pkl')
        joblib.dump(metadata, metadata_path)
        print(f"Metadata saved to: {metadata_path}")
        
    def predict(self, text):
        """Predict category for new ticket"""
        text_processed = self.preprocess_text(text)
        text_vectorized = self.vectorizer.transform([text_processed])
        prediction = self.best_model.predict(text_vectorized)
        
        # Get probability if available
        if hasattr(self.best_model, 'predict_proba'):
            proba = self.best_model.predict_proba(text_vectorized)
            confidence = np.max(proba) * 100
            return prediction[0], confidence
        else:
            return prediction[0], None

def main():
    # Initialize classifier
    classifier = TicketClassifier()
    
    # Load data
    data_path = 'data/training_data.csv'
    df = classifier.load_data(data_path)
    
    # Prepare features and labels
    X = df['text']
    y = df['category']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    
    # Vectorize text
    print("\nVectorizing text using TF-IDF...")
    X_train_vec = classifier.vectorizer.fit_transform(X_train)
    X_test_vec = classifier.vectorizer.transform(X_test)
    
    print(f"Feature vector shape: {X_train_vec.shape}")
    
    # Train models
    classifier.train_models(X_train_vec, y_train, X_test_vec, y_test)
    
    # Evaluate best model
    classifier.evaluate_model(X_test_vec, y_test)
    
    # Save model
    classifier.save_model()
    
    # Test predictions
    print("\n" + "="*60)
    print("Sample Predictions")
    print("="*60)
    
    test_cases = [
        "Printer not working in office",
        "Cannot connect to database",
        "Internet connection is very slow",
        "Excel keeps crashing when I open it"
    ]
    
    for test in test_cases:
        prediction, confidence = classifier.predict(test)
        if confidence:
            print(f"\nText: {test}")
            print(f"Predicted Category: {prediction}")
            print(f"Confidence: {confidence:.2f}%")
        else:
            print(f"\nText: {test}")
            print(f"Predicted Category: {prediction}")
    
    print("\n" + "="*60)
    print("Model Training Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
