# ===================================================================
# ==                 MASTER CSV COMPILER APPLICATION               ==
# ===================================================================
# This application takes a .zip file containing electoral data,
# finds all '_e_detail.csv' and '_e_sup.csv' pairs, intelligently
# combines them, and produces a single, verified master Excel file.
# ===================================================================

import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile
import io

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Master CSV Compiler"
)

# =============================================================================
# ---                      CORE COMPILATION LOGIC                           ---
# =============================================================================
# (This entire function remains unchanged from your perfect version)
def compile_csv_files_from_zip(uploaded_zip_file):
    """
    Takes an uploaded zip file, extracts it, processes all _e_detail and _e_sup
    files, and compiles them into a single master DataFrame.
    Returns the final DataFrame and a detailed log of the process.
    """
    log_messages = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_messages.append("✔️ Zip file uploaded. Extracting contents...")
        try:
            with zipfile.ZipFile(uploaded_zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            log_messages.append("✔️ Extraction complete.")
        except Exception as e:
            log_messages.append(f"❌ ERROR: Could not extract zip file. Reason: {e}")
            return None, "\n".join(log_messages)

        log_messages.append("\n--- Part 1: Finding and Grouping File Pairs ---")
        file_pairs = {}
        for root, _, filenames in os.walk(temp_dir):
            for filename in filenames:
                if filename.startswith('._'):
                    continue
                
                base_name, file_type = None, None
                if filename.endswith('_e_detail.csv'):
                    base_name, file_type = filename.replace('_e_detail.csv', ''), 'detail'
                elif filename.endswith('_e_sup.csv'):
                    base_name, file_type = filename.replace('_e_sup.csv', ''), 'sup'
                else:
                    continue
                
                if base_name not in file_pairs:
                    file_pairs[base_name] = {}
                file_pairs[base_name][file_type] = os.path.join(root, filename)
        log_messages.append(f"Grouping complete. Found {len(file_pairs)} unique base names to process.")

        log_messages.append("\n--- Part 2: Processing Pairs for Final Compilation ---")
        all_dataframes = []
        source_row_counter = 0
        success_count, skipped_count = 0, 0

        if not file_pairs:
            log_messages.append("❌ No file pairs were found to process.")
            return None, "\n".join(log_messages)

        for base_name, paths in sorted(file_pairs.items()):
            if 'detail' in paths:
                try:
                    detail_df = pd.read_csv(paths['detail'])
                    source_row_counter += len(detail_df)
                    combined_df_for_pair = detail_df
                    
                    if 'sup' in paths:
                        try:
                            sup_df = pd.read_csv(paths['sup'])
                            if not sup_df.empty:
                                source_row_counter += len(sup_df)
                                combined_df_for_pair = pd.concat([detail_df, sup_df], ignore_index=True)
                        except pd.errors.EmptyDataError:
                            pass
                    
                    all_dataframes.append(combined_df_for_pair)
                    log_messages.append(f"  -> Processed: {base_name}")
                    success_count += 1
                except Exception as e:
                    log_messages.append(f"  -> ❌ ERROR processing {base_name}: {e}")
                    skipped_count += 1
            else:
                log_messages.append(f"  -> ⚠️ WARNING: Skipping {base_name} (essential detail file is missing).")
                skipped_count += 1
        
        log_messages.append("\n--- Part 3: Compiling Final Output ---")
        if all_dataframes:
            try:
                master_df = pd.concat(all_dataframes, ignore_index=True)
                final_df_rows = len(master_df)
                
                summary = [
                    "\n" + "="*40, "          PROCESS COMPLETE: SUMMARY", "="*40,
                    f"Total base names processed successfully: {success_count}",
                    f"Total base names skipped or failed:    {skipped_count}",
                    "-" * 40, "Data Integrity Verification:",
                    f"  - Sum of rows from all source files:  {source_row_counter:,}",
                    f"  - Total rows in the final master file:  {final_df_rows:,}", "-" * 40
                ]
                if final_df_rows == source_row_counter:
                    summary.append("✅ VERIFICATION PASSED: The row counts match perfectly.")
                else:
                    mismatch = abs(final_df_rows - source_row_counter)
                    summary.append(f"❌ VERIFICATION FAILED: Mismatch of {mismatch:,} rows detected.")
                summary.append("="*40)
                log_messages.extend(summary)
                
                return master_df, "\n".join(log_messages)
            except Exception as e:
                log_messages.append(f"❌ CRITICAL ERROR during final compilation: {e}")
                return None, "\n".join(log_messages)
        else:
            log_messages.append("No data was successfully processed, so no master file was created.")
            return None, "\n".join(log_messages)

# =============================================================================
# ---                  STREAMLIT USER INTERFACE (REVISED)                   ---
# =============================================================================

### <<< MODIFICATION START: CACHED HELPER FUNCTION >>>
# This function converts the dataframe to Excel. We cache it so that this slow
# operation is not re-run every time the user interacts with the UI.
@st.cache_data
def convert_df_to_excel(df):
    output_buffer = io.BytesIO()
    df.to_excel(output_buffer, index=False, engine='openpyxl')
    return output_buffer.getvalue()
### <<< MODIFICATION END: CACHED HELPER FUNCTION >>>


st.title('📂 Master CSV Compiler')
st.markdown("This tool takes a `.zip` file containing `_e_detail.csv` and `_e_sup.csv` files, combines them into a single master **Excel file**, and verifies the total row count.")

### <<< MODIFICATION START: INITIALIZE SESSION STATE >>>
# We initialize session state variables to hold the results.
# This prevents them from being lost when the script re-runs.
if 'log_text' not in st.session_state:
    st.session_state.log_text = ""
if 'master_df' not in st.session_state:
    st.session_state.master_df = None
### <<< MODIFICATION END: INITIALIZE SESSION STATE >>>


uploaded_csv_zip = st.file_uploader("Upload Your Zipped CSV Data", type="zip")

if st.button('🚀 Start Compilation', type="primary", disabled=(not uploaded_csv_zip)):
    with st.spinner('Processing... This may take a moment.'):
        # The button's only job is to run the compilation and store results in state
        df, log = compile_csv_files_from_zip(uploaded_csv_zip)
        st.session_state.master_df = df
        st.session_state.log_text = log

### <<< MODIFICATION START: RESULTS DISPLAY BLOCK >>>
# This block is now separate from the button. It checks the session state
# on EVERY script re-run and displays the results if they exist.
if st.session_state.log_text:
    st.header("📊 Results")
    st.text_area("Processing Log", st.session_state.log_text, height=400)
    
    if st.session_state.master_df is not None:
        st.success("Compilation successful!")
        st.dataframe(st.session_state.master_df.head(10))
        
        # Call the cached function to get the excel data
        excel_data = convert_df_to_excel(st.session_state.master_df)
        
        st.download_button(
            label="📥 Download Master Excel File",
            data=excel_data,
            file_name="master_compiled_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
# This is the initial state before the button is pressed
else:
    st.info("Please upload a CSV zip file to begin the compilation process.")
### <<< MODIFICATION END: RESULTS DISPLAY BLOCK >>>
