import pandas as pd
import streamlit as st
import io

# === Streamlit App Setup ===
st.set_page_config(page_title="Business Verification Tracker", layout="wide")
st.title("📊 Business Verification Tracker: Field Officer Performance")

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

    # === Initialize match counters ===
    stats = {
        "short_term_id": 0,
        "short_term_phone": 0,
        "new_working_id": 0,
        "new_working_phone": 0
    }

    def process_dataset(df_source, source_name):
        df = df_source.copy()
        df["PHONE_CLEAN"] = df["PARTICIPANT PHONE"].apply(clean_phone)
        df["ID_CLEAN"] = df["ID"].astype(str).str.strip()
        df["COUNTY"] = df["COUNTY"].astype(str).str.upper()

        # Match by ID
        df["VERIFIED"] = df["ID_CLEAN"].isin(df_verif["ID_CLEAN"])
        stats[f"{source_name}_id"] = df["VERIFIED"].sum()

        # Match by Phone fallback
        unmatched = df[~df["VERIFIED"]]
        phone_match = unmatched["PHONE_CLEAN"].isin(df_verif["PHONE_CLEAN"])
        df.loc[unmatched[phone_match].index, "VERIFIED"] = True
        stats[f"{source_name}_phone"] = phone_match.sum()

        return df

    # Process each dataset separately
    df_short_verified = process_dataset(df_short, "short_term")
    df_new_verified = process_dataset(df_new, "new_working")

    # === County Aggregation ===
    def summarize(df):
        summary = df.groupby("COUNTY").agg(
            Assigned=("ID", "count"),
            Verified=("VERIFIED", "sum")
        ).reset_index()
        summary["% Verified"] = (summary["Verified"] / summary["Assigned"] * 100).round(1)
        return summary

    short_summary = summarize(df_short_verified)
    new_summary = summarize(df_new_verified)

    # === Display Results ===
    st.header("🧾 County-Level Verification Performance")

    st.subheader("📦 Short Term Working Capital")
    st.dataframe(short_summary)

    st.subheader("💼 New Working Capital")
    st.dataframe(new_summary)

    st.header("📈 Match Breakdown")
    st.markdown(f"""
    ### Short Term:
    - ✅ ID Matches: **{stats['short_term_id']}**
    - 📞 Phone Matches: **{stats['short_term_phone']}**
    - 🧮 Total Verified: **{stats['short_term_id'] + stats['short_term_phone']}**

    ### New Working Capital:
    - ✅ ID Matches: **{stats['new_working_id']}**
    - 📞 Phone Matches: **{stats['new_working_phone']}**
    - 🧮 Total Verified: **{stats['new_working_id'] + stats['new_working_phone']}**
    """)

    # === Downloads ===
    buffer_short = io.BytesIO()
    buffer_new = io.BytesIO()

    df_short_verified.to_excel(buffer_short, index=False)
    df_new_verified.to_excel(buffer_new, index=False)

    st.download_button(
        label="📥 Download Verified Short Term Report",
        data=buffer_short,
        file_name="Verified_Short_Term_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        label="📥 Download Verified New Working Report",
        data=buffer_new,
        file_name="Verified_New_Working_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
