import streamlit as st
import pandas as pd
import io

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

def load_and_clean_files(verif_file, short_term_file, new_working_file):
    df_verif = pd.read_excel(verif_file)
    df_short = pd.read_csv(short_term_file)
    df_new = pd.read_csv(new_working_file)

    # Clean and standardize
    df_verif["PHONE_CLEAN"] = df_verif["Verified Phone Number"].apply(clean_phone)
    df_verif["ID_CLEAN"] = df_verif["Verified ID Number"].astype(str).str.strip()

    df_short["PHONE_CLEAN"] = df_short["PARTICIPANT PHONE"].apply(clean_phone)
    df_short["ID_CLEAN"] = df_short["ID"].astype(str).str.strip()
    df_short["SOURCE"] = "Short Term"

    df_new["PHONE_CLEAN"] = df_new["PARTICIPANT PHONE"].apply(clean_phone)
    df_new["ID_CLEAN"] = df_new["ID"].astype(str).str.strip()
    df_new["SOURCE"] = "New Working"

    return df_verif, df_short, df_new

def match_and_tag(df_verif, df_short, df_new):
    combined = pd.concat([df_short, df_new], ignore_index=True)
    combined = combined.drop_duplicates(subset=["ID_CLEAN", "PHONE_CLEAN"])

    combined["VERIFIED"] = combined["ID_CLEAN"].isin(df_verif["ID_CLEAN"])
    not_verified = combined[~combined["VERIFIED"]]
    phone_matches = not_verified["PHONE_CLEAN"].isin(df_verif["PHONE_CLEAN"])
    combined.loc[not_verified[phone_matches].index, "VERIFIED"] = True

    return combined

def to_excel_download(df, label):
    towrite = io.BytesIO()
    df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    st.download_button(
        label=f"Download {label} as Excel",
        data=towrite,
        file_name=f"{label.replace(' ', '_')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

st.title("Jiinue Verification Checker")

verif_file = st.file_uploader("Upload Business Verifications Excel", type="xlsx")
short_term_file = st.file_uploader("Upload Short Term Working Capital CSV", type="csv")
new_working_file = st.file_uploader("Upload New Working Capital CSV", type="csv")

if verif_file and short_term_file and new_working_file:
    df_verif, df_short, df_new = load_and_clean_files(verif_file, short_term_file, new_working_file)
    result = match_and_tag(df_verif, df_short, df_new)

    st.success("✅ Matching Complete")
    st.dataframe(result.head(50))

    verified = result[result["VERIFIED"] == True]
    not_verified = result[result["VERIFIED"] == False]

    st.subheader("📄 Verified Participants")
    st.write(f"Total: {len(verified)}")
    to_excel_download(verified, "Verified Participants")

    st.subheader("📄 Not Verified Participants")
    st.write(f"Total: {len(not_verified)}")
    to_excel_download(not_verified, "Not Verified Participants")
