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
from pathlib import Path

from backend.app.config import (
    BASE_DIR, LABO_NOM, LABO_SOUS_TITRE, LABO_ADRESSE, LABO_TEL, LABO_EMAIL, LABO_DIRECTEUR, LABO_AGREMENT
)
from backend.app.database import SessionLocal
from backend.app.models.core import Demande


def _get_image_flowable(rel_or_abs_path: str, max_w_pt: float, max_h_pt: float):
    """Charge un logo ou média (SVG ou image matricielle) sous forme de Flowable ReportLab."""
    if not rel_or_abs_path:
        return None
    try:
        p_str = rel_or_abs_path.strip()
        if p_str.startswith("/uploads/"):
            abs_path = BASE_DIR / p_str.lstrip("/")
        elif p_str.startswith("/static/"):
            abs_path = BASE_DIR / "frontend" / p_str.lstrip("/")
        else:
            abs_path = Path(p_str)
            if not abs_path.is_absolute():
                abs_path = BASE_DIR / p_str

        if not abs_path.exists():
            return None

        ext = abs_path.suffix.lower()
        if ext == ".svg":
            try:
                from svglib.svglib import svg2rlg
                drawing = svg2rlg(str(abs_path))
                if drawing and drawing.width > 0 and drawing.height > 0:
                    scale = min(max_w_pt / drawing.width, max_h_pt / drawing.height)
                    drawing.scale(scale, scale)
                    drawing.width = drawing.width * scale
                    drawing.height = drawing.height * scale
                    return drawing
            except Exception:
                pass
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            try:
                from PIL import Image as PILImage
                with PILImage.open(str(abs_path)) as img:
                    img.verify()
                from reportlab.platypus import Image as RLImage
                return RLImage(str(abs_path), width=max_w_pt, height=max_h_pt)
            except Exception:
                return None
    except Exception:
        pass
    return None


def generate_medical_report_pdf(demande: Demande) -> bytes:
    """
    Génère le compte-rendu d'analyses officiel en PDF pour la demande passée en paramètre.
    """
    from backend.app.services.billing_service import get_or_create_tarification_params
    db_param = SessionLocal()
    params = get_or_create_tarification_params(db_param)
    db_param.close()

    labo_nom = params.nom_laboratoire or LABO_NOM
    labo_sub = params.sous_titre or LABO_SOUS_TITRE
    labo_adresse = params.adresse or LABO_ADRESSE
    labo_tel = params.telephone or LABO_TEL
    labo_email = params.email or LABO_EMAIL
    labo_directeur = params.directeur or LABO_DIRECTEUR
    labo_agrement = params.agrement or LABO_AGREMENT
    titre_rapport = params.titre_rapport or "COMPTE-RENDU D'ANALYSES DE BIOLOGIE MÉDICALE"

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
    logo_flowable = _get_image_flowable(params.logo_path, 3.8 * cm, 1.4 * cm)
    if logo_flowable:
        lab_text_cell = [
            Paragraph(f"<b>{labo_nom.upper()}</b>", style_labo_title),
            Paragraph(labo_sub, style_labo_sub),
            Paragraph(f"{labo_adresse} • Tél: {labo_tel}", style_labo_sub),
            Paragraph(f"{labo_directeur} • {labo_agrement}", style_labo_sub)
        ]
        t_left = Table([[logo_flowable, lab_text_cell]], colWidths=[4.0 * cm, 7.5 * cm])
        t_left.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        left_header_item = t_left
    else:
        left_header_item = [
            Paragraph(f"<b>{labo_nom}</b>", style_labo_title),
            Paragraph(f"{labo_sub}<br/>{labo_adresse} | Tél: {labo_tel}<br/>{labo_directeur} | {labo_agrement}", style_labo_sub)
        ]

    header_data = [
        [
            left_header_item,
            [
                Paragraph(f"<b>Dossier N° :</b> {demande.code_barres}<br/><b>Date :</b> {demande.date_reception.strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('RightH', parent=style_normal, alignment=TA_RIGHT)),
                Spacer(1, 0.15 * cm),
                Paragraph(f"<b>Statut :</b> {demande.statut.upper()}<br/><b>Édité le :</b> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('RightH2', parent=style_normal, alignment=TA_RIGHT))
            ]
        ]
    ]
    t_header = Table(header_data, colWidths=[11.5 * cm, 6.5 * cm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)

    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=8))

    # Titre du document
    story.append(Paragraph(titre_rapport, style_report_title))
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

    is_valide = (demande.statut == "Validé")
    valid_date_str = demande.date_validation.strftime('%d/%m/%Y à %H:%M') if demande.date_validation else "En cours de validation"
    valid_par_str = demande.valide_par or labo_directeur

    cachet_flowable = _get_image_flowable(params.cachet_path, 2.2 * cm, 2.2 * cm)
    sign_flowable = _get_image_flowable(params.signature_path, 3.0 * cm, 1.3 * cm)

    sign_elements = [
        Paragraph("<b>Validation Biologique</b>", ParagraphStyle('SignTitle', parent=style_normal, alignment=TA_CENTER, fontName='Helvetica-Bold')),
        Paragraph(f"<font size='7.5'>Validé le : <b>{valid_date_str}</b></font>", ParagraphStyle('SignDate', parent=style_normal, alignment=TA_CENTER)),
        Paragraph(f"<b>{valid_par_str}</b>", ParagraphStyle('SignDoc', parent=style_normal, alignment=TA_CENTER, fontSize=8, textColor=colors.HexColor('#0F172A')))
    ]

    if is_valide and (params.auto_signer_validation or cachet_flowable or sign_flowable):
        stamp_cells = []
        if cachet_flowable:
            stamp_cells.append(cachet_flowable)
        if sign_flowable:
            stamp_cells.append(sign_flowable)
        
        if stamp_cells:
            t_stamps = Table([stamp_cells], colWidths=[3.0 * cm] * len(stamp_cells))
            t_stamps.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 0),
            ]))
            sign_elements.append(t_stamps)

        sign_elements.append(Paragraph("<font size='6.5' color='#0284C7'>[DOCUMENT SÉCURISÉ - SIGNATURE & CACHET ÉLECTRONIQUE LIMS]</font>", ParagraphStyle('SignSec', parent=style_normal, alignment=TA_CENTER)))
    else:
        sign_elements.append(Spacer(1, 0.3 * cm))
        sign_elements.append(Paragraph("<i>[Document en attente de validation officielle]</i>", ParagraphStyle('SignWait', parent=style_normal, alignment=TA_CENTER, fontSize=7.5, textColor=colors.HexColor('#DC2626'))))

    sign_data = [
        [
            Paragraph(f"<b>Conclusion Biologique :</b><br/>{conclusion_text}", style_normal),
            sign_elements
        ]
    ]
    t_sign = Table(sign_data, colWidths=[11.5 * cm, 6.5 * cm])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
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


def generate_invoice_pdf(facture) -> bytes:
    """
    Génère la facture officielle / reçu d'honoraires d'analyses médicales au format PDF (ReportLab A4).
    Mise en page clinique haute définition conforme aux règles comptables et conventionnelles (CNSS / CNOPS / Assurances).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

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

    style_normal = ParagraphStyle('NormalInv', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#1E293B'))
    style_bold = ParagraphStyle('BoldInv', parent=style_normal, fontName='Helvetica-Bold')
    style_right = ParagraphStyle('RightInv', parent=style_normal, alignment=TA_RIGHT)
    style_right_bold = ParagraphStyle('RightBoldInv', parent=style_bold, alignment=TA_RIGHT)
    style_center = ParagraphStyle('CenterInv', parent=style_normal, alignment=TA_CENTER)
    style_center_bold = ParagraphStyle('CenterBoldInv', parent=style_bold, alignment=TA_CENTER)

    from backend.app.services.billing_service import get_or_create_tarification_params
    db_param = SessionLocal()
    params = get_or_create_tarification_params(db_param)
    db_param.close()

    labo_nom = params.nom_laboratoire or LABO_NOM
    labo_sub = params.sous_titre or LABO_SOUS_TITRE
    labo_adresse = params.adresse or LABO_ADRESSE
    labo_tel = params.telephone or LABO_TEL
    labo_email = params.email or LABO_EMAIL
    labo_directeur = params.directeur or LABO_DIRECTEUR
    ice_val = params.ice or "002847192000045"
    if_val = params.identifiant_fiscal or "40291823"
    pat_val = params.patente or "32194850"
    cnss_val = params.cnss_affiliation or "7849201"

    story = []

    # 1. En-tête du Laboratoire
    p = facture.patient
    demande = facture.demande

    logo_flowable = _get_image_flowable(params.logo_path, 3.8 * cm, 1.4 * cm)
    fiscal_info_p = Paragraph(f"<font size='7' color='#64748B'><b>ICE :</b> {ice_val} | <b>IF :</b> {if_val} | <b>Patente :</b> {pat_val} | <b>CNSS :</b> {cnss_val}</font>", style_normal)

    if logo_flowable:
        lab_details = [
            Paragraph(f"<b>{labo_nom.upper()}</b>", ParagraphStyle('LabName', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.HexColor('#0F172A'))),
            Paragraph(labo_sub, ParagraphStyle('LabSub', fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#0F766E'))),
            Paragraph(f"{labo_adresse} • Tél: {labo_tel}", style_normal),
            Paragraph(f"Email: {labo_email} • {labo_directeur}", style_normal),
            fiscal_info_p
        ]
        t_left = Table([[logo_flowable, lab_details]], colWidths=[3.8 * cm, 7.7 * cm])
        t_left.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        labo_header_left = t_left
    else:
        labo_header_left = [
            Paragraph(f"<b>{labo_nom.upper()}</b>", ParagraphStyle('LabName', fontName='Helvetica-Bold', fontSize=13, leading=15, textColor=colors.HexColor('#0F172A'))),
            Paragraph(labo_sub, ParagraphStyle('LabSub', fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#0F766E'))),
            Paragraph(f"{labo_adresse} • Tél: {labo_tel}", style_normal),
            Paragraph(f"Email: {labo_email} • {labo_directeur}", style_normal),
            fiscal_info_p
        ]

    statut_color = '#15803D' if facture.statut_paiement == 'Payé intégralement' else ('#B45309' if 'Avance' in facture.statut_paiement else '#DC2626')
    statut_bg = '#DCFCE7' if facture.statut_paiement == 'Payé intégralement' else ('#FEF3C7' if 'Avance' in facture.statut_paiement else '#FEE2E2')

    labo_header_right = [
        Paragraph(f"<b>FACTURE / REÇU D'HONORAIRES</b>", ParagraphStyle('FacTitre', fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_RIGHT, textColor=colors.HexColor('#0284C7'))),
        Paragraph(f"<b>N° : {facture.numero_facture}</b>", ParagraphStyle('FacNum', fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=TA_RIGHT, textColor=colors.HexColor('#0F172A'))),
        Paragraph(f"Date : {facture.date_facture.strftime('%d/%m/%Y à %H:%M')}", style_right),
        Spacer(1, 0.2 * cm),
        Paragraph(f"<font color='{statut_color}'><b>[ {facture.statut_paiement.upper()} ]</b></font>", ParagraphStyle('FacStatut', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT))
    ]

    t_header = Table([[labo_header_left, labo_header_right]], colWidths=[11.5 * cm, 6.5 * cm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)

    story.append(Spacer(1, 0.35 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=8))

    # 2. Encadré Patient & Détails de la Prise en Charge
    cin_str = p.cin if p else "-"
    cnss_str = p.numero_securite_sociale or facture.numero_prise_en_charge or "Non renseigné"
    nom_patient = f"{p.nom.upper()} {p.prenom}" if p else "Patient inconnu"
    age_sexe = f"{p.age} ans ({p.sexe})" if p and p.age else "-"
    prescripteur_str = demande.prescripteur if demande and demande.prescripteur else "Dr. Externe"
    prel_code = demande.code_barres if demande else "-"

    type_pe = facture.type_prise_en_charge or "Normal"
    taux_str = f"x {facture.taux_applique:.2f} DH" if facture.taux_applique else "x 1.36 DH"

    info_data = [
        [
            Paragraph("<b>INFORMATIONS DU PATIENT</b>", ParagraphStyle('SecT', parent=style_bold, textColor=colors.HexColor('#0284C7'), fontSize=9)),
            Paragraph("<b>COUVERTURE & FACTURATION</b>", ParagraphStyle('SecT2', parent=style_bold, textColor=colors.HexColor('#0284C7'), fontSize=9))
        ],
        [
            Paragraph(f"Nom & Prénom : <b>{nom_patient}</b><br/>CIN / Identifiant : <b>{cin_str}</b><br/>Âge & Sexe : {age_sexe}<br/>N° Sécurité Sociale / CNSS : {cnss_str}", style_normal),
            Paragraph(f"Prise en charge : <b>{type_pe.upper()}</b> ({taux_str})<br/>Organisme : <b>{facture.organisme_nom or type_pe}</b><br/>Dossier Prélèvement : <b>{prel_code}</b><br/>Prescripteur : {prescripteur_str}", style_normal)
        ]
    ]
    t_info = Table(info_data, colWidths=[9.0 * cm, 9.0 * cm])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_info)

    story.append(Spacer(1, 0.4 * cm))

    # 3. Tableau détaillé des Actes et Analyses
    rows_actes = [
        [
            Paragraph("<b>Code</b>", style_center_bold),
            Paragraph("<b>Désignation de l'Analyse Médicale</b>", style_bold),
            Paragraph("<b>Coeff B</b>", style_center_bold),
            Paragraph("<b>Prix Unit. (DH)</b>", style_right_bold),
            Paragraph("<b>Qté</b>", style_center_bold),
            Paragraph("<b>Total (DH)</b>", style_right_bold),
        ]
    ]

    for ligne in facture.lignes:
        rows_actes.append([
            Paragraph(f"<font color='#0284C7'><b>{ligne.code_acte}</b></font>", style_center),
            Paragraph(ligne.nom_acte, style_normal),
            Paragraph(f"B {int(ligne.coefficient) if ligne.coefficient.is_integer() else ligne.coefficient}", style_center),
            Paragraph(f"{ligne.prix_unitaire:.2f}", style_right),
            Paragraph(str(ligne.quantite), style_center),
            Paragraph(f"<b>{ligne.total_ligne:.2f}</b>", style_right_bold),
        ])

    t_actes = Table(rows_actes, colWidths=[2.2 * cm, 8.8 * cm, 2.0 * cm, 2.4 * cm, 1.2 * cm, 2.4 * cm])
    t_actes.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#0284C7')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
    ]))
    story.append(t_actes)

    story.append(Spacer(1, 0.4 * cm))

    # 4. Bloc Récapitulatif Financier
    tot_b_str = f"B {int(facture.total_b) if facture.total_b.is_integer() else facture.total_b:.1f}"

    recap_rows = [
        [
            Paragraph(f"<b>Total Cotation : {tot_b_str}</b><br/><font size='7.5' color='#64748B'>Exonération de TVA conformément à l'article 91-I-A-1° du CGI.</font>", style_normal),
            Paragraph("Total Brut :", style_right),
            Paragraph(f"<b>{facture.montant_brut:.2f} DH</b>", style_right_bold)
        ]
    ]

    if facture.remise_montant and facture.remise_montant > 0:
        recap_rows.append([
            "",
            Paragraph(f"Remise ({facture.remise_pourcent:g}%) :", style_right),
            Paragraph(f"-{facture.remise_montant:.2f} DH", ParagraphStyle('Remise', parent=style_right, textColor=colors.HexColor('#DC2626')))
        ])

    recap_rows.append([
        Paragraph(f"Mode de règlement : <b>{facture.mode_paiement}</b>" + (f" (Réf: {facture.reference_paiement})" if facture.reference_paiement else ""), style_normal),
        Paragraph("<b>NET À PAYER :</b>", ParagraphStyle('NetL', parent=style_right_bold, fontSize=10, textColor=colors.HexColor('#0F172A'))),
        Paragraph(f"<b>{facture.montant_net:.2f} DH</b>", ParagraphStyle('NetV', parent=style_right_bold, fontSize=10, textColor=colors.HexColor('#0284C7')))
    ])

    if facture.part_organisme and facture.part_organisme > 0:
        recap_rows.append([
            Paragraph("<font color='#0F766E'>Prise en charge par Tiers-Payant Organisme</font>", style_normal),
            Paragraph("Part Organisme (CNSS/Assur.) :", style_right),
            Paragraph(f"<b>{facture.part_organisme:.2f} DH</b>", style_right_bold)
        ])
        recap_rows.append([
            "",
            Paragraph("Ticket Modérateur Patient :", style_right),
            Paragraph(f"<b>{facture.part_patient:.2f} DH</b>", style_right_bold)
        ])

    recap_rows.append([
        "",
        Paragraph("Montant Encaissé :", style_right),
        Paragraph(f"<b>{facture.montant_paye:.2f} DH</b>", ParagraphStyle('PayeV', parent=style_right_bold, textColor=colors.HexColor('#15803D')))
    ])

    color_reste = colors.HexColor('#15803D') if facture.reste_a_payer <= 0 else colors.HexColor('#DC2626')
    recap_rows.append([
        "",
        Paragraph("<b>SOLDE RESTANT :</b>", ParagraphStyle('SoldeL', parent=style_right_bold, textColor=color_reste)),
        Paragraph(f"<b>{facture.reste_a_payer:.2f} DH</b>", ParagraphStyle('SoldeV', parent=style_right_bold, fontSize=9.5, textColor=color_reste))
    ])

    t_recap = Table(recap_rows, colWidths=[9.0 * cm, 5.5 * cm, 4.5 * cm])
    t_recap.setStyle(TableStyle([
        ('BOX', (1, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (1, -3), (-1, -3), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(KeepTogether([t_recap]))

    # 5. Bloc Signature et Cachet
    story.append(Spacer(1, 0.5 * cm))
    cachet_flowable = _get_image_flowable(params.cachet_path, 2.0 * cm, 2.0 * cm)
    sign_flowable = _get_image_flowable(params.signature_path, 2.8 * cm, 1.2 * cm)

    sign_box_items = [
        Paragraph("<b>Cachet et Signature du Laboratoire</b>", ParagraphStyle('SignFTitle', parent=style_center, fontSize=8, fontName='Helvetica-Bold')),
        Paragraph(f"<font size='7' color='#64748B'>Le {datetime.datetime.now().strftime('%d/%m/%Y')}</font>", ParagraphStyle('SignFDate', parent=style_center, fontSize=7)),
        Paragraph(f"<b>{labo_directeur}</b>", ParagraphStyle('SignFDir', parent=style_center, fontSize=7.5))
    ]

    stamp_cells = []
    if cachet_flowable:
        stamp_cells.append(cachet_flowable)
    if sign_flowable:
        stamp_cells.append(sign_flowable)

    if stamp_cells:
        t_stamps = Table([stamp_cells], colWidths=[2.8 * cm] * len(stamp_cells))
        t_stamps.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        sign_box_items.append(t_stamps)

    sign_box_items.append(Paragraph("<font size='6.5' color='#0284C7'>[DOCUMENT COMPTABLE CERTIFIÉ LIMS]</font>", ParagraphStyle('SignFSec', parent=style_center)))

    sign_table = Table([
        [
            Paragraph(
                "<i>Reçu délivré pour valoir ce que de droit.<br/>"
                "Les analyses de biologie médicale sont exécutées sous la responsabilité du Biologiste Médical Directeur.</i>",
                style_normal
            ),
            sign_box_items
        ]
    ], colWidths=[11.5 * cm, 6.5 * cm])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
        ('PADDING', (1, 0), (1, 0), 6),
    ]))
    story.append(KeepTogether([sign_table]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


