"""Generate a two-page customer quick-start guide; contains no credentials."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT

OUT = Path(__file__).parent
PDF = OUT / 'GST_Easy_V2_Simple_User_Guide.pdf'
W, H = 595.28, 841.89
GREEN = HexColor('#187653')
INK = HexColor('#17372D')
MUTED = HexColor('#4D625A')
style = ParagraphStyle('body', fontName='Helvetica', fontSize=10.5, leading=15.5,
                       textColor=INK, alignment=TA_LEFT)
c = canvas.Canvas(str(PDF), pagesize=(W, H))
c.setTitle('GST Easy V2 - Simple User Guide')
c.setAuthor('GST Easy')


def text(value, y, size=10.5, color=INK, width=W-88, x=44):
    s = ParagraphStyle('line', parent=style, fontSize=size, textColor=color)
    p = Paragraph(value, s)
    _, height = p.wrap(width, H)
    p.drawOn(c, x, y-height)
    return y-height


def header(page, subtitle):
    c.setFillColor(GREEN)
    c.rect(0, H-112, W, 112, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 24)
    c.drawString(44, H-49, 'GST Easy V2')
    c.setFont('Helvetica', 12)
    c.drawString(44, H-75, 'Simple user guide | '+subtitle)
    c.setStrokeColor(HexColor('#DCE6E0'))
    c.line(44, 44, W-44, 44)
    c.setFont('Helvetica', 8)
    c.setFillColor(MUTED)
    c.drawString(44, 29, 'Bills & Vouchers  |  19 October 2026')
    c.drawRightString(W-44, 29, f'{page} / 2')
    return H-135


def section(number, title, lines, y):
    y = text(f'<b>{number}. {title}</b>', y, 13, GREEN)-9
    for line in lines:
        y = text(line, y)-7
    return y-8


def note(title, body, y):
    p = Paragraph(f'<b>{title}</b><br/>{body}', style)
    _, height = p.wrap(W-112, H)
    c.setFillColor(HexColor('#EFF6F2'))
    c.roundRect(44, y-height-24, W-88, height+24, 8, fill=1, stroke=0)
    p.drawOn(c, 56, y-height-12)
    return y-height-36


y = header(1, 'Get started and manage bills')
y = text('<b>Open the application</b>', y, 11)-5
y = text('<link href="https://gst-easy-v2-web-foovqasysa-el.a.run.app" color="#187653">https://gst-easy-v2-web-foovqasysa-el.a.run.app</link>', y, 10)-18
y = section('1', 'Sign in and choose your workspace', [
    'Enter your email and password, then select <b>Sign in</b>. Use the eye icon to show or hide your password.',
    'Check the business name and reporting period before working. If you belong to more than one business, use <b>Switch Business</b> in the top-right account menu.',
    '<b>For the populated demo:</b> sign in as <b>naturelabs1@demo.com</b> using the password supplied separately, and select <b>October 2026</b>.'
], y)
y = section('2', 'Check your business details', [
    'Open the account menu &gt; <b>Business Profile</b>. Review the business name, GSTIN, address, contact information, website and logo.',
    'Use the available edit and save controls when authorized. <b>Add Business</b> creates another workspace. Viewers have read-only access.'
], y)
y = section('3', 'Upload, review and confirm bills', [
    '<b>Upload:</b> select <b>Upload Bills</b> from GST Easy or Bills &amp; Vouchers. Choose a supported file and wait for processing. Do not upload several formats of the same invoice.',
    '<b>Review:</b> open the bill and compare the extracted fields with the original. Click the preview or <b>View Original Bill</b> to open the full document.',
    '<b>Check:</b> supplier/customer, invoice number and date, purchase or sale, note type, line items and tax totals. Fix any validation messages and select <b>Save Changes</b>.',
    '<b>Confirm:</b> select <b>Confirm Bill</b> only after checking the details. To reject a bill, enter a reason and select <b>Reject Bill</b>. Follow the confirmation prompt if deleting.'
], y)
y = note('How totals update', 'Confirmed invoices feed the financial totals. Pending and rejected bills do not count as confirmed sales or purchases. Refresh the dashboard after making changes.', y)
assert y > 48, ('Page 1 overflow', y)
c.showPage()

y = header(2, 'Understand results and get help')
y = section('4', 'Read the GST Easy dashboard', [
    'Select the reporting month, then use <b>Refresh dashboard</b>. The nine cards summarize credit, sales tax, estimated cash requirement, purchases, sales and review/reconciliation counts.',
    'Money is shown in INR; review and invoice counts are whole numbers. An unavailable result is not the same as zero. Always check the selected business and period.'
], y)
y = section('5', 'Open detailed reports', [
    'Choose <b>Reports</b> in the sidebar, then <b>Open report</b> for the detail you need:',
    '<b>GST &amp; ITC:</b> usable credit, sales liability, estimated cash requirement and purchases without ITC.<br/><b>Invoice &amp; reconciliation:</b> pending reviews, mismatches and unmatched invoices.<br/><b>Registers:</b> sales and purchases.',
    'Use the available filters and evidence links. Select <b>Back to Reports</b> to return. Exports appear only where supported and permitted.'
], y)
y = section('6', 'Use Returns & Credit', [
    'Review the GST/ITC summary and reconciliation results. To add a statement, choose <b>Import GSTR-2B</b> in Reconciliation Evidence and select a supported JSON file for the same GSTIN and period.',
    'The current importer supports B2B records. Compare matches, differences and missing records using the case filter. A missing statement does not mean there are no mismatches.',
    'Importing a statement does not approve ITC or file a return. Use return-preparation actions only where your account is authorized and the feature is available.'
], y)
y = section('7', 'Find records and manage your account', [
    '<b>Search:</b> find invoice numbers, suppliers or customers; use available period, amount and status filters.',
    '<b>AI Assistant:</b> ask about sales, ITC, pending bills or cash estimates. It is read-only. Check the cited evidence and reports before relying on an answer.',
    '<b>Account menu:</b> open My Profile, Account Settings, Change Password or Help &amp; Support. Select <b>Logout</b> when finished. On mobile, use the bottom navigation and <b>More</b> menu.'
], y)
y = note('Demo boundaries and quick help', 'The demo uses fictional businesses and invoices, not tax-filing documents. Return preparation, approvals and financial exports remain restricted for this test account. Editing demo bills changes its totals. If data looks wrong, check the business and month, then refresh. For access issues, contact your business owner; never share passwords or verification codes.', y)
assert y > 48, ('Page 2 overflow', y)
c.save()
print(PDF)
