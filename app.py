import streamlit as str
import sqlite3
import pandas as pd
import datetime
import random

# Configure Page Layout
str.set_page_config(page_title="MOT Compliance Engine", layout="wide")

# ==========================================
# DATABASE LAYER
# ==========================================
DB_NAME = "mot_system.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes schema and seeds baseline evaluation criteria."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Vehicle Records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                reg_number TEXT PRIMARY KEY,
                make TEXT,
                model TEXT,
                year INTEGER,
                mileage INTEGER
            )
        ''')
        
        # Testing Thresholds
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS criteria (
                component TEXT PRIMARY KEY,
                threshold REAL,
                condition TEXT
            )
        ''')
        
        # MOT Master Records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mot_tests (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_number TEXT,
                test_date TEXT,
                status TEXT,
                FOREIGN KEY(reg_number) REFERENCES vehicles(reg_number)
            )
        ''')
        
        # Seed core parameters if empty
        cursor.execute("SELECT COUNT(*) FROM criteria")
        if cursor.fetchone()[0] == 0:
            standards = [
                ('Tire Tread Depth (mm)', 1.6, 'greater_than'),
                ('Brake Efficiency (%)', 50.0, 'greater_than'),
                ('Carbon Monoxide (CO %)', 0.2, 'less_than'),
                ('Hydrocarbons (HC ppm)', 200.0, 'less_than')
            ]
            cursor.executemany("INSERT INTO criteria VALUES (?, ?, ?)", standards)
        conn.commit()

init_db()

# ==========================================
# DATA SCIENCE SEEDING ENGINE (SYNTHETIC DATA)
# ==========================================
def seed_synthetic_data(num_records=200):
    """Generates bulk vehicle history data for analytical depth."""
    makes = ["Maruti Suzuki", "Hyundai", "Tata", "Mahindra", "Honda"]
    models = {"Maruti Suzuki": ["Swift", "Baleno"], "Hyundai": ["i20", "Creta"], 
              "Tata": ["Nexon", "Altroz"], "Mahindra": ["XUV300", "Thar"], "Honda": ["City", "Amaze"]}
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Clear old testing datasets to avoid inflation
        cursor.execute("DELETE FROM mot_tests")
        cursor.execute("DELETE FROM vehicles")
        
        for i in range(num_records):
            reg = f"DL-{random.randint(10,99)}-C-{random.randint(1000,9999)}"
            make = random.choice(makes)
            model = random.choice(models[make])
            year = random.randint(2012, 2024)
            mileage = random.randint(5000, 150000)
            
            cursor.execute("INSERT OR IGNORE INTO vehicles VALUES (?, ?, ?, ?, ?)", (reg, make, model, year, mileage))
            
            # Formulate failure logic tied back to vehicle age
            age = 2026 - year
            fail_chance = min(0.1 + (age * 0.07), 0.85) # Older vehicles yield a higher failure rate
            
            status = "FAIL" if random.random() < fail_chance else "PASS"
            test_date = (datetime.date.today() - datetime.timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
            
            cursor.execute("INSERT INTO mot_tests (reg_number, test_date, status) VALUES (?, ?, ?)", (reg, test_date, status))
        conn.commit()

# ==========================================
# INTERACTIVE APPLICATION FRONTEND
# ==========================================
str.title("🛡️ Vehicle MOT Compliance & Analytics Engine")
str.markdown("An implementation evaluating UK Ministry of Transport evaluation models adapted for Indian transport standards.")

# System Navigation Tabs
tab1, tab2, tab3 = str.tabs(["📊 Analytics Dashboard", "🚗 Run Compliance Test", "⚙️ Database Management"])

# --- TAB 1: DATA SCIENCE ANALYTICS ---
with tab1:
    str.header("Fleet Compliance Analysis")
    
    with get_db_connection() as conn:
        df_vehicles = pd.read_sql_query("SELECT * FROM vehicles", conn)
        df_tests = pd.read_sql_query("SELECT * FROM mot_tests", conn)
    
    if df_tests.empty:
        str.warning("The analytical database is currently empty. Head over to the Database Management tab to seed test data.")
    else:
        df_merged = pd.merge(df_tests, df_vehicles, on="reg_number")
        df_merged['Vehicle Age'] = 2026 - df_merged['year']
        
        # High Level KPIs
        col1, col2, col3 = str.columns(3)
        total_tested = len(df_merged)
        pass_rate = (len(df_merged[df_merged['status'] == 'PASS']) / total_tested) * 100
        
        col1.metric("Total Evaluated Vehicles", f"{total_tested}")
        col2.metric("Overall Pass Rate", f"{pass_rate:.1f}%")
        col3.metric("Average Vehicle Age", f"{df_merged['Vehicle Age'].mean():.1f} Years")
        
        str.markdown("---")
        
        # Visualization Columns
        v_col1, v_col2 = str.columns(2)
        
        with v_col1:
            str.subheader("Compliance Yield by Brand")
            brand_metrics = df_merged.groupby(['make', 'status']).size().unstack(fill_value=0)
            str.bar_chart(brand_metrics)
            
        with v_col2:
            str.subheader("Failure Probability vs. Vehicle Age")
            age_analysis = df_merged.groupby('Vehicle Age')['status'].value_counts(normalize=True).unstack(fill_value=0) * 100
            if 'FAIL' in age_analysis.columns:
                str.line_chart(age_analysis['FAIL'])
            else:
                str.info("No failure metrics present to chart.")

# --- TAB 2: INTERACTIVE TEST BENCH ---
with tab2:
    str.header("Real-Time Inspections Setup")
    
    col_v1, col_v2 = str.columns(2)
    with col_v1:
        reg_input = str.text_input("Registration Number", "DL-01-CA-9999").upper()
        make_input = str.selectbox("Manufacturer", ["Maruti Suzuki", "Hyundai", "Tata", "Mahindra", "Honda"])
        model_input = str.text_input("Model Variant", "Swift")
    with col_v2:
        year_input = str.number_input("Manufacturing Year", min_value=2000, max_value=2026, value=2020)
        mileage_input = str.number_input("Odometer Reading (km)", min_value=0, value=45000)

    str.markdown("### Telemetry Metrics Evaluation")
    col_m1, col_m2, col_m3, col_m4 = str.columns(4)
    
    with col_m1: t_depth = str.number_input("Tire Tread Depth (mm)", 0.0, 10.0, 2.1, 0.1)
    with col_m2: b_eff = str.number_input("Brake Efficiency (%)", 0.0, 100.0, 58.0, 1.0)
    with col_m3: co_em = str.number_input("Carbon Monoxide (CO %)", 0.0, 5.0, 0.12, 0.01)
    with col_m4: hc_em = str.number_input("Hydrocarbons (HC ppm)", 0.0, 1000.0, 145.0, 5.0)

    if str.button("Execute Compliance Evaluation", type="primary"):
        # Fetch operational standards dynamically
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM criteria")
            criteria_rules = {row['component']: (row['threshold'], row['condition']) for row in cursor.fetchall()}
        
        # Core Rule Verification Logic
        failures = []
        if t_depth <= criteria_rules['Tire Tread Depth (mm)'][0]: failures.append("Tire Tread Depth Deficient")
        if b_eff <= criteria_rules['Brake Efficiency (%)'][0]: failures.append("Brake System Efficiency Critical Fail")
        if co_em >= criteria_rules['Carbon Monoxide (CO %)'][0]: failures.append("Excessive CO Emissions Profile")
        if hc_em >= criteria_rules['Hydrocarbons (HC ppm)'][0]: failures.append("Excessive Hydrocarbon Emissions Profile")
        
        final_status = "FAIL" if failures else "PASS"
        
        # Save structural states into standard records
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO vehicles VALUES (?,?,?,?,?)", 
                           (reg_input, make_input, model_input, year_input, mileage_input))
            cursor.execute("INSERT INTO mot_tests (reg_number, test_date, status) VALUES (?,?,?)", 
                           (reg_input, datetime.date.today().strftime("%Y-%m-%d"), final_status))
            conn.commit()
            
        # Display Results
        if final_status == "PASS":
            str.success(f"✔️ **COMPLIANCE CERTIFIED**: Vehicle {reg_input} meets all functional thresholds.")
        else:
            str.error(f"❌ **COMPLIANCE DENIED**: Vehicle {reg_input} failed evaluation parameters.")
            str.markdown("**Reason(s) for failure:**")
            for fail in failures:
                str.write(f"- {fail}")

# --- TAB 3: SYSTEM CONTROLS ---
with tab3:
    str.header("System Maintenance & Configuration")
    str.write("Manage systemic baselines or simulate synthetic generation modeling sequences below.")
    
    records_to_seed = str.slider("Volume to Generate", 50, 1000, 250)
    if str.button("Populate Random Volumetric Data"):
        seed_synthetic_data(records_to_seed)
        str.success(f"Successfully generated and processed {records_to_seed} vehicle profiles into the analytics database!")
        str.rerun()