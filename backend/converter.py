import pandas as pd
import json
import os
import math

def convert_excel_to_json(input_file, output_file):
    print(f"Loading: {input_file}")
    
    # Read Excel, keep all columns as object to avoid automatic float conversion
    df = pd.read_excel(input_file, dtype=object)
    print(f"Loaded rows: {len(df)}")
    
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    
    # Fill NaN with None
    df = df.where(pd.notnull(df), None)
    
    # Convert numeric strings to int/float where appropriate
    numeric_cols = ['Targets', 'Quarter_1', 'Quarter_2', 'Quarter_3', 'Quarter_4', 'Fiscal_Year']
    for col in numeric_cols:
        if col in df.columns:
            def safe_numeric(x):
                if x is None:
                    return None
                try:
                    val = float(x)
                    if math.isnan(val):
                        return None
                    # Convert whole numbers to int
                    if val.is_integer():
                        return int(val)
                    return val
                except:
                    return None
            df[col] = df[col].apply(safe_numeric)
    
    # Force Mechanism_Code to string if present
    if 'Mechanism_Code' in df.columns:
        def safe_mech(x):
            if x is None:
                return None
            try:
                val = float(x)
                if math.isnan(val):
                    return None
                return str(int(val))
            except:
                return str(x)
        df['Mechanism_Code'] = df['Mechanism_Code'].apply(safe_mech)
    
    # Convert DataFrame to JSON-compatible dict
    data = df.to_dict(orient='records')

    # Ensure all NaN are converted to None in final JSON
    def fix_nan(d):
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d

    data = [fix_nan(row) for row in data]
    
    # Save JSON
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"JSON saved to: {output_file}")

if __name__ == "__main__":
    convert_excel_to_json("data/Mechanisms_Data.xlsx", "json/mech.json")
