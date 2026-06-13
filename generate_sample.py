"""
generate_sample.py
Creates sample_data/synthetic_contract.pdf -- a FICTIONAL contract
(Acme Staffing Pte Ltd / Alex Tan) seeded with red flags for
testing and the live demo. Never use a real uploaded contract.

Requires: pip install fpdf2
"""

import os
from fpdf import FPDF

CONTRACT_TEXT = """LETTER OF APPOINTMENT
Acme Staffing Pte Ltd

Dear Alex Tan,

We are pleased to offer you the position of L1 Support Analyst, deployed
to a client site, under the following terms.

Employee Particulars (fictional - for testing only)
NRIC: S9123456A
Email: alex.tan@example.com
Mobile: +65 9123 4567
Address: Blk 123 Clementi Ave 3 #12-345 Singapore 120123

Schedule 1 - Employment Details
Contract Period: 1 January 2026 to 30 June 2026
Designation: L1 Support Analyst
Basic Salary: S$3,000.00 per month

Program Bond (applicable for first employment contract only and
fulfilment of the Government Traineeship Programme):
The employee agrees to fulfil the program bond of 6- or 12-months.
In the event of resignation or failure to fulfil the full tenure period
of the employment contract, the company shall recover reasonable costs
of the program up to the equivalent of 1 month's salary as well as any
training-related expenses incurred for this position.

Termination Notice (Company): The Company may terminate this contract
by giving the employee 3 days' notice.
Termination Notice (Employee): The employee must give the Company one
(1) calendar month's notice.

Compassionate Leave: Compassionate leave may be granted at the sole
discretion of management on a case-by-case basis.

Training Form Note (Internal HR use): Government Traineeship Programme
bond in force during contract period.

The Company reserves the right to modify any terms of this agreement
at its sole discretion at any time.
"""


def generate_pdf(output_path="sample_data/synthetic_contract.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    pdf.multi_cell(0, 6, CONTRACT_TEXT)

    pdf.output(output_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    generate_pdf()