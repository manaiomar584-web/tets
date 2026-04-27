import os
import json
from fpdf import FPDF
from datetime import datetime

class RepairPDF(FPDF):
    def header(self):
        # Logo
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 25)
        
        # Header ASTER INFORMATIQUE
        self.set_x(40)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 8, "ASTER INFORMATIQUE", ln=True, align="L")
        self.set_x(40)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, "Reparation Informatique - Imprimantes - Cameras - UPS", ln=True, align="L")
        self.set_x(40)
        self.cell(0, 5, "Tel: 71 881 002 | Adresse: Impasse 1, 06 Ave Abdellaziz Thaalbi, Tunis 1013", ln=True, align="L")
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

def generate_job_pdf(job, type="depot"):
    pdf = RepairPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    title = "BON DE DEPOT" if type == "depot" else "BON DE RETRAIT"
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)

    # Meta Row
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(95, 8, f"N° Reparation : {job.get('product_number', '__________')}")
    
    date_label = "Date :" if type == "depot" else "Date de sortie :"
    date_val = job.get('received_date', '____ / ____ / ______') if type == "depot" else job.get('delivered_date', '____ / ____ / ______')
    try:
        if date_val and '-' in date_val and len(date_val) >= 10:
            dt = datetime.fromisoformat(date_val.split('T')[0])
            date_val = dt.strftime("%d / %m / %Y")
    except:
        pass
    pdf.cell(95, 8, f"{date_label} {date_val}", ln=True, align="R")
    pdf.ln(5)

    def add_section_title(text):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, text, ln=True)
        pdf.ln(1)

    def add_field(label, value):
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, f"* {label} ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, f"{value}\n")

    # --- CLIENT INFO ---
    add_section_title("Informations Client")
    add_field("Nom :", job.get("customer_name", "__________________________"))
    if type == "depot":
        add_field("Telephone :", job.get("phone_number", "____________________"))

    # --- APPAREIL INFO ---
    add_section_title("Informations Appareil" if type == "depot" else "Appareil")
    add_field("Type :", job.get("device_type", "__________________"))
    add_field("Marque & Modele :", job.get("brand_model", "__________________________"))
    if type == "depot":
        add_field("Numero de serie :", job.get("serial_number", "__________________________"))
    
    # --- PANNE / TRAVAIL ---
    section_name = "Panne Signalee" if type == "depot" else "Travail Effectue"
    add_section_title(section_name)
    content = job.get("problem", "") if type == "depot" else job.get("repair_done", "")
    pdf.set_font("Helvetica", "", 11)
    if content:
        pdf.multi_cell(0, 6, content)
    else:
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    if type == "depot":
        # --- ACCESSORIES ---
        add_section_title("Accessoires Remis")
        acc_str = job.get("accessories", "[]")
        accessories = []
        try:
            accessories = json.loads(acc_str) if isinstance(acc_str, str) else acc_str
        except:
            accessories = []
        all_acc = ["Chargeur", "Cable d'alimentation", "Batterie", "Sac / Housse", "Autre"]
        pdf.set_font("Helvetica", "", 11)
        for i in range(0, len(all_acc), 2):
            item1 = all_acc[i]
            mark1 = "X" if item1 in accessories else " "
            pdf.cell(95, 7, f"[{mark1}] {item1}")
            if i + 1 < len(all_acc):
                item2 = all_acc[i+1]
                mark2 = "X" if item2 in accessories else " "
                pdf.cell(95, 7, f"[{mark2}] {item2}")
            pdf.ln()
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, "Autre : ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, f"{job.get('other_accessory', '__________________________')}\n")

        # --- CONDITION ---
        add_section_title("Etat de l'Appareil")
        cond_str = job.get("device_condition", "[]")
        condition = []
        try:
            condition = json.loads(cond_str) if isinstance(cond_str, str) else cond_str
        except:
            condition = []
        all_cond = ["Bon etat", "Rayures", "Pieces cassees", "Ecran endommage", "Pieces manquantes"]
        pdf.set_font("Helvetica", "", 11)
        for i in range(0, len(all_cond), 2):
            item1 = all_cond[i]
            mark1 = "X" if item1 in condition else " "
            pdf.cell(95, 7, f"[{mark1}] {item1}")
            if i + 1 < len(all_cond):
                item2 = all_cond[i+1]
                mark2 = "X" if item2 in condition else " "
                pdf.cell(95, 7, f"[{mark2}] {item2}")
            pdf.ln()
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, "Remarques : ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, f"{job.get('condition_remarks', '_____________________________________')}\n")

        # --- STATUS ---
        add_section_title("Statut")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, "Appareil recu pour diagnostic / reparation", ln=True)

    else:
        # --- PAIEMENT ---
        add_section_title("Paiement")
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, "* Total : ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, f"{job.get('amount', '__________')} TND\n")
        paid = job.get("paid_status") == "Yes"
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"* Paye : {'[X] Oui [ ] Non' if paid else '[ ] Oui [X] Non'}", ln=True)
        
        # --- ETAT RESTITUTION ---
        add_section_title("Etat a la restitution")
        ret_cond_str = job.get("return_condition", "[]")
        ret_condition = []
        try:
            ret_condition = json.loads(ret_cond_str) if isinstance(ret_cond_str, str) else ret_cond_str
        except:
            ret_condition = []
        all_ret = ["Teste et fonctionnel", "Restitue en bon etat", "Client satisfait"]
        pdf.set_font("Helvetica", "", 11)
        for item in all_ret:
            mark = "X" if item in ret_condition else " "
            pdf.cell(0, 7, f"[{mark}] {item}", ln=True)

    # --- SIGNATURES ---
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    add_section_title("Signatures")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 10, "Signature du client : _______________________", align="L")
    tech_name = job.get("technician_name", "____________________")
    pdf.cell(95, 10, f"Signature du technicien : {tech_name}", align="R", ln=True)
    
    # --- FOOTER WARNING ---
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    warning = "Aster Informatique n'est pas responsable des defauts caches non visibles lors du depot." if type == "depot" else "Par sa signature, le client confirme avoir recupere son appareil."
    pdf.cell(0, 10, warning, align="C")

    return pdf.output()
