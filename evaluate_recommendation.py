from recommendation import get_recommendations
import sqlite3
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split

def evaluate_recommendations():
    """Evaluates recommendation system accuracy using Precision, Recall, and Confusion Matrix."""
    
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Fetch purchase history (user_id, product_id)
    cursor.execute("SELECT user_id, product_id FROM transactions")
    data = cursor.fetchall()
    conn.close()

    if not data:
        print("🔴 No transaction data available for evaluation.")
        return

    # Convert data to DataFrame
    df = pd.DataFrame(data, columns=["user_id", "product_id"])

    # Split into training and test sets (80% training, 20% testing)
    train_data, test_data = train_test_split(df, test_size=0.2, random_state=42)

    # Actual purchases in the test set
    actual_purchases = test_data.groupby("user_id")["product_id"].apply(set).to_dict()

    predicted_purchases = {}
    
    # Generate recommendations for test users
    for user_id in test_data["user_id"].unique():
        recommended_product_ids = get_recommendations(user_id, top_n=5)
        predicted_purchases[user_id] = set(recommended_product_ids) if recommended_product_ids else set()

    # Convert to binary arrays for evaluation
    y_true = []
    y_pred = []

    for user_id in actual_purchases.keys():
        actual_items = actual_purchases[user_id]
        predicted_items = predicted_purchases.get(user_id, set())

        for product_id in train_data["product_id"].unique():
            y_true.append(1 if product_id in actual_items else 0)
            y_pred.append(1 if product_id in predicted_items else 0)

    # Calculate Precision, Recall, and F1-score
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    # Confusion Matrix
    conf_matrix = confusion_matrix(y_true, y_pred)

    print("\n📊 Recommendation System Evaluation 📊")
    print(f"✅ Precision: {precision:.2f}")
    print(f"✅ Recall: {recall:.2f}")
    print(f"✅ F1-score: {f1:.2f}")
    print("🟢 Confusion Matrix:")
    print(conf_matrix)

# Run evaluation
if __name__ == "__main__":
    evaluate_recommendations()
