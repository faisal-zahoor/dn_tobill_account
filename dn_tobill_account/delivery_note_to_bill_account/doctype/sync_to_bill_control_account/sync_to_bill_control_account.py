# -*- coding: utf-8 -*-
# Copyright (c) 2020, SMB Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from erpnext.accounts.utils import get_company_default
import json,erpnext
from erpnext.accounts.utils import get_balance_on

from frappe.utils import (add_days, getdate, formatdate, date_diff,
	add_years, get_timestamp, nowdate, flt, cstr, add_months, get_last_day)

class SyncToBillControlAccount(Document):
	pass


def make_journal_entry(account1, account2, amount,company,party, cost_center=None,
					posting_date=None, exchange_rate=1,
					save=True, submit=False, project=None, remark=''):

	if not cost_center:
		cost_center = "_Test Cost Center - _TC"

	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date or nowdate()
	jv.company = company
	jv.user_remark = 'Sync To Bill Delivery Notes\n' + remark
	jv.multi_currency = 1
	jv.naming_series = 'PL-JV-.YY.-.#'

	jv.set("accounts", [
		{
			"account": account1,
			"cost_center": cost_center,
			"project": project,
			"debit_in_account_currency": amount if amount > 0 else 0,
			"credit_in_account_currency": abs(amount) if amount < 0 else 0,
			"exchange_rate": exchange_rate,
			"party_type":"Customer",
			"party":party
		}, {
			"account": account2,
			"cost_center": cost_center,
			"project": project,
			"credit_in_account_currency": amount if amount > 0 else 0,
			"debit_in_account_currency": abs(amount) if amount < 0 else 0,
			"exchange_rate": exchange_rate,
			"party_type":"Customer",
			"party":party
		}
	])
	if save or submit:
		jv.insert()

		if submit:
			jv.submit()

	return jv



def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map


@frappe.whitelist()
def get_tobill_dn(doc):
	doc = json.loads(doc)
	from_date = doc.get("from_date")
	to_date = doc.get("to_date")

	# all_dns = frappe.db.sql(""" select
	# 				dni.parent,
	# 				dni.item_code,
	# 				dni.qty,
	# 				dn.status
	# 				from `tabDelivery Note Item` as dni
	# 				join `tabDelivery Note` as dn on dn.name = dni.parent
	# 				where dn.status not in ('Draft', 'Cancelled')
	# 				and dn.status in ('To Bill')
 	# 				""",as_dict=1)
					
	all_dns = frappe.db.sql(""" select
					dni.parent,
					dni.item_code,
					dni.qty,
					dn.status
					from `tabDelivery Note Item` as dni
					join `tabDelivery Note` as dn on dn.name = dni.parent
					where dn.status not in ('Draft', 'Cancelled')
					and dn.status in ('To Bill')
					AND (dn.posting_date) >='{0}'
					AND (dn.posting_date) <='{1}';
 					""".format(from_date,to_date),as_dict=1)


	

	all_dns = list(set([dn.get("parent") for dn in all_dns]))

	print(all_dns,"===")

	# # closeable_dn=prepare_closeable_dn(all_dns)
	# closeable_dn = {}
	# to_bill_closeable = get_to_bill_closeable_dn(from_date,to_date)
	# print(to_bill_closeable,"====closeable_dn")
	# closeable_dn.update(to_bill_closeable)

	return all_dns

@frappe.whitelist()
def sync_control_account(closeable_dn,con_acc_1,con_acc_2):

	closeable_dn = json.loads(closeable_dn)
	party = ''	

	default_company = frappe.db.get_single_value('Global Defaults', 'default_company')
	
	# cost_center = erpnext.get_default_cost_center(default_company)
	
	default_income_account =get_company_default(default_company,"default_income_account")
	
	default_receivable_account =get_company_default(default_company,"default_receivable_account")
	
	default_cash_account =get_company_default(default_company,"default_cash_account")

	invoiced_dns = []
	partial_total =[]
	partial_total_main = []
	fully_to_bill_dn = []
	main_cost_center_total = []
	for dn in closeable_dn:
		res = get_invoiced_qty_map(dn)
		if res:
			for k,v in res.items():
				if v > 0:
					dni_details  = frappe.db.get_value("Delivery Note Item",{"name":k},
							["parent","qty as dn_qty","val_rate","cost_center"], as_dict=1)
							
					valuation_rate_dict = frappe.db.get_value("Stock Ledger Entry",{"voucher_detail_no":k},
							["voucher_detail_no","valuation_rate"], as_dict=1)
							
					valuation_rate = dni_details.get("val_rate")
					if valuation_rate_dict and valuation_rate_dict.get("valuation_rate"):
						valuation_rate = valuation_rate_dict.get("valuation_rate")

					if dni_details:
						invoiced_dns.append(k)
						print(v, dni_details)
						partial_qty_amt = (dni_details.get("dn_qty") - v) * valuation_rate
						if dni_details.get("cost_center") and dni_details.get("cost_center") == "Main SB - SHC":
							partial_total_main.append(partial_qty_amt)
						else:
							partial_total.append(partial_qty_amt)
						
		to_bill_dni_det = frappe.db.get_all("Delivery Note Item",{"parent":dn},
						["name", "qty as dn_qty","val_rate","parent","cost_center"])
						

		ind_t_d_total = 0
		for t_dn in to_bill_dni_det:
			if t_dn.get("name") in invoiced_dns:
				continue
			valuation_rate_dict = frappe.db.get_value("Stock Ledger Entry",{"voucher_detail_no":t_dn.get("name")},
					["voucher_detail_no","valuation_rate"], as_dict=1)
			valuation_rate = t_dn.get("val_rate")
			if valuation_rate_dict and valuation_rate_dict.get("valuation_rate"):
				valuation_rate = valuation_rate_dict.get("valuation_rate")
				
			# ind_t_d_total += t_dn.get("dn_qty") * valuation_rate
			if t_dn.get("cost_center") and t_dn.get("cost_center") == "Main SB - SHC":
				main_cost_center_total.append(t_dn.get("dn_qty") * valuation_rate)
			else:
				fully_to_bill_dn.append(t_dn.get("dn_qty") * valuation_rate)
		
		# fully_to_bill_dn.append(ind_t_d_total)


	total_amount = sum(partial_total) + sum(fully_to_bill_dn)
	balance = get_balance_on(con_acc_1, cost_center="DECOR - SB")
	act_balance = total_amount - balance
	remark = con_acc_1 + ": " + str(balance) + "\nTo Bill Amount Total: " + str(total_amount)
	if act_balance and act_balance != 0:
		make_journal_entry(con_acc_1, con_acc_2, act_balance, default_company, party, cost_center="DECOR - SB", remark=remark)


	total_amount = sum(partial_total_main) + sum(main_cost_center_total)
	balance = get_balance_on(con_acc_1, cost_center="Main SB - SHC")
	act_balance = total_amount - balance
	remark = con_acc_1 + ": " + str(balance) + "\nTo Bill Amount Total: " + str(total_amount)
	if act_balance and act_balance != 0:
		make_journal_entry(con_acc_1, con_acc_2, act_balance, default_company, party, cost_center="Main SB - SHC", remark=remark)
	# if act_balance < 0 :
	# 	make_journal_entry(con_acc_2,con_acc_1,act_balance,default_company,party,cost_center)
	# else:
	# 	make_journal_entry(con_acc_1, con_acc_2, act_balance, default_company, party, cost_center, remark=remark)

	return True

