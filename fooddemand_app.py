import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
import shap
import seaborn as sns
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import partial_dependence
from streamlit_folium import folium_static

# Streamlit App Title
st.title("📍 Food Hamper Demand Prediction & Explainability (XAI)")

# Sidebar: File Uploader
st.sidebar.header("Upload Your Processed Dataset")
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Load the dataset
        df = pd.read_csv(uploaded_file, encoding="utf-8")
        df["year_month"] = pd.to_datetime(df["year_month"])  # Convert to DateTime

        st.success("✅ File successfully uploaded!")

        # Display dataset preview
        st.subheader("📌 Dataset Preview")
        st.write(df.head())

        # 📍 Interactive Map of Hamper Distribution
        st.subheader("📍 Food Hamper Distribution Map")

        map_center = [df["latitude"].mean(), df["longitude"].mean()]
        m = folium.Map(location=map_center, zoom_start=10)
        marker_cluster = MarkerCluster().add_to(m)

        for _, row in df.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f"Postal Code: {row['postal_code']} | Hampers: {row['quantity']}",
                tooltip=row["postal_code"],
            ).add_to(marker_cluster)

        folium_static(m)

        # 📈 Feature Importance & SHAP Analysis
        st.subheader("📊 Feature Importance & SHAP Analysis")

        # Train a Random Forest model using all numerical features except 'quantity'
        X = df.select_dtypes(include=["number"]).drop(columns=["quantity"])
        y = df["quantity"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Feature Importance Plot
        feature_importances = pd.Series(model.feature_importances_, index=X.columns)
        fig_feat, ax = plt.subplots()
        feature_importances.plot(kind="barh", ax=ax, title="Feature Importance in Hamper Predictions")
        st.pyplot(fig_feat)

        # 📊 SHAP Analysis
        st.subheader("🔍 SHAP Explanation for Predictions")

        explainer = shap.Explainer(model, X_train)
        shap_values = explainer(X_test)

        # 📌 SHAP Summary Plot
        st.write("### SHAP Summary: Feature Impact on Predictions")
        st.write("This plot shows how different features contribute to hamper demand predictions.")

        fig_shap_summary, ax = plt.subplots()
        shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
        st.pyplot(fig_shap_summary)

        # 📌 SHAP Waterfall Plot for a Single Prediction
        st.write("### SHAP Waterfall: How a Single Prediction is Made")
        st.write("This plot explains how each feature contributes to a specific prediction.")

        # Select a sample observation for explanation
        sample_idx = np.random.randint(len(X_test))
        fig_waterfall = shap.plots.waterfall(shap_values[sample_idx])
        st.pyplot(fig_waterfall)

        # 📦 User Selection for Postal Code Prediction
        st.subheader("📦 Predict Hampers for a Given Postal Code")

        postal_code_selected = st.selectbox("Select a Postal Code", df["postal_code"].unique())

        if st.button("Predict Hampers"):
            location_row = df[df["postal_code"] == postal_code_selected].iloc[0]
            lat_input, lon_input = location_row["latitude"], location_row["longitude"]
            prediction = model.predict([[lat_input, lon_input]])[0]
            st.success(f"📦 Predicted Hampers for Postal Code {postal_code_selected}: {round(prediction)}")

        # 📈 Time Series Forecasting (ARIMA) with Prediction Intervals
        st.subheader("📉 Time-Based Hamper Demand Prediction (ARIMA)")

        def train_arima(postal_code):
            df_filtered = df[df["postal_code"] == postal_code].set_index("year_month")

            if len(df_filtered) < 12:
                st.warning("⚠️ Not enough historical data for reliable prediction.")
                return None, None

            try:
                model = ARIMA(df_filtered["quantity"], order=(2, 1, 1))
                model_fit = model.fit()

                # Predict next 6 months with confidence intervals
                forecast = model_fit.get_forecast(steps=6)
                pred_mean = forecast.predicted_mean
                pred_ci = forecast.conf_int()

                pred_index = pd.date_range(start=df_filtered.index[-1], periods=6, freq="M")

                return df_filtered, pred_mean, pred_ci, pred_index

            except Exception as e:
                st.error(f"⚠️ ARIMA Model Error: {e}")
                return None, None, None, None

        df_filtered, pred_mean, pred_ci, pred_index = train_arima(postal_code_selected)

        if df_filtered is not None:
            fig_arima, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_filtered.index, df_filtered["quantity"], label="Actual Demand")
            ax.plot(pred_index, pred_mean, label="Predicted Demand", linestyle="dashed", color="red")
            ax.fill_between(pred_index, pred_ci.iloc[:, 0], pred_ci.iloc[:, 1], color='gray', alpha=0.3)
            ax.set_title(f"Hamper Demand Forecast for {postal_code_selected}")
            ax.legend()
            st.pyplot(fig_arima)

        # 📊 Decomposition Plot (Trend, Seasonality, Residuals)
        st.subheader("📊 Time Series Decomposition")
        
        if len(df_filtered) >= 24:
            decomposition = sm.tsa.seasonal_decompose(df_filtered["quantity"], model="additive", period=12)
            fig_dec, axes = plt.subplots(3, 1, figsize=(10, 8))
            decomposition.trend.plot(ax=axes[0], title="Trend")
            decomposition.seasonal.plot(ax=axes[1], title="Seasonality")
            decomposition.resid.plot(ax=axes[2], title="Residuals")
            st.pyplot(fig_dec)

    except Exception as e:
        st.error(f"⚠️ Error processing the file: {e}")

else:
    st.warning("⚠️ Please upload a processed CSV file to proceed.")

