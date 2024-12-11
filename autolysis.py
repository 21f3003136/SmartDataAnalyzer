import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import openai
import requests

# Set up the AI Proxy token from environment variable
openai.api_key = os.environ["AIPROXY_TOKEN"]


def analyze_data(file_path):
    # Load the dataset
    df = pd.read_csv(file_path)

    # Generate summary statistics
    summary_stats = df.describe(include='all').to_dict()
    missing_values = df.isnull().sum().to_dict()
    
    # Filter numeric columns for correlation analysis
    numeric_df = df.select_dtypes(include='number')

    # Check if there are any numeric columns available for correlation
    if not numeric_df.empty:
        correlation_matrix = numeric_df.corr().to_dict()
    else:
        correlation_matrix = {}

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

def visualize_data(df, output_dir):
    # Create a heatmap for the correlation matrix if applicable
    if df.select_dtypes(include='number').shape[1] > 0:
        plt.figure(figsize=(10, 8))
        sns.heatmap(df.select_dtypes(include='number').corr(), annot=True, fmt=".2f", cmap='coolwarm')  
        plt.title('Correlation Matrix')
        plt.savefig(os.path.join(output_dir, 'correlation_matrix.png'))
        plt.close()

def generate_story(analysis_results):
    # Prepare the prompt for the LLM
    prompt = f"Analyze the following dataset results:\n\n"
    prompt += f"Summary Statistics: {analysis_results['summary_stats']}\n"
    prompt += f"Missing Values: {analysis_results['missing_values']}\n"
    prompt += f"Correlation Matrix: {analysis_results['correlation_matrix']}\n"
    prompt += "Write a narrative story about these findings."

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

    print(output_dir)
    # Analyze the data
    analysis_results = analyze_data(file_path)
    encod=encoding(file_path)
    print('abc',encod)
    # Load the data for visualization
    df = pd.read_csv(file_path, encoding=encod)
    
    # Visualize the data
    visualize_data(df, output_dir)
    
    # Generate a story from the analysis
    story = generate_story(analysis_results)
    
    # Save the story as README.md
    save_readme(story, output_dir)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py dataset.csv")
        sys.exit(1)
    
    main(sys.argv[1])