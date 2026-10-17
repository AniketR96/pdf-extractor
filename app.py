import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

def extract_mahavitaran(pdf_file, filename):
    data = {"Outlet": "", "Consumer No:": "", "BILL NO.(GGN):": "", "Bill Date:": "", "Due Date:": "", 
            "Bill Amount Rs:": "", "If Paid upto this Date:": "", "IF PAID UPTO": "", 
            "Current Reading": "", "Prevoius Reading": "", "Current Reading Date:": "", "Previous Reading Date:": ""}
    
    outlet_match = re.search(r'(IMH[A-Za-z0-9_]+)', filename)
    if outlet_match: data["Outlet"] = outlet_match.group(1)

    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        data["Consumer No:"] = "'" + (re.search(r'Consumer No:\s*(\w+)', text).group(1) if re.search(r'Consumer No:\s*(\w+)', text) else "")
        data["BILL NO.(GGN):"] = "'" + (re.search(r'BILL NO\.\(GGN\):\s*(\w+)', text).group(1) if re.search(r'BILL NO\.\(GGN\):\s*(\w+)', text) else "")
        data["Bill Date:"] = re.search(r'Bill Date:\s*([\d\w-]+)', text).group(1) if re.search(r'Bill Date:\s*([\d\w-]+)', text) else ""
        data["Due Date:"] = re.search(r'Due Date:\s*([\d\w-]+)', text).group(1) if re.search(r'Due Date:\s*([\d\w-]+)', text) else ""
        data["Bill Amount Rs:"] = re.search(r'Bill Amount Rs:\s*([\d\.]+)', text).group(1) if re.search(r'Bill Amount Rs:\s*([\d\.]+)', text) else ""
    return data

def extract_general_invoice(pdf_file, filename, pattern_dict, prefix_fields=[]):
    data = {key: "" for key in pattern_dict.keys()}
    
    if "Booking Id" in data:
        nf_match = re.search(r'(NF\d+)', filename)
        if nf_match: data["Booking Id"] = nf_match.group(1)

    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        for key, pattern in pattern_dict.items():
            if key == "Booking Id": continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                data[key] = f"'{val}" if key in prefix_fields else val
    return data

TAB_CONFIGS = {
    "Mahavitaran": {
        "headers": ["Outlet", "Consumer No:", "BILL NO.(GGN):", "Bill Date:", "Due Date:", "Bill Amount Rs:", "If Paid upto this Date:", "IF PAID UPTO", "Current Reading", "Prevoius Reading", "Current Reading Date:", "Previous Reading Date:"],
        "processor": extract_mahavitaran
    },
    "MMT Inv": {
        "headers": ["Booking Id", "Invoice No.", "Passenger Name(s)", "Ticket No.", "PNR", "*Fare Charges", "Service Fees", "IGST @18%", "Grand Total"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Invoice No.": r'Invoice No\.\s*[:\-]?\s*(\S+)', "PNR": r'PNR\s*[:\-]?\s*(\S+)', "Grand Total": r'Grand Total\s*[:\-]?\s*([\d\.]+)'})
    },
    "Air India Inv": {
        "headers": ["Booking Id", "Invoice Number :", "Invoice Date :", "PNR :", "Reference Document Number :", "Total Value"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Invoice Number :": r'Invoice Number\s*:\s*(\S+)', "Invoice Date :": r'Invoice Date\s*:\s*(\S+)', "PNR :": r'PNR\s*:\s*(\S+)', "Reference Document Number :": r'Reference Document Number\s*:\s*(\S+)', "Total Value": r'Total Value\s*(\S+)'}, prefix_fields=["Invoice Number :", "Reference Document Number :"])
    },
    "Indigo Inv": {
        "headers": ["Booking Id", "Number :", "Date :", "PNR :", "Total(Incl Taxes)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Number :": r'Number\s*:\s*(\S+)', "Date :": r'Date\s*:\s*(\S+)', "PNR :": r'PNR\s*:\s*(\S+)', "Total(Incl Taxes)": r'Total\(Incl Taxes\)\s*([\d\.]+)'})
    },
    "SpiceJet Inv": {
        "headers": ["Booking Id", "Invoice No:", "Invoice Date:", "PNR:", "Total Invoice Value inclusive of Taxes (in figures)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Invoice No:": r'Invoice No:\s*(\S+)', "Invoice Date:": r'Invoice Date:\s*(\S+)', "PNR:": r'PNR:\s*(\S+)', "Total Invoice Value inclusive of Taxes (in figures)": r'Total Invoice Value.*?\s+([\d\.]+)'})
    },
    "Air India Express Inv": {
        "headers": ["Booking Id", "Invoice Number :", "Invoice Date :", "PNR No :", "Total Invoice Value"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Invoice Number :": r'Invoice Number\s*:\s*(\S+)', "Invoice Date :": r'Invoice Date\s*:\s*(\S+)', "PNR No :": r'PNR No\s*:\s*(\S+)', "Total Invoice Value": r'Total Invoice Value\s*(\S+)'})
    },
    "SNV Aviation": {
        "headers": ["Booking Id", "Invoice Number:", "Invoice Date:", "PNR:", "Total Amount (incl.tax)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {"Booking Id": "", "Invoice Number:": r'Invoice Number:\s*(\S+)', "Invoice Date:": r'Invoice Date:\s*(\S+)', "PNR:": r'PNR:\s*(\S+)', "Total Amount (incl.tax)": r'Total Amount \(incl\.tax\)\s*([\d\.]+)'})
    }
}

st.set_page_config(page_title="PDF Extractor", layout="wide")
st.title("Multi-PDF Data Extractor")
st.write("Upload PDFs under the corresponding tab to extract data directly into Excel.")

tab_names = list(TAB_CONFIGS.keys())
tabs = st.tabs(tab_names)

for i, tab_name in enumerate(tab_names):
    with tabs[i]:
        st.header(f"Extract {tab_name} Data")
        config = TAB_CONFIGS[tab_name]
        
        uploaded_files = st.file_uploader(f"Drag and drop {tab_name} PDFs here", type="pdf", accept_multiple_files=True, key=f"uploader_{tab_name}")
        
        if uploaded_files:
            if st.button(f"Extract {tab_name} Data", key=f"btn_{tab_name}"):
                all_data = []
                with st.spinner('Extracting data...'):
                    for uploaded_file in uploaded_files:
                        try:
                            extracted = config["processor"](uploaded_file, uploaded_file.name)
                            all_data.append(extracted)
                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {e}")
                
                if all_data:
                    df = pd.DataFrame(all_data, columns=config["headers"])
                    
                    # Create in-memory buffer for the Excel file
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Sheet1')
                    
                    st.success("Extraction complete!")
                    st.download_button(
                        label="Download Excel File",
                        data=buffer.getvalue(),
                        file_name=f"{tab_name}_Extracted_Data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{tab_name}"
                    )
