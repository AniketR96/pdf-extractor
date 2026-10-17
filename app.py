import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

def extract_mahavitaran(pdf_file, filename):
    data = {"Outlet": "", "Consumer No:": "", "BILL NO.(GGN):": "", "Bill Date:": "", "Due Date:": "", 
            "Bill Amount Rs:": "", "If Paid upto this Date:": "", "IF PAID UPTO": "", 
            "Current Reading": "", "Prevoius Reading": "", "Current Reading Date:": "", "Previous Reading Date:": ""}
    
    outlet_match = re.search(r'(IMH[A-Za-z0-9]+)', filename)
    if outlet_match: data["Outlet"] = outlet_match.group(1)

    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        c_match = re.search(r'(?:ग्राहक क्रमांक|Consumer No)[\s\|:]*(\d+)', text)
        if c_match: data["Consumer No:"] = "'" + c_match.group(1)
        
        b_match = re.search(r'BILL NO\.\(GGN\)[\s\|:]*(\d+)', text)
        if b_match: data["BILL NO.(GGN):"] = "'" + b_match.group(1)
        
        bd_match = re.search(r'(?:देयक दिनांक|Bill Date)[\s\|:]*([\d]{2}-[\d]{2}-[\d]{4})', text)
        if bd_match: data["Bill Date:"] = bd_match.group(1)
        
        dd_match = re.search(r'(?:देय दिनांक|Due Date)[\s\|:]*([\d]{2}-[\d]{2}-[\d]{4})', text)
        if dd_match: data["Due Date:"] = dd_match.group(1)
        
        amt_match = re.search(r'(?:देयक रक्कम रु|Bill Amount)[\s\|:]*([\d\.]+)', text)
        if amt_match: data["Bill Amount Rs:"] = amt_match.group(1)
        
        paid_upto_match = re.search(r'(?:या तारखे पर्यंत भरल्यास|If Paid upto)[^\d]*([\d]{2}-[\d]{2}-[\d]{4})[^\d]*([\d\.]+)', text, re.IGNORECASE)
        if paid_upto_match:
            data["If Paid upto this Date:"] = paid_upto_match.group(1)
            data["IF PAID UPTO"] = paid_upto_match.group(2)
            
        cr_match = re.search(r'(?:चालु रिडिंग|Current Reading)(?!\s*दिनांक|\s*Date)[\s\|:]*(\d+)', text)
        if cr_match: data["Current Reading"] = cr_match.group(1)
            
        pr_match = re.search(r'(?:मागील रिडिंग|Previous Reading)(?!\s*दिनांक|\s*Date)[\s\|:]*(\d+)', text)
        if pr_match: data["Prevoius Reading"] = pr_match.group(1)
        
        crd_match = re.search(r'(?:चालु रिडिंग दिनांक|Current Reading Date).*?([\d]{2}-[\d]{2}-[\d]{4})', text, re.DOTALL)
        if crd_match: data["Current Reading Date:"] = crd_match.group(1)
            
        prd_match = re.search(r'(?:मागील रिडिंग दिनांक|Previous Reading Date).*?([\d]{2}-[\d]{2}-[\d]{4})', text, re.DOTALL)
        if prd_match: data["Previous Reading Date:"] = prd_match.group(1)

    return data

def extract_general_invoice(pdf_file, filename, pattern_dict, prefix_fields=[]):
    data = {key: "" for key in pattern_dict.keys()}
    
    if "Booking Id" in data:
        nf_match = re.search(r'(NF\d+)', filename)
        if nf_match: data["Booking Id"] = nf_match.group(1)

    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        for key, pattern in pattern_dict.items():
            if key == "Booking Id": continue
            
            # Using DOTALL ensures we can search across newlines natively
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                data[key] = f"'{val}" if key in prefix_fields else val
    return data

# Regex Patterns tuned strictly to the provided document samples
TAB_CONFIGS = {
    "Mahavitaran": {
        "headers": ["Outlet", "Consumer No:", "BILL NO.(GGN):", "Bill Date:", "Due Date:", "Bill Amount Rs:", "If Paid upto this Date:", "IF PAID UPTO", "Current Reading", "Prevoius Reading", "Current Reading Date:", "Previous Reading Date:"],
        "processor": extract_mahavitaran
    },
    "MMT Inv": {
        "headers": ["Booking Id", "Invoice No.", "Passenger Name(s)", "Ticket No.", "PNR", "*Fare Charges", "Service Fees", "IGST @18%", "Grand Total"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Invoice No.": r'Invoice No\.\s*([A-Za-z0-9]+)',
            "Passenger Name(s)": r'Passenger Name\(s\).*?PNR[\s\r\n]+([^\|]+)\|',
            "Ticket No.": r'Passenger Name\(s\).*?PNR[\s\r\n]+[^\|]+\|\s*([A-Za-z0-9]+)\s*\|',
            "PNR": r'Passenger Name\(s\).*?PNR[\s\r\n]+[^\|]+\|\s*[A-Za-z0-9]+\s*\|\s*([A-Za-z0-9]+)', 
            "*Fare Charges": r'\*Fare Charges.*?\|\s*([\d\.]+)', 
            "Service Fees": r'Service Fees[\s\r\n]*\|\s*([\d\.]+)', 
            "IGST @18%": r'IGST[^\|]*\|\s*([\d\.]+)', 
            "Grand Total": r'Grand Total[\s\r\n]*\|\s*([\d\.]+)'
        })
    },
    "Air India Inv": {
        "headers": ["Booking Id", "Invoice Number :", "Invoice Date :", "PNR :", "Reference Document Number :", "Total Value"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Invoice Number :": r'Invoice Number:\s*([A-Za-z0-9]+)', 
            "Invoice Date :": r'Invoice Date:\s*([\d/]+)', 
            "PNR :": r'PNR:\s*([A-Za-z0-9]+)', 
            "Reference Document Number :": r'Reference Document Number:\s*([A-Za-z0-9]+)', 
            "Total Value": r'Total\s*\|[\s\|]*([\d\,\.]+)'
        }, prefix_fields=["Invoice Number :", "Reference Document Number :"])
    },
    "Indigo Inv": {
        "headers": ["Booking Id", "Number :", "Date :", "PNR :", "Total(Incl Taxes)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Number :": r'Number:\s*([A-Za-z0-9]+)', 
            "Date :": r'Date:\s*([\d-A-Za-z]+)', 
            "PNR :": r'PNR:\s*([A-Za-z0-9]+)', 
            "Total(Incl Taxes)": r'Grand Total[\s\|]+(?:[\d\,\.]+\s*\|\s*)*([\d\,\.]+)'
        })
    },
    "SpiceJet Inv": {
        "headers": ["Booking Id", "Invoice No:", "Invoice Date:", "PNR:", "Total Invoice Value inclusive of Taxes (in figures)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Invoice No:": r'Invoice No:\s*([A-Za-z0-9/]+)', 
            "Invoice Date:": r'Invoice Date:\s*([\d-A-Za-z\s]+(?:AM|PM)?)', 
            "PNR:": r'PNR:\s*(?:\|\s*)?([A-Za-z0-9]+)', 
            "Total Invoice Value inclusive of Taxes (in figures)": r'Total Invoice Value inclusive of Taxes \(in figures\)[\sA-Za-z\(\)\n\r]*?([\d\.]+)'
        })
    },
    "Air India Express Inv": {
        "headers": ["Booking Id", "Invoice Number :", "Invoice Date :", "PNR No :", "Total Invoice Value"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Invoice Number :": r'Invoice Number\s*:\s*([A-Za-z0-9]+)', 
            "Invoice Date :": r'Invoice Date\s*:\s*([\d-]+)', 
            "PNR No :": r'PNR No\s*:\s*([A-Za-z0-9]+)', 
            "Total Invoice Value": r'Grand Total[\s\|\d\,\.]+?([\d\,\.]+)[\n\r]*'
        })
    },
    "SNV Aviation": {
        "headers": ["Booking Id", "Invoice Number:", "Invoice Date:", "PNR:", "Total Amount (incl.tax)"],
        "processor": lambda p, f: extract_general_invoice(p, f, {
            "Booking Id": "", 
            "Invoice Number:": r'Invoice Number:\s*([A-Za-z0-9]+)', 
            "Invoice Date:": r'Invoice Date:\s*([\d-A-Za-z]+)', 
            "PNR:": r'PNR:\s*([A-Za-z0-9]+)', 
            "Total Amount (incl.tax)": r'Grand Total[\s\|]+(?:[\d\,\.]+\s*\|\s*)*([\d\,\.]+)'
        })
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
