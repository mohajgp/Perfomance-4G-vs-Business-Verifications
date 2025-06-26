import pandas as pd
import streamlit as st
import io

# === Streamlit App Setup ===
st.set_page_config(page_title="Business Verification Dashboard", layout="wide")
st.title("📊 Jiinue Business Verification Performance Dashboard")

# === File Upload ===
verif_file = st.file_uploader("Upload Business Verifications File (Excel)", type=["xlsx"])
short_term_file = st.file_uploader("Upload Short Term Working Capital File (CSV)", type=["csv"])
new_working_file = st.file_uploader("Upload New Working Capital File (CSV)", type=["csv"])

if verif_file and short_term_file and new_working_file:
    # === Load Files ===
    df_verif = pd.read_excel(verif_file)
    df_short = pd.read_csv(short_term_file)
    df_new = pd.read_csv(new_working_file)

    # === Clean Phone Numbers ===
    def clean_phone(phone):
        if pd.isna(phone):
            return ""
        phone = str(phone).strip().replace(" ", "").replace("+", "")
        if phone.startswith("07"):
            return "254" + phone[1:]
        elif phone.startswith("7") and len(phone) == 9:
            return "254" + phone
        elif phone.startswith("254") and len(phone) == 12:
            return phone
        return phone

    # === Prepare Verification Data ===
    df_verif["PHONE_CLEAN"] = df_verif["Verified Phone Number"].apply(clean_phone)
    df_verif["ID_CLEAN"] = df_verif["Verified ID Number"].astype(str).str.strip()
    df_verif = df_verif.drop_duplicates(subset=["ID_CLEAN", "PHONE_CLEAN"])

    match_log = {"Matched by ID": 0, "Matched by Phone": 0}

    def process_dataset(df_source, source_label):
        df = df_source.copy()
        df["PHONE_CLEAN"] = df["PARTICIPANT PHONE"].apply(clean_phone)
        df["ID_CLEAN"] = df["ID"].astype(str).str.strip()
        df["SOURCE"] = source_label
        df["COUNTY"] = df["COUNTY"].astype(str).str.upper()

        # Match by ID
        df["VERIFIED"] = df["ID_CLEAN"].isin(df_verif["ID_CLEAN"])
        match_log["Matched by ID"] += df["VERIFIED"].sum()

        # Fallback to phone
        not_verified = df[~df["VERIFIED"]]
        phone_match = not_verified["PHONE_CLEAN"].isin(df_verif["PHONE_CLEAN"])
        df.loc[not_verified[phone_match].index, "VERIFIED"] = True
        match_log["Matched by Phone"] += phone_match.sum()

        return df

    df_short_proc = process_dataset(df_short, "Short Term")
    df_new_proc = process_dataset(df_new, "New Working")
    df_all = pd.concat([df_short_proc, df_new_proc], ignore_index=True)

    # === County-level Aggregation ===
    def summarize_by_county(df, label):
        summary = df.groupby("COUNTY").agg(
            Assigned=(label, "count"),
            Verified=("VERIFIED", "sum")
        ).reset_index()
        summary["% Verified"] = (summary["Verified"] / summary["Assigned"] * 100).round(1)
        return summary

    short_summary = summarize_by_county(df_short_proc, "SOURCE")
    new_summary = summarize_by_county(df_new_proc, "SOURCE")

    # === Dashboard Output ===
    st.header("📍 County-Level Verification Summary")

    st.subheader("Short Term Working Capital")
    st.dataframe(short_summary)

    st.subheader("New Working Capital")
    st.dataframe(new_summary)

    st.header("🔍 Match Method Breakdown")
    total_matches = match_log["Matched by ID"] + match_log["Matched by Phone"]
    st.markdown(f"""
    - ✅ Matched by ID: **{match_log['Matched by ID']}**
    - 📞 Matched by Phone: **{match_log['Matched by Phone']}**
    - 🧮 Total Verified Matches: **{total_matches}**
    """)

    # === Export Full Combined Report ===
    buffer = io.BytesIO()
    df_all.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Download Full Combined Report (with verification flags)",
        data=buffer,
        file_name="Combined_Verification_Status_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
