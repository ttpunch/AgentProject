import pandas as pd
import numpy as np
from typing import Dict, List, Any, Union
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from statsmodels.tsa.api import VAR
from langchain_core.messages import HumanMessage
from connectors.mongo_connector import MongoConnector
import json
import re
import textwrap

class DataScienceAgent:
    def __init__(self, llm):
        self.llm = llm

    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the Data Science Agent.
        Decides which analysis to run based on the question.
        """
        print("--- Data Science Agent ---")
        question = state["question"]
        chat_history = state.get("chat_history", [])
        
        # Determine analysis type
        analysis_type = self._determine_analysis_type(question, chat_history)
        print(f"DEBUG: Analysis Type: {analysis_type}")
        
        machine_id = self._extract_machine_id(question)
        if not machine_id:
             # If no machine ID, try to infer or ask for it. For now, default to CNC-001 if testing, or return error.
             # Better to return error.
             if "CNC" in question.upper():
                 # Try harder regex
                 match = re.search(r"(CNC-\d{3})", question, re.IGNORECASE)
                 if match:
                     machine_id = match.group(1).upper()
        
        if not machine_id:
            return {"final_answer": "I need a specific Machine ID (e.g., CNC-001) to perform this analysis."}

        # Fetch Data
        df = self._fetch_data(machine_id)
        if df.empty:
            return {"final_answer": f"No data found for {machine_id}."}

        # Execute Analysis
        if analysis_type == "ANOMALY":
            return self._run_anomaly_detection(df, machine_id)
        elif analysis_type == "RUL":
            return self._run_rul_prediction(df, machine_id)
        elif analysis_type == "FORECAST":
            return self._run_forecasting(df, machine_id)
        else:
            return {"final_answer": "I'm not sure which advanced analysis to run. I can do Anomaly Detection, RUL Prediction, or Forecasting."}

    def _determine_analysis_type(self, question: str, chat_history: List[Dict[str, str]] = []) -> str:
        prompt = f"""
        Classify the user's request into one of these categories:
        1. ANOMALY: Questions about "anomalies", "outliers", "weird behavior", "unusual".
        2. RUL: Questions about "remaining useful life", "how long until failure", "RUL", "time to breakdown".
        3. FORECAST: Questions about "future values", "predict temperature", "what will happen next", "forecast".
        
        Chat History:
        {chat_history}
        
        Question: {question}
        
        Return ONLY the category name.
        """
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip().upper()

    def _extract_machine_id(self, question: str) -> str:
        match = re.search(r"(CNC-\d{3})", question, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def _fetch_data(self, machine_id: str = None, limit: int = 500) -> pd.DataFrame:
        from connectors.mongo_connector import MongoConnector
        from connectors.postgres_connector import PostgresConnector
        
        mongo_df = pd.DataFrame()
        pg_df = pd.DataFrame()
        
        # Fetch from MongoDB
        mongo = MongoConnector()
        try:
            match_stage = {}
            if machine_id:
                match_stage = {"machine_id": machine_id}
            
            pipeline = []
            if match_stage:
                pipeline.append({"$match": match_stage})
                
            pipeline.extend([
                {"$sort": {"timestamp": -1}},
                {"$limit": limit},
                {"$sort": {"timestamp": 1}}
            ])
            
            mongo_df = mongo.aggregate("sensor_logs", pipeline)
            if not mongo_df.empty:
                mongo_df['timestamp'] = pd.to_datetime(mongo_df['timestamp'])
                if '_id' in mongo_df.columns:
                    mongo_df = mongo_df.drop(columns=['_id'])
        except Exception as e:
            print(f"Error fetching from MongoDB: {e}")
        finally:
            mongo.close()

        # Fetch from Postgres
        pg = PostgresConnector()
        try:
            query = "SELECT * FROM sensor_data"
            if machine_id:
                query += f" WHERE machine_id = '{machine_id}'"
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            pg_df = pg.fetch_query(query)
            if not pg_df.empty:
                pg_df['timestamp'] = pd.to_datetime(pg_df['timestamp'])
        except Exception as e:
            print(f"Error fetching from Postgres: {e}")
        finally:
            pg.close()

        # Combine DataFrames
        combined_df = pd.concat([mongo_df, pg_df], ignore_index=True)
        
        if not combined_df.empty:
             # Sort combined data
             combined_df = combined_df.sort_values(by='timestamp')
             
        return combined_df

    def _run_anomaly_detection(self, df: pd.DataFrame, machine_id: str) -> Dict[str, Any]:
        # Features
        # Features
        features = ['vibration', 'temperature', 'pressure']
        
        # Ensure all features exist
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0.0 # Default value if missing
                
        X = df[features].values
        
        # Isolation Forest
        iso_forest = IsolationForest(contamination=0.05, random_state=42)
        df['anomaly'] = iso_forest.fit_predict(X)
        
        # -1 is anomaly, 1 is normal
        anomalies = df[df['anomaly'] == -1]
        num_anomalies = len(anomalies)
        
        # Prepare Chart Data (Scatter plot of anomalies)
        # We'll return the full dataset but marked
        chart_data = df.copy()
        chart_data['timestamp'] = chart_data['timestamp'].astype(str)
        chart_data_list = chart_data.to_dict(orient='records')
        
        summary = f"""
        **Anomaly Detection Report for {machine_id}**
        
        - **Model**: Isolation Forest (Unsupervised)
        - **Data Points Analyzed**: {len(df)}
        - **Anomalies Detected**: {num_anomalies}
        
        The chart below highlights the anomalous points in red.
        """
        
        return {
            "final_answer": summary,
            "chart_data": chart_data_list,
            "chart_type": "scatter_anomaly" # Custom type for frontend
        }

    def _run_rul_prediction(self, df: pd.DataFrame, machine_id: str) -> Dict[str, Any]:
        # Simplified RUL using Random Forest
        # We need a target variable. Since we don't have historical failure data in this simple setup,
        # we will simulate a "Health Index" based on vibration and temp, and predict that.
        # In a real scenario, we'd train on run-to-failure datasets.
        
        # Synthetic Health Index (0 to 100, where 0 is failed)
        # Assume max vibration 100 is failure, max temp 200 is failure.
        # This is a heuristic for demonstration.
        
        df['health_index'] = 100 - (df['vibration'] * 0.5 + df['temperature'] * 0.2)
        
        features = ['vibration', 'temperature', 'pressure']
        
        # Ensure all features exist
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0.0

        X = df[features].values
        y = df['health_index'].values
        
        # Train Random Forest
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X[:-1], y[:-1]) # Train on all but last
        
        current_health = rf.predict([X[-1]])[0]
        
        # Estimate RUL based on degradation rate
        # Calculate slope of health index over last 50 points
        recent_df = df.tail(50)
        slope = np.polyfit(range(len(recent_df)), recent_df['health_index'], 1)[0]
        
        if slope >= 0:
            rul_msg = "Stable (Infinite)"
        else:
            # Days to reach 0
            steps_to_failure = (0 - current_health) / slope
            # Assuming 1 step = 1 minute (based on data freq)
            days = steps_to_failure / (60 * 24)
            rul_msg = f"{days:.1f} days"

        summary = f"""
        **RUL Prediction for {machine_id}**
        
        - **Model**: Random Forest Regressor (Health Index Estimation)
        - **Current Health Index**: {current_health:.1f} / 100
        - **Degradation Trend**: {slope:.4f} health points/min
        - **Estimated RUL**: **{rul_msg}**
        """
        
        return {"final_answer": summary}

    def _run_forecasting(self, df: pd.DataFrame, machine_id: str) -> Dict[str, Any]:
        # VAR Model for multivariate forecasting
        features = ['vibration', 'temperature', 'pressure']
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0.0
                
        data = df[features]
        
        model = VAR(data)
        results = model.fit(5) # Lag order
        
        # Forecast next 60 steps (1 hour)
        lag_order = results.k_ar
        forecast_input = data.values[-lag_order:]
        fc = results.forecast(y=forecast_input, steps=60)
        
        # Create Forecast DataFrame
        last_time = df['timestamp'].iloc[-1]
        forecast_index = pd.date_range(start=last_time, periods=61, freq='T')[1:]
        
        fc_df = pd.DataFrame(fc, index=forecast_index, columns=data.columns)
        
        # Prepare Chart Data: Combine History + Forecast
        # We'll just show the forecast for clarity, or append it.
        # Let's return just the forecast for a "Future View"
        
        fc_df['timestamp'] = fc_df.index.astype(str)
        fc_df['type'] = 'forecast'
        
        # Get recent history for context
        history_df = df.tail(60).copy()
        history_df['timestamp'] = history_df['timestamp'].astype(str)
        history_df['type'] = 'history'
        
        combined_df = pd.concat([history_df, fc_df])
        chart_data = combined_df.to_dict(orient='records')
        
        summary = f"""
        **1-Hour Forecast for {machine_id}**
        
        - **Model**: Vector Autoregression (VAR)
        - **Variables**: Vibration, Temperature, Pressure
        - **Horizon**: 60 minutes
        
        The chart shows the predicted trends.
        """
        
        return {
            "final_answer": summary,
            "chart_data": chart_data,
            "chart_type": "forecast"
        }

    def determine_next_step(self, state: Dict[str, Any]) -> str:
        """
        Decides whether to use Spark (Big Data) or Pandas (Real-time/Complex Models).
        """
        question = state["question"]
        chat_history = state.get("chat_history", [])
        
        prompt = f"""
        Classify the user's request into one of these engines:
        1. SPARK: If the user mentions "Spark", "Big Data", "Batch", "Hadoop", "Cluster", or requests heavy aggregation like "monthly stats", "yearly average", "count all".
        2. PANDAS: For standard requests like "Anomaly Detection", "RUL", "Forecast", "Real-time", "Predict", "Outliers".
        
        Chat History:
        {chat_history}
        
        Question: {question}
        
        Return ONLY the engine name: SPARK or PANDAS.
        """
        response = self.llm.invoke([HumanMessage(content=prompt)])
        decision = response.content.strip().upper()
        
        if "SPARK" in decision:
            return "spark_engine"
        else:
            return "pandas_engine"

    def run_spark_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes heavy data analysis using Apache Spark.
        """
        print("--- Spark Engine ---")
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, avg, min, max, count
        
        question = state["question"]
        chat_history = state.get("chat_history", [])
        machine_id = self._extract_machine_id(question)
        
        # Initialize Spark (Local Mode for this demo)
        spark = SparkSession.builder \
            .appName("Agent_Spark_Analysis") \
            .config("spark.driver.memory", "1g") \
            .getOrCreate()
            
        try:
            # Fetch data from Mongo (Simulated by fetching to Pandas first then creating Spark DF)
            # In production, use Mongo-Spark connector directly.
            pdf = self._fetch_data(machine_id, limit=10000) # Fetch more data for Spark
            if pdf.empty:
                target_msg = machine_id if machine_id else "any machine"
                return {"final_answer": f"No data found for {target_msg} to run Spark analysis."}
                
            sdf = spark.createDataFrame(pdf)
            sdf.createOrReplaceTempView("sensor_data")
            
            # 1. Get Schema
            schema_str = "\n".join([f"{f.name}: {f.dataType}" for f in sdf.schema.fields])
            
            # 2. Generate SQL via LLM
            sql_prompt = f"""
            You are a Spark SQL expert. Write a SQL query to answer the user's question based on the schema below.
            
            Table: sensor_data
            Schema:
            {schema_str}
            
            Chat History:
            {chat_history}
            
            Question: {question}
            
            Rules:
            - Return ONLY the SQL query. No markdown, no explanations.
            - Use standard Spark SQL syntax.
            - If the question is vague, select the top 10 records.
            """
            
            sql_response = self.llm.invoke([HumanMessage(content=sql_prompt)])
            sql_query = sql_response.content.strip().replace("```sql", "").replace("```", "").strip()
            print(f"DEBUG: Generated SQL: {sql_query}")
            
            # 3. Execute SQL
            result_df = spark.sql(sql_query)
            
            # 4. Format Results
            num_partitions = sdf.rdd.getNumPartitions()
            results = result_df.limit(20).collect() # Limit to avoid blowing up context
            columns = result_df.columns
            
            # --- Chart Generation Logic ---
            chart_data = []
            chart_type = None
            
            # Heuristic: If we have timestamp + numbers -> Line Chart
            # If we have string (category) + numbers -> Bar Chart
            
            has_timestamp = any('timestamp' in col.lower() or 'date' in col.lower() for col in columns)
            numeric_cols = [c for c in columns if 'avg' in c or 'count' in c or 'sum' in c or 'max' in c or 'min' in c or 'vibration' in c or 'temperature' in c or 'pressure' in c]
            
            if results:
                # Convert Row objects to dicts
                chart_data = [row.asDict() for row in results]
                
                # Ensure JSON serializable (handle dates/decimals)
                for item in chart_data:
                    for k, v in item.items():
                        if hasattr(v, 'isoformat'): # Date/Time
                            item[k] = v.isoformat()
                        elif hasattr(v, '__str__'): # Decimal or other objects
                             item[k] = str(v)

                if has_timestamp and numeric_cols:
                    chart_type = "line"
                elif numeric_cols:
                    chart_type = "bar"
            
            # Convert to Markdown Table
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"
            rows = []
            for row in results:
                row_str = "| " + " | ".join([str(row[col]) for col in columns]) + " |"
                rows.append(row_str)
            
            table_str = "\n".join([header, separator] + rows)
            
            summary = textwrap.dedent(f"""
            **Spark Dynamic Analysis Report**
            
            - **Engine**: Apache Spark 3.5.0 (Local)
            - **Partitions Used**: {num_partitions}
            - **Executed Query**: `{sql_query}`
            
            ### Results
            {table_str}
            """)
            
            return {
                "final_answer": summary,
                "chart_data": chart_data,
                "chart_type": chart_type
            }
            
        except Exception as e:
            return {"final_answer": f"Spark Analysis Failed: {str(e)}"}
        finally:
            spark.stop()

    def run_pandas_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes standard analysis using Pandas/Scikit-Learn.
        """
        return self.analyze(state)
