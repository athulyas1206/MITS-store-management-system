import sqlite3
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import os

CACHE_FILE = "recommendation_matrix.pkl"

def build_user_item_matrix():
    """Builds the user-item matrix and saves it to a file for caching."""
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, product_id, COUNT(product_id) as purchase_count 
        FROM transactions 
        GROUP BY user_id, product_id
    """)
    
    data = cursor.fetchall()
    conn.close()

    if not data:
        return None  # No data available

    df = pd.DataFrame(data, columns=["user_id", "product_id", "purchase_count"])

    user_item_matrix = df.pivot_table(index="user_id", columns="product_id", values="purchase_count", fill_value=0)
    
    # Save matrix to cache
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(user_item_matrix, f)
    
    return user_item_matrix

def get_recommendations(user_id, top_n=5):
    """Returns top N recommended product IDs for the given user."""
    # Load cached matrix or rebuild if not available
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            user_item_matrix = pickle.load(f)
    else:
        user_item_matrix = build_user_item_matrix()

    if user_item_matrix is None or user_id not in user_item_matrix.index:
        return []  # No recommendations for new users

    # Compute user similarity
    user_similarity = cosine_similarity(user_item_matrix)

    # Get index of the given user
    user_idx = user_item_matrix.index.get_loc(user_id)

    # Find top similar users
    similar_users = np.argsort(user_similarity[user_idx])[::-1][1:6]  # Top 5 similar users

    # Get product recommendations
    recommended_products = set()
    for similar_user in similar_users:
        similar_user_id = user_item_matrix.index[similar_user]
        purchased_items = set(user_item_matrix.columns[user_item_matrix.loc[similar_user_id] > 0])
        recommended_products.update(purchased_items)

    return list(recommended_products)[:top_n]
