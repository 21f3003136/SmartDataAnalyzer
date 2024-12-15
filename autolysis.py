import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import openai
import requests
import chardet
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import statsmodels.api as sm
import geopandas as gpd
import networkx as nx

# Set up the AI Proxy token from environment variable
openai.api_key = os.environ["AIPROXY_TOKEN"]

def analyze_data(df):
    # Generate summary statistics
    summary_stats = df.describe(include='all').to_dict()
    missing_values = df.isnull().sum().to_dict()

    # Filter numeric columns for correlation analysis
    numeric_df = df.select_dtypes(include='number')

    # Check if there are any numeric columns available for correlation
    correlation_matrix = numeric_df.corr().to_dict() if not numeric_df.empty else {}

    return {
        "summary_stats": summary_stats,
        "missing_values": missing_values,
        "correlation_matrix": correlation_matrix,
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.apply(str).to_dict()
    }

def encoding(file_path):
    with open(file_path, "rb") as files:
        data = files.read()
    encod = chardet.detect(data)["encoding"]
    return encod

def detect_outliers(df):
    numeric_df = df.select_dtypes(include='number')
    isolation_forest = IsolationForest(contamination=0.05)
    outliers = isolation_forest.fit_predict(numeric_df)
    return df[outliers == -1]

def regression_analysis(df, target_column):
    X = df.drop(columns=[target_column])
    y = df[target_column]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    return model.coef_, model.intercept_

def feature_importance_analysis(df, target_column):
    X = df.drop(columns=[target_column])
    y = df[target_column]

    model = RandomForestRegressor()
    model.fit(X, y)

    importance = model.feature_importances_
    feature_importance = pd.Series(importance, index=X.columns).sort_values(ascending=False)
    
    return feature_importance

def time_series_analysis(df):
    time_columns = df.select_dtypes(include=['datetime', 'object']).columns.tolist()
    
    if not time_columns:
        raise ValueError("No suitable time column found in the dataset.")
    
    # Assume the first datetime column is the time series column
    time_column = time_columns[0]
    
    # Check for a numerical target column (not datetime)
    target_columns = df.select_dtypes(include='number').columns.tolist()
    
    if not target_columns:
        raise ValueError("No numerical target column found in the dataset.")
    
    target_column = target_columns[0]  # Assume the first numerical column is the target

    df[time_column] = pd.to_datetime(df[time_column])
    ts_data = df.set_index(time_column)[target_column]
    
    decomposition = sm.tsa.seasonal_decompose(ts_data, model='additive')
    
    return decomposition

def cluster_analysis(df, n_clusters=3):
    numeric_df = df.select_dtypes(include='number')
    
    if numeric_df.empty:
        raise ValueError("No numeric columns found for clustering.")
        
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(numeric_df)
    
    return kmeans.labels_

def geographic_analysis(df):
    lat_col = None
    lon_col = None
    
    # Identify latitude and longitude columns based on naming conventions or types
    for col in df.columns:
        if 'lat' in col.lower() or 'latitude' in col.lower():
            lat_col = col
        elif 'lon' in col.lower() or 'longitude' in col.lower():
            lon_col = col
            
    if lat_col is None or lon_col is None:
        raise ValueError("Latitude and/or longitude columns not found.")
        
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]))
    
    return gdf

def network_analysis(df):
    source_col = None
    target_col = None
    
    # Identify source and target columns based on naming conventions or types
    for col in df.columns:
        if 'source' in col.lower():
            source_col = col
        elif 'target' in col.lower():
            target_col = col
            
    if source_col is None or target_col is None:
        raise ValueError("Source and/or target columns not found.")
        
    G = nx.from_pandas_edgelist(df, source=source_col, target=target_col)
    
    return G

def visualize_data(df, output_dir):
   # Create a heatmap for the correlation matrix if applicable
   if df.select_dtypes(include='number').shape[1] > 0:
       plt.figure(figsize=(10, 8))
       sns.heatmap(df.select_dtypes(include='number').corr(), annot=True, fmt=".2f", cmap='coolwarm')  
       plt.title('Correlation Matrix')
       plt.savefig(os.path.join(output_dir, 'correlation_matrix.png'))
       plt.close()

def generate_story(analysis_results):
   prompt = f"Analyze the following dataset results:\n\n"
   prompt += f"Summary Statistics: {analysis_results['summary_stats']}\n"
   prompt += f"Missing Values: {analysis_results['missing_values']}\n"
   prompt += f"Correlation Matrix: {analysis_results['correlation_matrix']}\n"
   
   AI_TOKEN = os.getenv("AIPROXY_TOKEN")
   headers = {"Authorization": f"Bearer {AI_TOKEN}", "Content-Type": "application/json"}  
   data = {
       "model": "gpt-4o-mini",
       "messages": [{"role": "user", "content": prompt}]
   }
   
   try:
       response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)
       response_json = response.json()
       return response_json["choices"][0]["message"]["content"]
   except Exception as e:
       print(f"Error: {e}")
       sys.exit(1)

def save_readme(story, output_dir):
   with open(os.path.join(output_dir, 'README.md'), 'w') as f:
       f.write("# Data Analysis Report\n\n")
       f.write(story)

def main(file_path):
   output_dir = os.path.join(os.getcwd(), os.path.splitext(file_path)[0])
   
   if not os.path.exists(output_dir):
       os.mkdir(output_dir)

   encod = encoding(file_path)
   
   # Load the data for visualization
   df = pd.read_csv(file_path, encoding=encod)

   # Analyze the data
   analysis_results = analyze_data(df)

   # Outlier detection
   outliers_detected = detect_outliers(df)

   # Automatically determine the target column using AI (first numerical column)
   target_columns = df.select_dtypes(include='number').columns.tolist()
   
   if not target_columns:
       raise ValueError("No numerical target column found for regression analysis.")
       
   selected_target_column = target_columns[0]  # Assume the first numerical column is the target

   # Regression analysis using the detected target column
   regression_results = regression_analysis(df, selected_target_column)

   # Feature importance analysis (using the same detected target column)
   feature_importance_results = feature_importance_analysis(df, selected_target_column)

   # Time series analysis (dynamically find a time column)
   time_series_decomposition_result = time_series_analysis(df)

   # Cluster analysis (default to 3 clusters)
   cluster_labels_result = cluster_analysis(df)

   # Geographic analysis (dynamically find latitude and longitude columns)
   geographic_data_result = geographic_analysis(df)

   # Network analysis (dynamically find source and target columns)
   network_graph_result = network_analysis(df)

   # Visualize the data
   visualize_data(df, output_dir)
   
   # Generate a story from the analysis results including all analyses performed.
   story_content_parts=[
       generate_story(analysis_results),
       f"Outliers detected: {len(outliers_detected)}",
       f"Regression coefficients: {regression_results[0]}",
       f"Regression intercept: {regression_results[1]}",
       f"Feature importance: {feature_importance_results.to_dict()}",
       f"Time series decomposition result: {time_series_decomposition_result}",
       f"Cluster labels: {cluster_labels_result}",
       f"Geographic data points: {geographic_data_result}",
       f"Network graph nodes: {network_graph_result.number_of_nodes()} edges: {network_graph_result.number_of_edges()}"
   ]
   
   full_story_content="\n\n".join(story_content_parts)

   # Save the story as README.md
   save_readme(full_story_content, output_dir)

if __name__ == "__main__":
   import sys
   
   if len(sys.argv) != 2:
       print("Usage: uv run autolysis.py dataset.csv")
       sys.exit(1)
   
   main(sys.argv[1])
