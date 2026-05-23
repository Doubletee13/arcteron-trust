from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from typing import Optional
from datetime import datetime, date
import io

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


def tx_to_dict(tx: Transaction, current_user_id, db: Session = None) -> dict:
    is_credit = (
        str(tx.receiver_id) == str(current_user_id) or
        tx.transaction_type == TransactionType.credit
    )

    # Resolve display name: for local transfers look up the user name
    display_name = tx.recipient_name  # works for international transfers
    display_bank = tx.recipient_bank
    display_account = tx.recipient_account

    if db and not display_name:
        if not is_credit and tx.receiver_id:
            # Outgoing local transfer - show receiver's name
            receiver = db.query(User).filter(User.id == tx.receiver_id).first()
            if receiver:
                display_name = f"{receiver.first_name} {receiver.last_name}"
                display_bank = "Arcteron Trust"
                # Use full account number from account record
                receiver_acct = db.query(Account).filter(Account.user_id == tx.receiver_id).first()
                if receiver_acct:
                    display_account = receiver_acct.account_number
        elif is_credit and tx.sender_id:
            # Incoming local transfer - show sender's name
            sender = db.query(User).filter(User.id == tx.sender_id).first()
            if sender:
                display_name = f"{sender.first_name} {sender.last_name}"
                display_bank = "Arcteron Trust"
                sender_acct = db.query(Account).filter(Account.user_id == tx.sender_id).first()
                if sender_acct:
                    display_account = sender_acct.account_number

    # Determine the current user's own account number for receipt display
    own_account = None
    if db:
        user_acct = db.query(Account).filter(Account.user_id == current_user_id).first()
        if user_acct:
            own_account = user_acct.account_number

    return {
        "id": str(tx.id),
        "reference": tx.reference,
        "amount": float(tx.amount),
        "currency": tx.currency,
        "transaction_type": tx.transaction_type,
        "status": tx.status,
        "description": tx.description,
        "admin_note": tx.admin_note,
        "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "sender_id": str(tx.sender_id) if tx.sender_id else None,
        "receiver_id": str(tx.receiver_id) if tx.receiver_id else None,
        "sender_account_number": tx.sender_account_number,
        "receiver_account_number": tx.receiver_account_number,
        "own_account_number": own_account,
        "recipient_name": display_name,
        "recipient_bank": display_bank,
        "recipient_account": display_account,
        "recipient_swift": tx.recipient_swift,
        "recipient_country": tx.recipient_country,
        "sender_balance_before": float(tx.sender_balance_before) if tx.sender_balance_before else None,
        "sender_balance_after": float(tx.sender_balance_after) if tx.sender_balance_after else None,
        "receiver_balance_before": float(tx.receiver_balance_before) if tx.receiver_balance_before else None,
        "receiver_balance_after": float(tx.receiver_balance_after) if tx.receiver_balance_after else None,
        "is_credit": is_credit,
        "requires_code": tx.requires_code,
        "code_type": tx.code_type,
    }


@router.get("/recent")
def get_recent_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(Transaction).filter(
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    ).order_by(Transaction.created_at.desc()).limit(20).all()
    return [tx_to_dict(tx, current_user.id, db) for tx in transactions]


@router.get("/all")
def get_all_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tx_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    query = db.query(Transaction).filter(
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    )

    if tx_type == "credit":
        query = query.filter(Transaction.receiver_id == current_user.id)
    elif tx_type == "debit":
        query = query.filter(Transaction.sender_id == current_user.id)

    if status:
        query = query.filter(Transaction.status == status)

    if date_from:
        query = query.filter(Transaction.transaction_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.filter(Transaction.transaction_date <= datetime.combine(date_to, datetime.max.time()))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.reference.ilike(search_term),
                Transaction.description.ilike(search_term),
                Transaction.recipient_name.ilike(search_term),
                Transaction.sender_account_number.ilike(search_term),
                Transaction.receiver_account_number.ilike(search_term),
            )
        )

    total = query.count()
    transactions = query.order_by(Transaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "transactions": [tx_to_dict(tx, current_user.id, db) for tx in transactions]
    }


@router.get("/{tx_id}")
def get_single_transaction(
    tx_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetch a single transaction by ID — used by the frontend receipt modal."""
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return tx_to_dict(tx, current_user.id, db)


@router.get("/{tx_id}/receipt")
def download_receipt(
    tx_id: str,
    theme: str = Query("dark"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    is_credit = str(tx.receiver_id) == str(current_user.id) or tx.transaction_type == TransactionType.credit

    pdf_bytes = generate_receipt_pdf(tx, current_user, account, is_credit, theme, db)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt-{tx.reference}.pdf"'
        }
    )


@router.get("/statement/download")
def download_statement(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    theme: str = Query("light"),
):
    query = db.query(Transaction).filter(
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    )

    if date_from:
        query = query.filter(Transaction.transaction_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Transaction.transaction_date <= datetime.combine(date_to, datetime.max.time()))

    transactions = query.order_by(Transaction.transaction_date.asc()).all()
    account = db.query(Account).filter(Account.user_id == current_user.id).first()

    pdf_bytes = generate_statement_pdf(transactions, current_user, account, date_from, date_to, theme)

    filename = f"statement-{current_user.last_name}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ── PDF Branding & UI Components ──

from reportlab.platypus import Flowable

class LogoFlowable(Flowable):
    def __init__(self, size=40, color='#FFFFFF', opacity=1.0):
        Flowable.__init__(self)
        self.width = self.height = size
        self.size = size
        self.color = color
        self.opacity = opacity

    def draw(self):
        from reportlab.lib.colors import HexColor
        canvas = self.canv
        canvas.saveState()
        
        scale = self.size / 40.0
        canvas.scale(scale, scale)
        
        c = HexColor(self.color)
        
        # Background Circle (Subtle)
        canvas.setStrokeColor(c)
        canvas.setLineWidth(1.5)
        canvas.setStrokeAlpha(0.3 * self.opacity)
        canvas.circle(20, 20, 18, fill=0)
        
        # Main "A" Path
        canvas.setStrokeAlpha(0)
        canvas.setFillColor(c)
        canvas.setFillAlpha(0.9 * self.opacity)
        p = canvas.beginPath()
        p.moveTo(20, 32)
        p.lineTo(30, 12)
        p.lineTo(24, 12)
        p.lineTo(20, 20)
        p.lineTo(16, 12)
        p.lineTo(10, 12)
        p.close()
        canvas.drawPath(p, fill=1, stroke=0)
        
        # Horizontal Line
        canvas.setStrokeColor(c)
        canvas.setLineWidth(1.5)
        canvas.setStrokeAlpha(0.6 * self.opacity)
        canvas.line(14, 17, 26, 17)
        
        # Top Dot
        canvas.setStrokeAlpha(0)
        canvas.setFillAlpha(0.5 * self.opacity)
        canvas.circle(20, 34, 2, fill=1, stroke=0)
        
        canvas.restoreState()


def generate_receipt_pdf(tx, user, account, is_credit: bool, theme: str = 'dark', db: Session = None) -> bytes:  # noqa: C901
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white, black, transparent
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    
    # Theme-Aware Colors
    if theme == 'dark':
        bg_main       = HexColor('#111827')
        card_bg       = HexColor('#1F2937')
        text_primary  = white
        text_secondary = HexColor('#9CA3AF')
        text_muted    = HexColor('#6B7280')
        border_color  = HexColor('#2B2F36')
        wm_color      = HexColor('#FFFFFF')
        logo_color    = '#FFFFFF'
    else:
        bg_main       = white
        card_bg       = HexColor('#F9FAFB')
        text_primary  = HexColor('#111827')
        text_secondary = HexColor('#4B5563')
        text_muted    = HexColor('#9CA3AF')
        border_color  = HexColor('#E5E7EB')
        wm_color      = HexColor('#111827')
        logo_color    = '#111827'

    accent_success = HexColor('#10B981')
    accent_danger  = HexColor('#EF4444')
    accent_warning = HexColor('#F59E0B')

    # ── Watermark: diagonal repeating logo + text ──
    def draw_watermark(canvas, doc):
        from reportlab.lib.colors import HexColor
        canvas.saveState()
        # Fill page background
        canvas.setFillColor(bg_main)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

        # Watermark settings
        canvas.setFillColor(wm_color)
        canvas.setFillAlpha(0.04) 
        canvas.setFont('Times-Bold', 9)

        import math
        step_x, step_y = 100, 70
        angle = -25  # degrees
        rad = math.radians(angle)

        page_w, page_h = A4
        for row in range(-2, int(page_h / step_y) + 3):
            for col in range(-2, int(page_w / step_x) + 3):
                cx = col * step_x
                cy = row * step_y
                canvas.saveState()
                canvas.translate(cx, cy)
                canvas.rotate(angle)

                # Mini logo
                scale = 0.28
                canvas.saveState()
                canvas.scale(scale, scale)
                canvas.setStrokeColor(wm_color)
                canvas.setStrokeAlpha(0.04)
                canvas.setLineWidth(1.2)
                canvas.circle(20, 20, 18, fill=0, stroke=1)
                canvas.setFillAlpha(0.04)
                p = canvas.beginPath()
                p.moveTo(20, 32); p.lineTo(30, 12); p.lineTo(24, 12)
                p.lineTo(20, 20); p.lineTo(16, 12); p.lineTo(10, 12)
                p.close()
                canvas.drawPath(p, fill=1, stroke=0)
                canvas.restoreState()

                canvas.setFillColor(wm_color)
                canvas.setFillAlpha(0.04)
                canvas.drawString(14, 2, 'Arcteron Trust')
                canvas.restoreState()

        canvas.restoreState()

    tx_date_val = tx.transaction_date or tx.created_at
    tx_date_str = tx_date_val.strftime("%b %d, %Y") if tx_date_val else "—"
    tx_time_str = tx_date_val.strftime("%I:%M:%S %p UTC") if tx_date_val else "—"
    tx_datetime_str = f"{tx_date_str} · {tx_time_str}" if tx_date_val else "—"

    party_label = "Transfer From" if is_credit else "Transfer To"
    party_name  = "External Sender"
    recipient_acct = tx.recipient_account or "—"
    bank_name = tx.recipient_bank or "Arcteron Trust"

    if is_credit:
        if tx.sender_id and db:
            sender = db.query(User).filter(User.id == tx.sender_id).first()
            if sender:
                party_name = f"{sender.first_name} {sender.last_name}"
                bank_name  = "Arcteron Trust"
                sender_acct = db.query(Account).filter(Account.user_id == sender.id).first()
                if sender_acct: recipient_acct = sender_acct.account_number
    else:
        party_name = tx.recipient_name or "Unknown Recipient"
        if tx.receiver_id and db:
            receiver = db.query(User).filter(User.id == tx.receiver_id).first()
            if receiver:
                party_name = f"{receiver.first_name} {receiver.last_name}"
                bank_name  = "Arcteron Trust"
                rec_acc = db.query(Account).filter(Account.user_id == receiver.id).first()
                if rec_acc: recipient_acct = rec_acc.account_number

    def mask_acct(n):
        if not n or n == '—': return '—'
        d = ''.join(c for c in str(n) if c.isdigit())
        return ('**** ' + d[-4:]) if len(d) > 4 else ('**** ' + d.zfill(4))

    def fmt_acct(n):
        if not n or n == '—': return '—'
        d = ''.join(c for c in str(n) if c.isdigit())
        groups = [d[i:i+4] for i in range(0, len(d), 4)]
        return ' '.join(groups)

    if is_credit:
        display_recipient_acct = mask_acct(recipient_acct)
        display_user_acct      = fmt_acct(account.account_number) if account else '—'
    else:
        display_recipient_acct = fmt_acct(recipient_acct)
        display_user_acct      = mask_acct(account.account_number) if account else '—'

    tx_type_str = (tx.transaction_type or 'Transfer').replace('_', ' ').title()
    sign        = '+' if is_credit else '-'
    amount_val  = f"{sign}${float(tx.amount):,.2f}"

    status_str      = (tx.status or 'Completed').title()
    amount_color    = accent_success if is_credit else accent_danger
    status_color    = (accent_success if tx.status == 'completed'
                       else accent_warning if tx.status == 'pending'
                       else accent_danger)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    brand_font = 'Times-Bold'
    FULL_W     = A4[0] - 44*mm  

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    label_sty  = sty('lbl',   fontSize=9,  fontName='Helvetica',      textColor=text_muted,
                               leading=10, spaceAfter=2)
    value_sty  = sty('val',   fontSize=11, fontName='Helvetica-Bold',  textColor=text_primary, leading=14)
    amount_sty = sty('amt',   fontSize=32, fontName=brand_font,        textColor=amount_color,
                               alignment=TA_CENTER, leading=38)
    status_sty = sty('sts',   fontSize=12, fontName='Helvetica',       textColor=status_color,
                               alignment=TA_CENTER, leading=16)
    dt_sty     = sty('dt',    fontSize=9,  fontName='Helvetica',       textColor=text_secondary,
                               alignment=TA_CENTER, leading=13)
    brand_sty  = sty('brd',   fontSize=16, fontName=brand_font,        textColor=text_primary, leading=20)
    footer_sty = sty('foot',  fontSize=7.5, fontName='Helvetica',      textColor=text_muted,
                               alignment=TA_CENTER, leading=11)

    elements = []

    logo_fl = LogoFlowable(size=28, color=logo_color)
    brand_p = Paragraph('Arcteron Trust', brand_sty)
    receipt_label_p = Paragraph('Transaction Receipt',
                                 sty('rl', fontSize=9, fontName='Helvetica',
                                     textColor=text_muted, alignment=TA_RIGHT, leading=12))

    header_inner = Table(
        [[logo_fl, brand_p, receipt_label_p]],
        colWidths=[10*mm, 100*mm, 56*mm]
    )
    header_inner.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',(0, 0), (-1, -1), 0),
        ('TOPPADDING',  (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_inner)
    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=border_color))
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph(amount_val, amount_sty))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(status_str, status_sty))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(tx_datetime_str, dt_sty))
    elements.append(Spacer(1, 8*mm))

    elements.append(HRFlowable(width="100%", thickness=1, color=border_color,
                                lineCap='round', dash=[2, 4]))
    elements.append(Spacer(1, 6*mm))

    rows = [
        (party_label,    party_name),
        ('Bank',         bank_name),
        ('Account No.',  display_recipient_acct),
        ('Reference',    tx.reference or '—'),
        ('Type',         tx_type_str),
        ('Your Account', display_user_acct),
    ]

    def make_row(lbl, val, is_last=False):
        lbl_p = Paragraph(lbl, label_sty)
        val_p = Paragraph(str(val) if val else '—', value_sty)
        row_table = Table([[lbl_p, val_p]], colWidths=[FULL_W * 0.42, FULL_W * 0.58])
        style = [
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',(0, 0), (-1, -1), 0),
            ('TOPPADDING',  (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN',       (1, 0), (1, 0), 'RIGHT'),
        ]
        if not is_last:
            style.append(('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color))
        row_table.setStyle(TableStyle(style))
        return row_table

    for i, (lbl, val) in enumerate(rows):
        elements.append(make_row(lbl, val, is_last=(i == len(rows) - 1)))

    elements.append(Spacer(1, 6*mm))

    elements.append(HRFlowable(width="100%", thickness=1, color=border_color,
                                lineCap='round', dash=[2, 4]))
    elements.append(Spacer(1, 8*mm))

    elements.append(Paragraph(
        'This is an official transaction receipt issued by Arcteron Trust — Private Banking &amp; Wealth '
        'Management. FDIC Insured · Member SIPC. For inquiries: support@arcterontrust.com',
        footer_sty
    ))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f'© {datetime.now().year} Arcteron Trust',
        sty('copy', fontSize=8, fontName=brand_font, textColor=text_primary, alignment=TA_CENTER)
    ))

    doc.build(elements, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    return buffer.getvalue()


def generate_statement_pdf(transactions, user, account, date_from, date_to, theme: str = 'light') -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    # Theme-Aware Colors
    if theme == 'dark':
        bg_main = HexColor('#0F1115')
        text_primary = white
        text_secondary = HexColor('#9CA3AF')
        text_muted = HexColor('#6B7280')
        border_color = HexColor('#2B2F36')
        light_gray = HexColor('#171A20')
        navy = HexColor('#1F2937') # Dark background for headers
        logo_color = '#FFFFFF'
    else:
        bg_main = white
        text_primary = HexColor('#111827')
        text_secondary = HexColor('#4B5563')
        text_muted = HexColor('#9CA3AF')
        border_color = HexColor('#E5E7EB')
        light_gray = HexColor('#F5F7FA')
        navy = HexColor('#111827')
        logo_color = '#111827'

    green = HexColor('#10B981')
    red = HexColor('#EF4444')
    dark_gray = HexColor('#374151')

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setTitle("Arcteron Trust")
        canvas.setFillColor(bg_main)
        canvas.rect(0, 0, A4[0], A4[1], fill=1)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    elements = []
    brand_font = 'Times-Bold'

    # ── Letterhead (Premium Branding) ──
    logo = LogoFlowable(size=32, color=logo_color)
    
    brand_style = ParagraphStyle(
        'brand', 
        fontSize=24, 
        fontName=brand_font, 
        textColor=white if theme == 'dark' else navy, 
        leading=28,
        letterSpacing=0.5
    )
    
    header_data = [[
        logo,
        Paragraph('Arcteron Trust', brand_style),
        Paragraph('ACCOUNT STATEMENT',
                  ParagraphStyle('hr', fontSize=10, fontName='Helvetica-Bold', textColor=white if theme == 'dark' else navy, alignment=TA_RIGHT))
    ]]
    header_table = Table(header_data, colWidths=[12*mm, 88*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(header_table)
    
    tagline_data = [[
        Paragraph('Private Banking &amp; Wealth Management | FDIC Insured | Member SIPC',
                  ParagraphStyle('tl', fontSize=8, fontName='Helvetica', textColor=text_muted)),
        Paragraph(f'Generated: {datetime.now().strftime("%B %d, %Y")}',
                  ParagraphStyle('tr', fontSize=8, fontName='Helvetica', textColor=text_muted, alignment=TA_RIGHT))
    ]]
    tag_table = Table(tagline_data, colWidths=[100*mm, 80*mm])
    tag_table.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 0)]))
    elements.append(tag_table)
    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=navy))
    elements.append(Spacer(1, 8*mm))

    # ── Account Summary ──
    period_from = date_from.strftime('%B %d, %Y') if date_from else 'All time'
    period_to = date_to.strftime('%B %d, %Y') if date_to else datetime.now().strftime('%B %d, %Y')

    account_info = [
        [
            Paragraph('ACCOUNT HOLDER', ParagraphStyle('al', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('ACCOUNT NUMBER', ParagraphStyle('al', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('ROUTING NUMBER', ParagraphStyle('al', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('STATEMENT PERIOD', ParagraphStyle('al', fontSize=8, fontName='Helvetica', textColor=text_muted)),
        ],
        [
            Paragraph(f'{user.first_name} {user.last_name}',
                     ParagraphStyle('av', fontSize=11, fontName='Helvetica-Bold', textColor=text_primary)),
            Paragraph(f'****{account.account_number[-4:]}' if account else '—',
                     ParagraphStyle('av', fontSize=11, fontName='Helvetica-Bold', textColor=text_primary)),
            Paragraph(account.routing_number if account else '—',
                     ParagraphStyle('av', fontSize=11, fontName='Helvetica-Bold', textColor=text_primary)),
            Paragraph(f'{period_from} — {period_to}',
                     ParagraphStyle('av', fontSize=10, fontName='Helvetica-Bold', textColor=text_primary)),
        ]
    ]

    acc_table = Table(account_info, colWidths=[45*mm, 40*mm, 40*mm, 55*mm])
    acc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_gray),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,0), 0.5, border_color),
    ]))
    elements.append(acc_table)
    elements.append(Spacer(1, 8*mm))

    # ── Summary stats ──
    total_credit = sum(float(tx.amount) for tx in transactions
                      if str(tx.receiver_id) == str(user.id) or tx.transaction_type == 'credit')
    total_debit = sum(float(tx.amount) for tx in transactions
                     if str(tx.sender_id) == str(user.id) and tx.transaction_type != 'credit')

    summary_data = [
        [
            Paragraph('TOTAL TRANSACTIONS', ParagraphStyle('sl', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('TOTAL CREDITS', ParagraphStyle('sl', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('TOTAL DEBITS', ParagraphStyle('sl', fontSize=8, fontName='Helvetica', textColor=text_muted)),
            Paragraph('CURRENT BALANCE', ParagraphStyle('sl', fontSize=8, fontName='Helvetica', textColor=text_muted)),
        ],
        [
            Paragraph(str(len(transactions)),
                     ParagraphStyle('sv', fontSize=14, fontName='Helvetica-Bold', textColor=text_primary)),
            Paragraph(f'${total_credit:,.2f}',
                     ParagraphStyle('sv', fontSize=14, fontName='Helvetica-Bold', textColor=green)),
            Paragraph(f'${total_debit:,.2f}',
                     ParagraphStyle('sv', fontSize=14, fontName='Helvetica-Bold', textColor=red)),
            Paragraph(f'${float(account.balance):,.2f}' if account else '—',
                     ParagraphStyle('sv', fontSize=14, fontName='Helvetica-Bold', textColor=text_primary)),
        ]
    ]

    summ_table = Table(summary_data, colWidths=[45*mm, 40*mm, 40*mm, 55*mm])
    summ_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_main),
        ('BACKGROUND', (0,1), (-1,1), light_gray),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('LINEBELOW', (0,0), (-1,0), 0.5, border_color),
        ('GRID', (0,0), (-1,-1), 0.3, border_color),
    ]))
    elements.append(summ_table)
    elements.append(Spacer(1, 10*mm))

    # ── Transactions table ──
    elements.append(Paragraph('Transaction History',
                               ParagraphStyle('th', fontSize=12, fontName='Helvetica-Bold',
                                              textColor=text_primary, spaceAfter=4)))
    elements.append(Spacer(1, 3*mm))

    if not transactions:
        elements.append(Paragraph('No transactions found for the selected period.',
                                   ParagraphStyle('nt', fontSize=10, fontName='Helvetica', textColor=text_muted,
                                                  alignment=TA_CENTER)))
    else:
        col_style = ParagraphStyle('col', fontSize=8, fontName='Helvetica-Bold', textColor=white)
        tx_headers = [
            [
                Paragraph('DATE', col_style),
                Paragraph('REFERENCE', col_style),
                Paragraph('DESCRIPTION', col_style),
                Paragraph('TYPE', col_style),
                Paragraph('STATUS', col_style),
                Paragraph('AMOUNT', col_style),
            ]
        ]

        tx_rows = []
        for tx in transactions:
            is_credit = str(tx.receiver_id) == str(user.id) or tx.transaction_type == 'credit'
            amount_color = green if is_credit else red
            sign = '+' if is_credit else '-'
            tx_date_val = tx.transaction_date or tx.created_at
            date_str = tx_date_val.strftime('%m/%d/%Y') if tx_date_val else '—'
            ref_short = tx.reference[:16] + '...' if tx.reference and len(tx.reference) > 16 else (tx.reference or '—')
            desc_short = (tx.description or '—')[:35] + ('...' if tx.description and len(tx.description) > 35 else '')
            tx_type = tx.transaction_type.replace('_', ' ').title() if tx.transaction_type else '—'
            status = tx.status.title() if tx.status else '—'

            tx_rows.append([
                Paragraph(date_str, ParagraphStyle('td', fontSize=8, fontName='Helvetica', textColor=text_primary)),
                Paragraph(ref_short, ParagraphStyle('td', fontSize=7, fontName='Helvetica', textColor=text_secondary)),
                Paragraph(desc_short, ParagraphStyle('td', fontSize=8, fontName='Helvetica', textColor=text_primary)),
                Paragraph(tx_type, ParagraphStyle('td', fontSize=8, fontName='Helvetica', textColor=text_primary)),
                Paragraph(status, ParagraphStyle('td', fontSize=8, fontName='Helvetica', textColor=text_primary)),
                Paragraph(f'{sign}${float(tx.amount):,.2f}',
                          ParagraphStyle('td', fontSize=9, fontName='Helvetica-Bold', textColor=amount_color, alignment=TA_RIGHT)),
            ])

        all_data = tx_headers + tx_rows

        tx_table = Table(all_data, colWidths=[24*mm, 32*mm, 48*mm, 28*mm, 20*mm, 30*mm])
        style = [
            ('BACKGROUND', (0,0), (-1,0), navy),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [bg_main, light_gray]),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, border_color),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
        ]
        tx_table.setStyle(TableStyle(style))
        elements.append(tx_table)

    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=border_color))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph(
        'This statement is confidential and intended solely for the named account holder. '
        'Arcteron Trust is FDIC insured and a member of SIPC. '
        'For questions, contact support@arcterontrust.com.',
        ParagraphStyle('footer', fontSize=7, fontName='Helvetica', textColor=text_muted,
                       alignment=TA_CENTER, leading=11)
    ))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f'© {datetime.now().year} Arcteron Trust — Private Banking & Wealth Management',
        ParagraphStyle('copy', fontSize=8, fontName=brand_font, textColor=navy, alignment=TA_CENTER)
    ))

    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()