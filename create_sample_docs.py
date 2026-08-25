import os
from pathlib import Path

def create_samples():
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed yet. Sample PDF generation will run once dependencies finish installing.")
        return

    docs_dir = Path("./sample_docs")
    docs_dir.mkdir(exist_ok=True)

    # 1. Verifone M400 Troubleshooting Guide
    doc1 = fitz.open()
    page1 = doc1.new_page()
    text1 = """AMPM Service POS Documentation
Verifone M400 PIN Pad Field Troubleshooting Guide
Document ID: DOC-VERI-400-v2

Page 1: Common Hardware & Cash-Back Display Symptoms

Symptom A: Cash-Back Other Amount displaying 10x requested amount.
When a customer selects 'Other Amount' for cash-back on the Verifone M400 PIN pad, the screen displays $100 instead of $10.
Root Cause: Decimal scaling misalignment in register.ini under [PINPAD_CONFIG] section.
Resolution:
1. Access LOC Software SMS Register setup.
2. Open C:\\LOC_SMS\\Config\\register.ini in Notepad.
3. Locate entry: PinpadCashbackScale factor.
4. Set PinpadCashbackScale=1 (default was incorrectly set to 10).
5. Save register.ini and reboot the POS lane terminal.

Symptom B: PIN pad displays 'No Host Connection' or IP loop back error.
1. Check Ethernet cable connection at the base of the M400 stand.
2. Verify static IP address on M400 by pressing 1 + 5 + 9 simultaneously.
3. Subnet mask must match store LAN (255.255.255.0). Gateway must be 192.168.1.1.
4. Ping the terminal IP from the master register server.
"""
    page1.insert_text((50, 50), text1)

    page2 = doc1.new_page()
    text2 = """AMPM Service POS Documentation
Verifone M400 PIN Pad Field Troubleshooting Guide - Page 2

Symptom C: M400 PIN Pad screen frozen on AMPM logo during reboot.
Resolution Steps:
1. Perform hard power reset by unplugging the 12V power supply cord from the powered USB/splitter cable.
2. Wait 15 seconds before re-inserting power plug.
3. If screen remains blue, check serial COM port assignment in Device Manager (COM3 required for LOC SMS).
4. Reload M400 OS image via Verifone Direct Loader if firmware corrupted.
"""
    page2.insert_text((50, 50), text2)
    doc1.save(str(docs_dir / "Verifone_M400_Troubleshooting_Guide.pdf"))
    doc1.close()

    # 2. LOC SMS Register Configuration
    doc2 = fitz.open()
    p1 = doc2.new_page()
    t1 = """AMPM Service POS Documentation
LOC Software SMS Register & Server Configuration Guide
Document ID: DOC-LOC-SMS-2025

Page 1: Lane Offline Operations & DB Synchronization

Issue: Lane operating in Offline Mode (Red indicator on status bar).
Symptoms: Store register is unable to sync transactions with master server or load updated price book items.
Step-by-step Resolution:
1. Verify master server service 'LOC_DB_Sync' is running via Windows Services (services.msc).
2. Check network connectivity between Lane and Server (Port 1433 for SQL Server).
3. If server is reachable, force manual DB sync by running 'C:\\LOC_SMS\\Bin\\SyncTool.exe /force'.
4. Inspect sync error log at C:\\LOC_SMS\\Logs\\Sync_Error.log.
"""
    p1.insert_text((50, 50), t1)
    doc2.save(str(docs_dir / "LOC_SMS_Register_Configuration.pdf"))
    doc2.close()

    # 3. Buypass Fiserv Payment Integration
    doc3 = fitz.open()
    p1_3 = doc3.new_page()
    t1_3 = """AMPM Service POS Documentation
Buypass / Fiserv Payment Processing Reference Manual
Document ID: DOC-BUYPASS-2024

Page 1: Credit / Debit Card Authorization Errors & Host Timeouts

Error Code: Buypass Error 91 - Host Timeout
Cause: The payment gateway failed to respond within the 15-second timeout window.
Resolution:
1. Verify broadband internet connection on the main store router.
2. Confirm Buypass primary IP address in POS config: 192.168.10.50 (Port 8443).
3. Run Buypass Diagnostic Ping tool from register: 'C:\\LOC_SMS\\Bin\\BuypassDiag.exe -ping'.
4. If batch fails to settle at end of day, force manual batch settlement using Manager Function 402.
"""
    p1_3.insert_text((50, 50), t1_3)
    doc3.save(str(docs_dir / "Buypass_Fiserv_Payment_Integration.pdf"))
    doc3.close()

    print("[Success] Created sample PDF manuals in ./sample_docs/")

if __name__ == "__main__":
    create_samples()
