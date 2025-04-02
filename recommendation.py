import sqlite3
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import os

CACHE_FILE = "recommendation_matrix.pkl"



def get_recommendations(user_id, top_n=5):
    """Returns top N recommended product IDs for the given user."""
    
    user_item_matrix = build_user_item_matrix()
    
    if user_item_matrix is None:
        print("🔴 No user-item matrix found.")  # Debugging
        return []

    if str(user_id) not in user_item_matrix.index:
        print(f"🔴 User {user_id} not found in user-item matrix.")  # Debugging
        print("🟡 Existing users in matrix:", list(user_item_matrix.index))  # Debugging
        return []

    # Compute user similarity
    user_similarity = cosine_similarity(user_item_matrix)

    # Get index of the given user
    user_idx = user_item_matrix.index.get_loc(str(user_id))

    # Find top similar users
    similar_users = np.argsort(user_similarity[user_idx])[::-1][1:6]  # Top 5 similar users

    # Get product recommendations
    recommended_products = set()
    for similar_user in similar_users:
        similar_user_id = user_item_matrix.index[similar_user]
        purchased_items = set(user_item_matrix.columns[user_item_matrix.loc[similar_user_id] > 0])
        recommended_products.update(purchased_items)

    print(f"🟢 Recommended products for user {user_id}: {recommended_products}")  # Debugging

    return list(recommended_products)[:top_n]


def build_user_item_matrix():
    """Builds the user-item matrix for recommendations."""
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Fetch purchase history (user_id, product_id, purchase_count)
    cursor.execute("""
        SELECT user_id, product_id, COUNT(product_id) as purchase_count 
        FROM transactions 
        GROUP BY user_id, product_id
    """)
    
    data = cursor.fetchall()
    conn.close()

    if not data:
        print("🔴 No transactions found in database.")  # Debugging
        return None  # No recommendations possible

    # Convert to DataFrame
    df = pd.DataFrame(data, columns=["user_id", "product_id", "purchase_count"])

    # Ensure user_id is a string
    df["user_id"] = df["user_id"].astype(str)  # ✅ Fix user_id type issue

    # Create user-item matrix
    user_item_matrix = df.pivot_table(index="user_id", columns="product_id", values="purchase_count", fill_value=0)

    return user_item_matrix

    
    return list(recommended_products)[:top_n]

