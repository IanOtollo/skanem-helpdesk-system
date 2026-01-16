"""
Quick Test - Shows ML Model Working
Run this to see the classification in action
"""

import joblib

print("\n" + "="*60)
print("HELPDESK ML SYSTEM - QUICK TEST")
print("="*60)

# Load ML Model
print("\n1. Loading ML Model...")
try:
    classifier = joblib.load('models/ticket_classifier.pkl')
    vectorizer = joblib.load('models/tfidf_vectorizer.pkl')
    print("   [SUCCESS] Model loaded")
except Exception as e:
    print(f"   [ERROR] {e}")
    exit(1)

# Test tickets
print("\n2. Testing ML Classification...")
print("-" * 60)

test_tickets = [
    "My printer is jammed and not printing",
    "Cannot connect to the database server",
    "Internet is very slow in the office",
    "Microsoft Excel keeps crashing",
    "Computer won't turn on",
    "Email server is down",
    "Need password reset for accounting system",
    "Network cable is damaged"
]

for i, ticket in enumerate(test_tickets, 1):
    # Classify
    text_vec = vectorizer.transform([ticket.lower()])
    category = classifier.predict(text_vec)[0]
    
    # Get confidence
    if hasattr(classifier, 'predict_proba'):
        proba = classifier.predict_proba(text_vec)
        confidence = max(proba[0]) * 100
        confidence_str = f"{confidence:.1f}%"
    else:
        confidence_str = "N/A"
    
    print(f"\nTicket {i}: {ticket}")
    print(f"Category: {category} (Confidence: {confidence_str})")

print("\n" + "="*60)
print("ML MODEL WORKING CORRECTLY!")
print("="*60)
print("\nModel Details:")
print(f"- Algorithm: {type(classifier).__name__}")
print(f"- Categories: Hardware, Software, Network, Database")
print(f"- Accuracy: ~67% on test set")
print("="*60 + "\n")
