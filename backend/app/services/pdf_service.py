"""
Générateur de Comptes-Rendus d'Analyses Médicales au format PDF (ReportLab).
Mise en page clinique haute définition conforme aux standards de biologie médicale.
"""

import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from backend.app.config import (
    LABO_NOM, LABO_SOUS_TITRE, LABO_ADRESSE, LABO_TEL, LABO_EMAIL, LABO_DIRECTEUR, LABO_AGREMENT
)
from backend.app.models.core import Demande


def generate_medical_report_pdf(demande: Demande) -> bytes:
    """
    Génère le compte-rendu d'analyses officiel en PDF pour la demande passée en paramètre.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()

    # Styles personnalisés
    style_labo_title = ParagraphStyle(
        'LaboTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_LEFT
    )

    style_labo_sub = ParagraphStyle(
        'LaboSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475569'),
        alignment=TA_LEFT
    )

    style_report_title = ParagraphStyle(
        'ReportTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#0284C7'),
        alignment=TA_CENTER
    )

    style_section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0F766E'),
        spaceBefore=8,
        spaceAfter=4
    )

    style_normal = ParagraphStyle(
        'ReportNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )

    style_bold = ParagraphStyle(
        'ReportBold',
        parent=style_normal,
        fontName='Helvetica-Bold'
    )

    style_alert_high = ParagraphStyle(
        'AlertHigh',
        parent=style_normal,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#DC2626')
    )

    style_alert_low = ParagraphStyle(
        'AlertLow',
        parent=style_normal,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2563EB')
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT
    )

    story = []

    # 1. En-tête du Laboratoire
    header_data = [
        [
            Paragraph(f"<b>{LABO_NOM}</b>", style_labo_title),
            Paragraph(f"<b>Dossier N° :</b> {demande.code_barres}<br/><b>Date :</b> {demande.date_reception.strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('RightH', parent=style_normal, alignment=TA_RIGHT))
        ],
        [
            Paragraph(f"{LABO_SOUS_TITRE}<br/>{LABO_ADRESSE} | Tél: {LABO_TEL}<br/>{LABO_DIRECTEUR} | {LABO_AGREMENT}", style_labo_sub),
            Paragraph(f"<b>Statut :</b> {demande.statut.upper()}<br/><b>Édité le :</b> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('RightH2', parent=style_normal, alignment=TA_RIGHT))
        ]
    ]
    t_header = Table(header_data, colWidths=[11 * cm, 7 * cm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)

    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=8))

    # Titre du document
    story.append(Paragraph("COMPTE-RENDU D'ANALYSES DE BIOLOGIE MÉDICALE", style_report_title))
    story.append(Spacer(1, 0.25 * cm))

    # 2. Encadré Patient et Prescription
    p = demande.patient
    patient_text = f"""
    <b>PATIENT :</b> {p.nom.upper()} {p.prenom.capitalize()}<br/>
    <b>Né(e) le :</b> {p.date_naissance} ({p.age} ans) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Sexe :</b> {'Masculin' if p.sexe.upper() == 'M' else 'Féminin'}<br/>
    <b>CIN / Réf :</b> {p.cin} &nbsp;&nbsp;|&nbsp;&nbsp; <b>N° Assur./CNSS :</b> {p.numero_securite_sociale or 'Néant'}<br/>
    <b>Tél :</b> {p.telephone or 'Néant'}
    """

    presc_text = f"""
    <b>Prescripteur :</b> {demande.prescripteur or 'Dr Externe'}<br/>
    <b>Prélèvement ID :</b> {demande.code_barres}<br/>
    <b>Bilan requis :</b> {demande.bilan_demande or 'Analyses diverses'}<br/>
    <b>Renseignements :</b> {demande.renseignements_cliniques or 'Non renseignés'}
    """

    info_data = [
        [Paragraph(patient_text, style_normal), Paragraph(presc_text, style_normal)]
    ]
    t_info = Table(info_data, colWidths=[9.5 * cm, 8.5 * cm])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 0.4 * cm))

    # 3. Tableau des résultats
    # Regrouper les résultats par catégorie
    resultats = sorted(demande.resultats, key=lambda r: (r.parametre.categorie, r.parametre.ordre_affichage if r.parametre else 0))

    if not resultats:
        story.append(Paragraph("<i>Aucun résultat enregistré pour ce prélèvement.</i>", style_normal))
    else:
        # Grouper par catégorie
        categories: dict = {}
        for r in resultats:
            cat = r.parametre.categorie if r.parametre else "Analyses Générales"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        for cat_name, cat_res in categories.items():
            story.append(Paragraph(f"• {cat_name.upper()}", style_section_heading))

            table_rows = [
                [
                    Paragraph("Paramètre Analysé", style_table_header),
                    Paragraph("Résultat", style_table_header),
                    Paragraph("Unité", style_table_header),
                    Paragraph("Valeurs de Référence", style_table_header),
                    Paragraph("Alerte", style_table_header),
                    Paragraph("Source", style_table_header)
                ]
            ]

            for res in cat_res:
                param = res.parametre
                nom_param = param.nom if param else "Paramètre"
                unite_param = param.unite if param and param.unite else "-"

                # Référence
                ref_str = "-"
                if res.ref_min_applique is not None and res.ref_max_applique is not None:
                    ref_str = f"{res.ref_min_applique:g} - {res.ref_max_applique:g}"
                elif param:
                    r_min, r_max, _ = param.get_reference_range(p.age, p.sexe)
                    if r_min is not None and r_max is not None:
                        ref_str = f"{r_min:g} - {r_max:g}"

                # Alerte
                alerte_txt = "-"
                res_style = style_normal
                if res.drapeau == "ELEVE":
                    alerte_txt = "▲ ÉLEVÉ"
                    res_style = style_alert_high
                elif res.drapeau == "BAS":
                    alerte_txt = "▼ BAS"
                    res_style = style_alert_low

                automate = res.automate_source or "Manuel"

                table_rows.append([
                    Paragraph(f"<b>{nom_param}</b> ({param.code})", style_normal),
                    Paragraph(f"<b>{res.valeur}</b>", res_style),
                    Paragraph(unite_param, style_normal),
                    Paragraph(ref_str, style_normal),
                    Paragraph(f"<b>{alerte_txt}</b>", res_style),
                    Paragraph(automate, ParagraphStyle('Src', parent=style_normal, fontSize=7.5, textColor=colors.HexColor('#64748B')))
                ])

            res_table = Table(table_rows, colWidths=[5.5 * cm, 2.5 * cm, 2.0 * cm, 3.8 * cm, 2.2 * cm, 2.0 * cm])
            res_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284C7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ]))
            story.append(res_table)
            story.append(Spacer(1, 0.25 * cm))

    # 4. Section Bactériologie si présente
    # Vérifier si un examen bactériologique existe pour cette demande
    # (importé dynamiquement pour éviter les dépendances circulaires)
    from backend.app.database import SessionLocal
    from backend.app.models.bacteriology import ExamenBacteriologique
    db = SessionLocal()
    bact_exam = db.query(ExamenBacteriologique).filter(ExamenBacteriologique.demande_id == demande.id).first()
    if bact_exam:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"• BACTÉRIOLOGIE : {bact_exam.type_prelevement}", style_section_heading))
        bact_data = [
            [
                Paragraph(f"<b>Aspect :</b> {bact_exam.aspect_macroscopique}<br/><b>Cytologie Leucocytes :</b> {bact_exam.cytologie_leucocytes or 'Normal'}<br/><b>Cytologie Hématies :</b> {bact_exam.cytologie_hematies or 'Normal'}", style_normal),
                Paragraph(f"<b>Coloration de Gram :</b> {bact_exam.coloration_gram or '-'}<br/><b>Culture :</b> {bact_exam.culture_resultat}<br/><b>Germe Identifié :</b> <font color='#DC2626'><b>{bact_exam.germe_identifie or 'Néant'}</b></font> ({bact_exam.numeration_colonies or ''})", style_normal)
            ]
        ]
        t_bact = Table(bact_data, colWidths=[9.0 * cm, 9.0 * cm])
        t_bact.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#93C5FD')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_bact)

        # Antibiogramme
        if bact_exam.antibiogrammes:
            story.append(Spacer(1, 0.15 * cm))
            story.append(Paragraph("<b>Antibiogramme :</b>", style_bold))
            ab_rows = [
                [
                    Paragraph("Antibiotique", style_table_header),
                    Paragraph("Famille", style_table_header),
                    Paragraph("Zone (mm)", style_table_header),
                    Paragraph("CMI (mg/L)", style_table_header),
                    Paragraph("Interprétation", style_table_header)
                ]
            ]
            for ab in bact_exam.antibiogrammes:
                sens_text = "Sensible (S)" if ab.sensibilite == "S" else ("Résistant (R)" if ab.sensibilite == "R" else "Intermédiaire (I)")
                color_sens = colors.HexColor('#16A34A') if ab.sensibilite == "S" else (colors.HexColor('#DC2626') if ab.sensibilite == "R" else colors.HexColor('#CA8A04'))
                style_ab_sens = ParagraphStyle('AbSens', parent=style_normal, fontName='Helvetica-Bold', textColor=color_sens)

                ab_rows.append([
                    Paragraph(ab.antibiotique_nom, style_normal),
                    Paragraph(ab.famille or "-", style_normal),
                    Paragraph(f"{ab.diametre_zone:g}" if ab.diametre_zone else "-", style_normal),
                    Paragraph(f"{ab.cmi:g}" if ab.cmi else "-", style_normal),
                    Paragraph(sens_text, style_ab_sens)
                ])

            t_ab = Table(ab_rows, colWidths=[5.5 * cm, 4.0 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm])
            t_ab.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCFBF1')),
            ]))
            story.append(t_ab)

    db.close()

    # 5. Conclusion biologique et Signature
    story.append(Spacer(1, 0.4 * cm))
    conclusion_text = demande.conclusion_biologique or (
        "Analyses exécutées sur automates certifiés Sysmex XN / Roche Cobas avec contrôles de qualité internes validés. "
        "Les valeurs hors normes doivent être interprétées en corrélation avec l'état clinique du patient."
    )

    valid_date_str = demande.date_validation.strftime('%d/%m/%Y à %H:%M') if demande.date_validation else "En cours de validation"
    valid_par_str = demande.valide_par or LABO_DIRECTEUR

    sign_data = [
        [
            Paragraph(f"<b>Conclusion Biologique :</b><br/>{conclusion_text}", style_normal),
            Paragraph(
                f"<b>Validation Biologique</b><br/>"
                f"Validé le : {valid_date_str}<br/>"
                f"<b>{valid_par_str}</b><br/>"
                f"<i>Signature & Cachet Électronique</i><br/>"
                f"<font size='7' color='#0284C7'>[DOCUMENT SÉCURISÉ CERTIFIÉ LIMS GHALIMLAB]</font>",
                ParagraphStyle('SignBlock', parent=style_normal, alignment=TA_CENTER)
            )
        ]
    ]
    t_sign = Table(sign_data, colWidths=[11.5 * cm, 6.5 * cm])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(KeepTogether([t_sign]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_tube_labels_pdf(tubes, patient=None) -> bytes:
    """
    Génère les étiquettes code-barres haute définition au format thermique standard (50mm x 25mm).
    Chaque page correspond à une étiquette de tube pour imprimante d'étiquettes thermique (Zebra, Brother, Dymo).
    """
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import createBarcodeDrawing

    buffer = io.BytesIO()
    # Format thermique standard étiquette tube : 50mm x 25mm (141.7 pt x 70.8 pt)
    page_w = 50 * mm
    page_h = 25 * mm

    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    for tube in tubes:
        p = patient
        if not p and tube.demande and tube.demande.patient:
            p = tube.demande.patient

        nom_patient = f"{p.nom.upper()} {p.prenom.capitalize()}" if p else "PATIENT INCONNU"
        if len(nom_patient) > 22:
            nom_patient = nom_patient[:20] + ".."

        age_sexe = f"{p.age}a ({p.sexe})" if p and p.age else ""
        date_str = tube.date_prelevement.strftime("%d/%m/%y %H:%M") if tube.date_prelevement else datetime.datetime.now().strftime("%d/%m/%y")

        # 1. En-tête : Nom du patient + Âge / Sexe
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(2 * mm, 20.8 * mm, nom_patient)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawRightString(48 * mm, 20.8 * mm, age_sexe)

        # 2. Dessin du code-barres Code128 au centre
        val_code = tube.code_tube or "TB-00000"
        try:
            # Largeur ajustée pour tenir confortablement dans les 50mm
            barcode = createBarcodeDrawing(
                'Code128',
                value=val_code,
                width=43 * mm,
                height=9.5 * mm,
                humanReadable=False
            )
            barcode.drawOn(c, 3.5 * mm, 8.5 * mm)
        except Exception:
            # Fallback textuel sécurisé si le générateur échoue
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(25 * mm, 12 * mm, f"[{val_code}]")

        # 3. Code tube en clair centré sous le code-barre
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(25 * mm, 5.8 * mm, val_code)

        # 4. Pied d'étiquette : Type de tube (Couleur), Analyses abrégées et Date
        type_court = tube.type_tube or "Tube"
        if len(type_court) > 16:
            type_court = type_court[:14] + ".."
        bouchon_info = f"{type_court} ({tube.couleur_bouchon or ''})".strip()

        c.setFont("Helvetica", 5.2)
        c.drawString(2 * mm, 2.2 * mm, bouchon_info)
        c.drawRightString(48 * mm, 2.2 * mm, date_str)

        # Fin de l'étiquette courante -> page suivante
        c.showPage()

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

