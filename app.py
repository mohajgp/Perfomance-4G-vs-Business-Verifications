import pandas as pd
import streamlit as st
import io

st.set_page_config(page_title="Verification Summary", layout="wide")
st.title("📊 Business Verification Summary + Match Reasons")

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

    def summarize(source_df, label):
        df = source_df.copy()
        df["PHONE_CLEAN"] = df["PARTICIPANT PHONE"].apply(clean_phone)
        df["ID_CLEAN"] = df["ID"].astype(str).str.strip()

        df["VERIFIED"] = False
        df["MATCH_METHOD"] = "None"
        df["REASON"] = "No match on ID or Phone"

        id_match = df["ID_CLEAN"].isin(df_verif["ID_CLEAN"])
        df.loc[id_match, "VERIFIED"] = True
        df.loc[id_match, "MATCH_METHOD"] = "ID"
        df.loc[id_match, "REASON"] = "Matched by ID"

        unmatched = df[~df["VERIFIED"]]
        phone_match = unmatched["PHONE_CLEAN"].isin(df_verif["PHONE_CLEAN"])
        df.loc[unmatched[phone_match].index, "VERIFIED"] = True
        df.loc[unmatched[phone_match].index, "MATCH_METHOD"] = "Phone"
        df.loc[unmatched[phone_match].index, "REASON"] = "Matched by Phone"

        total = len(df)
        verified = df["VERIFIED"].sum()
        id_matches = (df["MATCH_METHOD"] == "ID").sum()
        phone_matches = (df["MATCH_METHOD"] == "Phone").sum()
        not_verified = total - verified

        logs[label] = df

        return {
            "Dataset": label,
            "Total Assigned": total,
            "Verified": verified,
            "Matched by ID": id_matches,
            "Matched by Phone": phone_matches,
            "Not Verified": not_verified
        }

    summary_data = [summarize(df_short, "Short Term"), summarize(df_new, "New Working")]
    summary_df = pd.DataFrame(summary_data)

    st.subheader("📄 High-Level Summary")
    st.dataframe(summary_df)

    # Download Summary
    summary_buffer = io.BytesIO()
    summary_df.to_excel(summary_buffer, index=False)
    st.download_button("📥 Download Summary Report",
                       data=summary_buffer,
                       file_name="Verification_Summary_Report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Download per-source log files
    for label, log_df in logs.items():
        log_buffer = io.BytesIO()
        log_df.to_excel(log_buffer, index=False)
        st.download_button(
            label=f"📥 Download {label} Verification Log with Reasons",
            data=log_buffer,
            file_name=f"{label.replace(' ', '_')}_Verification_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
