# app.py

import pandas as pd
import streamlit as st
import io

st.set_page_config(page_title="Verification Tracker", layout="wide")
st.title("📊 Business Verification Dashboard")

verif_file = st.file_uploader("Upload Business Verifications (Excel)", type=["xlsx"])
short_file = st.file_uploader("Upload Short Term Working Capital (CSV)", type=["csv"])
new_file = st.file_uploader("Upload New Working Capital (CSV)", type=["csv"])

if verif_file and short_file and new_file:
    df_verif = pd.read_excel(verif_file)
    df_short = pd.read_csv(short_file)
    df_new = pd.read_csv(new_file)

    def clean_phone(p):
        if pd.isna(p): return ""
        p = str(p).strip().replace(" ", "").replace("+", "")
        if p.startswith("07"): return "254" + p[1:]
        elif p.startswith("7") and len(p) == 9: return "254" + p
        elif p.startswith("254") and len(p) == 12: return p
        return p

    df_verif["PHONE_CLEAN"] = df_verif["Verified Phone Number"].apply(clean_phone)
    df_verif["ID_CLEAN"] = df_verif["Verified ID Number"].astype(str).str.strip()
    df_verif = df_verif.drop_duplicates(subset=["ID_CLEAN", "PHONE_CLEAN"])

    logs = {}
    performance = {}

    def process(df_src, label):
        df = df_src.copy()
        df["PHONE_CLEAN"] = df["PARTICIPANT PHONE"].apply(clean_phone)
        df["ID_CLEAN"] = df["ID"].astype(str).str.strip()
        df["COUNTY"] = df["COUNTY"].astype(str).str.upper()

        df["VERIFIED"] = False
        df["MATCH_METHOD"] = "None"
        df["REASON"] = "No match on ID or Phone"

        # Match by ID
        id_match = df["ID_CLEAN"].isin(df_verif["ID_CLEAN"])
        df.loc[id_match, "VERIFIED"] = True
        df.loc[id_match, "MATCH_METHOD"] = "ID"
        df.loc[id_match, "REASON"] = "Matched by ID"

        # Match by Phone
        unmatched = df[~df["VERIFIED"]]
        phone_match = unmatched["PHONE_CLEAN"].isin(df_verif["PHONE_CLEAN"])
        df.loc[unmatched[phone_match].index, "VERIFIED"] = True
        df.loc[unmatched[phone_match].index, "MATCH_METHOD"] = "Phone"
        df.loc[unmatched[phone_match].index, "REASON"] = "Matched by Phone"

        # Merge with Verification Data (only matched)
        matched = df[df["VERIFIED"]].merge(
            df_verif,
            how="left",
            left_on=["ID_CLEAN", "PHONE_CLEAN"],
            right_on=["ID_CLEAN", "PHONE_CLEAN"]
        )

        # Clean extra blank rows if any
        matched = matched.dropna(subset=["Name of the Participant", "Verified ID Number", "Verified Phone Number"])

        logs[label] = matched

        # County Performance Summary
        perf = df.groupby("COUNTY").agg(
            Assigned=("ID", "count"),
            Verified=("VERIFIED", "sum")
        ).reset_index()
        perf["% Verified"] = (perf["Verified"] / perf["Assigned"] * 100).round(1)
        performance[label] = perf

        return {
            "Dataset": label,
            "Total Assigned": len(df),
            "Verified": df["VERIFIED"].sum(),
            "Matched by ID": (df["MATCH_METHOD"] == "ID").sum(),
            "Matched by Phone": (df["MATCH_METHOD"] == "Phone").sum(),
            "Not Verified": (~df["VERIFIED"]).sum()
        }

    # Run summaries
    summary_df = pd.DataFrame([
        process(df_short, "Short Term"),
        process(df_new, "New Working")
    ])

    st.subheader("📄 High-Level Summary")
    st.dataframe(summary_df)

    st.subheader("📊 County Performance")
    for label, perf_df in performance.items():
        st.markdown(f"**{label}**")
        st.dataframe(perf_df)

    # Download Summary Report
    summary_buffer = io.BytesIO()
    with pd.ExcelWriter(summary_buffer, engine="xlsxwriter") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        for label, perf_df in performance.items():
            perf_df.to_excel(writer, sheet_name=label[:31], index=False)
    st.download_button("📥 Download Summary Report",
                       data=summary_buffer.getvalue(),
                       file_name="Verification_Summary_Report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Download Verified Logs
    for label, log_df in logs.items():
        log_buffer = io.BytesIO()
        log_df.to_excel(log_buffer, index=False)
        st.download_button(
            label=f"📥 Download {label} Verified Log (With Verification Columns)",
            data=log_buffer.getvalue(),
            file_name=f"{label.replace(' ', '_')}_Verification_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
