# -*- coding: utf-8 -*-
"""ML_Capstone.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1b-KXYuKcF5M_RYr6lxn6rfSEH3mRqDUr
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import haversine_distances, euclidean_distances
from math import radians

# Merge all dataset sheets
file_path = "Dataset Model.xlsx"
sheets =  pd.read_excel(file_path, sheet_name=None)
dataframes = []

for sheet_name, sheet_df in sheets.items():
  sheet_df['Kota'] = sheet_name
  dataframes.append(sheet_df)

df = pd.concat(dataframes, ignore_index=True)
df.info()

# Normalization of Latitude and Longitude columns
scaler = MinMaxScaler()
pd_normalized = scaler.fit_transform(df[['Latitude', 'Longitude']])
df_normalized = pd.DataFrame(pd_normalized)
df_normalized.info()

# Define the autoencoder model
input_dim = df_normalized.shape[1]  # Number of features (2: lat, lon)
encoding_dim = 2  # Latent space dimension (can adjust this)

# Input layer
input_layer = Input(shape=(input_dim,))
# Encoding layers
encoded = Dense(128, activation='relu')(input_layer)
encoded = Dense(encoding_dim, activation='relu')(encoded)
# Decoding layers
decoded = Dense(256, activation='relu')(encoded)
decoded = Dense(input_dim, activation='sigmoid')(decoded)

# Autoencoder model
autoencoder = Model(input_layer, decoded)

# Encoder model (for embeddings)
encoder = Model(input_layer, encoded)

# Compile the autoencoder
autoencoder.compile(optimizer='adam', loss='mse',metrics=['accuracy'])

# Train the autoencoder
early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10)
autoencoder.fit(df_normalized, df_normalized, epochs=100, batch_size=32, verbose=1, callbacks=[early_stopping])

# Get the embedding (compression representation) of the data
embeddings = encoder.predict(pd_normalized) # hidden representation of latitude and longitude
embedding_df = pd.DataFrame(embeddings, columns=['dim1', 'dim2'])
print(embedding_df)

# Cluster embeddings
kmeans = KMeans(n_clusters=3, random_state=42)
df['Cluster'] = kmeans.fit_predict(embeddings)

# Function to find the closest location
def find_nearest_locations_with_rating(user_location, df, kmeans, encoder, scaler, n_neighbors, weight_distance, weight_rating):
  """
     Search for nearby locations based on geographical distance and place rating.
     Args:
        user_location (list): User location coordinates [latitude, longitude].
        df (DataFrame): DataFrame dengan kolom ['Nama Tempat', 'Latitude', 'Longitude', 'Cluster', 'Rating'].
        kmeans (KMeans): KMeans model for clustering.
        encoder: Encoder model for location embedding.
        scaler: Normalizer for input data.
        n_neighbors (int): Number of closest locations taken.
        weight_distance (float): Weight for distance (0-1).
        weight_rating (float): Weight for rating (0-1).

    Returns:
        DataFrame: Place recommendation DataFrame with columns ['Nama Tempat', 'Latitude', 'Longitude', 'Jarak_km', 'Rating'].
    """
  # Normalize and encode user location
  user_location_arr = np.array([user_location])
  user_location_normalized = scaler.transform(user_location_arr)
  user_location_embedding = encoder.predict(user_location_normalized)
  # Cluster prediction
  new_cluster = kmeans.predict(user_location_embedding)[0]
  # Coordinate to radian conversion for Haversine calculation
  def prepare_coordinates(lat, lon):
      return np.array([[radians(lat), radians(lon)]])
  user_loc_radians = prepare_coordinates(user_location[0], user_location[1])
  # Filter data based on cluster and nearest cluster
  cluster_radius = 1  # Cluster radius for search (customizable)
  nearby_clusters = np.where(
      euclidean_distances(kmeans.cluster_centers_[new_cluster].reshape(1, -1),
                          kmeans.cluster_centers_) < cluster_radius)[1]

  potential_locations = df[df['Cluster'].isin(nearby_clusters)].copy()
  # If there are no locations in adjacent clusters, use the same cluster
  if len(potential_locations) == 0:
        potential_locations = df[df['Cluster'] == new_cluster].copy()
  # Calculate the Haversine distance for potential locations
  locations_radians = np.radians(
      potential_locations[['Latitude', 'Longitude']].values
  )
  # Calculate the distance in kilometers (earth radius = 6371 km)
  distances = haversine_distances(user_loc_radians, locations_radians)[0] * 6371

  # Add distance to DataFrame and sort
  potential_locations['Jarak_km'] = distances
  # Hitung skor berdasarkan kombinasi jarak dan rating
  potential_locations['Score'] = (
      weight_distance * potential_locations['Jarak_km'] +
      weight_rating * (-potential_locations['Rating'])  # Negative rating to prioritize higher value
  )
  # Sort by score
  nearest_locations = potential_locations.nsmallest(n_neighbors, 'Score')

  # Output format
  result = nearest_locations.copy()
  result['Jarak_km'] = result['Jarak_km'].round(2)
  return result

# User input
Lat_inp = float(input('Masukkan Latitude Lokasi: '))
Log_inp = float(input('Masukkan Longitude Lokasi: '))
user_location = [Lat_inp, Log_inp]

# Find recommended service places
place_recommendation = find_nearest_locations_with_rating(
    user_location=user_location,
    df=df,
    kmeans=kmeans,
    encoder=encoder,
    scaler=scaler,
    n_neighbors=5,
    weight_distance=0.5,  # Distance weight
    weight_rating=0.5     # Rating weight
)

print("Rekomendasi tempat servis yang ditemukan:")
print(place_recommendation[['Nama Tempat', 'Latitude', 'Longitude', 'Jarak_km', 'Rating']])