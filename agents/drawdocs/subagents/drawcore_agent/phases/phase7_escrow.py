"""
Phase 7: Escrow Calculations

Calculates and updates Aggregate Escrow Account fields based on SOP Step 19.
This phase handles:
- Cushion month calculations (2 for taxes/insurance, 0 for MI)
- Starting balance calculations
- State-specific tax calculations (NV, CA, CO, TX)
- Escrow setup (due dates, monthly amounts)

Based on: Docs Draw SOP Step 19 (Lines 496-537)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, write_fields, log_issue

logger = logging.getLogger(__name__)


# Field mappings for Phase 7 - Escrow Calculations
ESCROW_FIELDS = {
    # Input fields (needed for calculations)
    "748": {"name": "Closing Date", "type": "input"},
    "230": {"name": "Monthly Hazard Insurance", "type": "input"},
    "235": {"name": "Monthly Flood Insurance", "type": "input"},
    "231": {"name": "Monthly Property Tax", "type": "input"},
    "1296": {"name": "Monthly Mortgage Insurance", "type": "input"},
    "1109": {"name": "Loan Amount", "type": "input"},
    "14": {"name": "Property State", "type": "input"},
    "19": {"name": "Property Type", "type": "input"},
    "1811": {"name": "Sales Price", "type": "input"},
    
    # Output fields (calculated and written)
    "ESC.X100": {"name": "Escrow Tax Cushion Months", "type": "output"},
    "ESC.X101": {"name": "Escrow Insurance Cushion Months", "type": "output"},
    "ESC.X102": {"name": "Escrow MI Cushion Months", "type": "output"},
    "ESC.X103": {"name": "Escrow Starting Balance", "type": "output"},
    "ESC.X104": {"name": "Escrow First Payment Date", "type": "output"},
}


def calculate_first_payment_date(closing_date: str) -> str:
    """
    Calculate first payment date (1 month after closing date).
    
    Example: Closing Date = 01/24/2019 → First Payment = 03/01/2019
    
    Args:
        closing_date: Closing date string (YYYY-MM-DD format)
        
    Returns:
        First payment date string (YYYY-MM-DD format)
    """
    try:
        if 'T' in closing_date:
            close_dt = datetime.fromisoformat(closing_date.split('T')[0])
        else:
            close_dt = datetime.strptime(closing_date[:10], "%Y-%m-%d")
        
        # First payment is first day of month, 1 month after closing
        first_payment = close_dt + relativedelta(months=1)
        first_payment = first_payment.replace(day=1)
        
        return first_payment.strftime("%Y-%m-%d")
    
    except Exception as e:
        logger.error(f"[ESCROW] Error calculating first payment date: {e}")
        return ""


def calculate_state_specific_monthly_tax(
    state: str,
    property_type: str,
    sales_price: float,
    tax_summary_amount: Optional[float] = None
) -> Optional[float]:
    """
    Calculate monthly property tax based on state-specific rules.
    
    Based on SOP Step 19 (Lines 513-526):
    - NV, AZ: 1% of sales price / 12
    - CA: 1.25% of sales price / 12 (or tax summary, whichever is higher)
    - CO: Mill Levy calculation or 1% of sales price (UW decision)
    - Other states: Use tax summary
    
    Args:
        state: Property state (CA, NV, AZ, CO, etc.)
        property_type: Property type (new construction, resale, etc.)
        sales_price: Sales price from purchase contract
        tax_summary_amount: Monthly tax from tax summary (if available)
        
    Returns:
        Calculated monthly tax amount or None if cannot calculate
    """
    state = state.upper() if state else ""
    
    logger.info(f"[ESCROW] Calculating monthly tax for {state} state...")
    
    # Nevada and Arizona: 1% of sales price / 12
    if state in ["NV", "NEVADA", "AZ", "ARIZONA"]:
        if sales_price:
            monthly_tax = (sales_price * 0.01) / 12
            logger.info(f"[ESCROW] {state} calculation: {sales_price} * 0.01 / 12 = ${monthly_tax:.2f}")
            return monthly_tax
    
    # California: 1.25% of sales price / 12 vs tax summary (whichever is higher)
    elif state in ["CA", "CALIFORNIA"]:
        if sales_price:
            calc_tax = (sales_price * 0.0125) / 12
            logger.info(f"[ESCROW] CA calculation: {sales_price} * 0.0125 / 12 = ${calc_tax:.2f}")
            
            if tax_summary_amount:
                monthly_tax = max(calc_tax, tax_summary_amount)
                logger.info(f"[ESCROW] CA uses higher of calculated (${calc_tax:.2f}) or tax summary (${tax_summary_amount:.2f}) = ${monthly_tax:.2f}")
                return monthly_tax
            else:
                return calc_tax
    
    # Colorado: Use mill levy or 1% (typically UW decision, default to tax summary)
    elif state in ["CO", "COLORADO"]:
        logger.info(f"[ESCROW] CO state - using tax summary: ${tax_summary_amount:.2f}")
        return tax_summary_amount
    
    # Other states: Use tax summary
    else:
        if tax_summary_amount:
            logger.info(f"[ESCROW] {state} - using tax summary: ${tax_summary_amount:.2f}")
            return tax_summary_amount
    
    logger.warning(f"[ESCROW] Cannot calculate monthly tax for {state} - insufficient data")
    return None


def calculate_escrow_account(
    monthly_tax: float,
    monthly_insurance: float,
    monthly_mi: float = 0.0,
    monthly_flood: float = 0.0,
    closing_date: str = None
) -> Dict[str, Any]:
    """
    Calculate escrow account fields based on SOP rules.
    
    Based on SOP Step 19:
    - Cushion: 2 months for taxes/insurance, 0 for MI
    - Starting balance: Must stay positive
    
    Args:
        monthly_tax: Monthly property tax
        monthly_insurance: Monthly hazard insurance
        monthly_mi: Monthly mortgage insurance (if applicable)
        monthly_flood: Monthly flood insurance (if applicable)
        closing_date: Loan closing date
        
    Returns:
        Dictionary of calculated escrow fields
    """
    logger.info(f"[ESCROW] Calculating escrow account...")
    logger.info(f"[ESCROW]   Monthly Tax: ${monthly_tax:.2f}")
    logger.info(f"[ESCROW]   Monthly Insurance: ${monthly_insurance:.2f}")
    logger.info(f"[ESCROW]   Monthly MI: ${monthly_mi:.2f}")
    logger.info(f"[ESCROW]   Monthly Flood: ${monthly_flood:.2f}")
    
    escrow_data = {
        # Cushion months (from SOP)
        "tax_cushion": 2,
        "insurance_cushion": 2,
        "mi_cushion": 0,
        
        # Calculate starting balance
        # Formula: (monthly amounts * cushion months) = initial deposit
        "starting_balance": (
            (monthly_tax * 2) +
            (monthly_insurance * 2) +
            (monthly_flood * 2) +
            (monthly_mi * 0)  # No cushion for MI
        )
    }
    
    # Calculate first payment date
    if closing_date:
        escrow_data["first_payment_date"] = calculate_first_payment_date(closing_date)
    
    logger.info(f"[ESCROW] ✅ Calculated escrow:")
    logger.info(f"[ESCROW]   Tax cushion: {escrow_data['tax_cushion']} months")
    logger.info(f"[ESCROW]   Insurance cushion: {escrow_data['insurance_cushion']} months")
    logger.info(f"[ESCROW]   MI cushion: {escrow_data['mi_cushion']} months")
    logger.info(f"[ESCROW]   Starting balance: ${escrow_data['starting_balance']:.2f}")
    
    # Verify starting balance is positive
    if escrow_data["starting_balance"] < 0:
        logger.error(f"[ESCROW] ❌ Starting balance is negative: ${escrow_data['starting_balance']:.2f}")
        escrow_data["error"] = "Starting balance must be positive"
    
    return escrow_data


def process_escrow_phase(
    loan_id: str,
    doc_context: Dict[str, Any],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Process Phase 7: Escrow Calculations.
    
    Args:
        loan_id: Encompass loan GUID
        doc_context: Prep Agent output with extracted field values
        dry_run: If True, don't actually write to Encompass
        
    Returns:
        Dictionary with phase results
    """
    logger.info("[PHASE 7] Escrow Calculations - Starting")
    
    result = {
        "status": "in_progress",
        "fields_processed": 0,
        "fields_updated": 0,
        "issues_logged": 0,
        "updates": [],
        "issues": [],
        "calculations": {}
    }
    
    try:
        # Get input field IDs
        input_field_ids = [fid for fid, info in ESCROW_FIELDS.items() if info["type"] == "input"]
        
        # Read current values from Encompass
        logger.info(f"[PHASE 7] Reading {len(input_field_ids)} input fields...")
        field_values = read_fields(loan_id, input_field_ids)
        
        # Extract required values
        monthly_tax = field_values.get("231")  # Monthly Property Tax
        monthly_insurance = field_values.get("230")  # Monthly Hazard Insurance
        monthly_mi = field_values.get("1296", 0)  # Monthly MI (if applicable)
        monthly_flood = field_values.get("235", 0)  # Monthly Flood Insurance (if applicable)
        closing_date = field_values.get("748")
        state = field_values.get("14", "")
        property_type = field_values.get("19", "")
        sales_price = field_values.get("1811")
        
        # Check if we have minimum required fields
        if not monthly_tax or not monthly_insurance:
            logger.warning("[PHASE 7] Missing required monthly amounts - skipping escrow calculations")
            result["status"] = "skipped"
            result["issues"].append({
                "type": "warning",
                "message": "Missing monthly tax or insurance amounts - cannot calculate escrow"
            })
            return result
        
        # Convert to floats (strip commas first)
        try:
            # Helper to clean and convert numeric strings
            def clean_float(value):
                if not value or value == "":
                    return 0
                # Remove commas and convert to float
                return float(str(value).replace(",", ""))
            
            monthly_tax = clean_float(monthly_tax)
            monthly_insurance = clean_float(monthly_insurance)
            monthly_mi = clean_float(monthly_mi)
            monthly_flood = clean_float(monthly_flood)
        except (ValueError, TypeError) as e:
            logger.error(f"[PHASE 7] Error converting amounts to float: {e}")
            logger.error(f"[PHASE 7] Values: tax={monthly_tax}, insurance={monthly_insurance}, mi={monthly_mi}, flood={monthly_flood}")
            result["status"] = "failed"
            result["issues"].append({
                "type": "error",
                "message": f"Invalid monthly amounts: {str(e)}"
            })
            return result
        
        # Calculate escrow account
        escrow_calc = calculate_escrow_account(
            monthly_tax=monthly_tax,
            monthly_insurance=monthly_insurance,
            monthly_mi=monthly_mi,
            monthly_flood=monthly_flood,
            closing_date=closing_date
        )
        
        result["calculations"] = escrow_calc
        
        # Check for calculation errors
        if "error" in escrow_calc:
            logger.error(f"[PHASE 7] Calculation error: {escrow_calc['error']}")
            result["status"] = "failed"
            result["issues"].append({
                "type": "error",
                "message": escrow_calc["error"]
            })
            log_issue(
                loan_id=loan_id,
                issue_type="critical",
                message=f"Escrow calculation error: {escrow_calc['error']}"
            )
            return result
        
        # Prepare updates for Encompass
        updates = {
            "ESC.X100": escrow_calc["tax_cushion"],
            "ESC.X101": escrow_calc["insurance_cushion"],
            "ESC.X102": escrow_calc["mi_cushion"],
            "ESC.X103": escrow_calc["starting_balance"],
        }
        
        if "first_payment_date" in escrow_calc:
            updates["ESC.X104"] = escrow_calc["first_payment_date"]
        
        result["fields_processed"] = len(updates)
        
        # Write to Encompass
        if not dry_run:
            logger.info(f"[PHASE 7] Writing {len(updates)} escrow fields to Encompass...")
            try:
                success = write_fields(loan_id, updates)
                if success:
                    result["fields_updated"] = len(updates)
                    result["status"] = "success"
                    result["updates"] = [
                        {
                            "field_id": fid,
                            "field_name": ESCROW_FIELDS.get(fid, {}).get("name", fid),
                            "value": val,
                            "written": True
                        }
                        for fid, val in updates.items()
                    ]
                    logger.info(f"[PHASE 7] ✅ Successfully wrote {len(updates)} escrow fields")
                else:
                    raise RuntimeError("Write operation failed")
            
            except Exception as e:
                logger.error(f"[PHASE 7] Error writing fields: {e}")
                result["status"] = "failed"
                result["issues"].append({
                    "type": "error",
                    "message": f"Failed to write escrow fields: {str(e)}"
                })
                log_issue(
                    loan_id=loan_id,
                    issue_type="error",
                    message=f"Escrow field write failed: {str(e)}"
                )
                return result
        else:
            # Dry run
            result["fields_updated"] = len(updates)
            result["status"] = "success"
            result["updates"] = [
                {
                    "field_id": fid,
                    "field_name": ESCROW_FIELDS.get(fid, {}).get("name", fid),
                    "value": val,
                    "written": False,
                    "dry_run": True
                }
                for fid, val in updates.items()
            ]
            logger.info(f"[PHASE 7] 🔍 DRY RUN - Would write {len(updates)} escrow fields")
        
        logger.info(f"[PHASE 7] Complete - {result['fields_processed']} processed, "
                   f"{result['fields_updated']} updated, {result['issues_logged']} issues")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7] Failed: {e}", exc_info=True)
        result["status"] = "failed"
        result["issues"].append({
            "type": "error",
            "message": f"Phase 7 failed: {str(e)}"
        })
        return result


def calculate_state_tax_if_new_construction(
    state: str,
    sales_price: float,
    property_type: str,
    tax_summary: Optional[float] = None
) -> Optional[float]:
    """
    Calculate monthly tax for new construction properties based on state rules.
    
    This function should be called when property is new construction or under construction.
    
    Args:
        state: Property state
        sales_price: Purchase price
        property_type: new_construction, under_construction, or resale
        tax_summary: Monthly tax from tax summary (fallback)
        
    Returns:
        Calculated monthly tax or None
    """
    state = state.upper()
    
    if property_type.lower() in ["new_construction", "under_construction"]:
        result = calculate_state_specific_monthly_tax(state, property_type, sales_price, tax_summary)
        if result:
            logger.info(f"[ESCROW] New construction tax calculation for {state}: ${result:.2f}/month")
            return result
    
    # Not new construction or cannot calculate
    if tax_summary:
        logger.info(f"[ESCROW] Using tax summary for {state}: ${tax_summary:.2f}/month")
        return tax_summary
    
    return None





