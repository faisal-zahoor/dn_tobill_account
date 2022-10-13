// Copyright (c) 2020, SMB Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sync To Bill Control Account', {
  get_records:function(frm){
		frm.trigger("fetch_tobill_dn")
	},

  fetch_tobill_dn:function(frm){

			frappe.call({
			method:"dn_tobill_account.delivery_note_to_bill_account.doctype.sync_to_bill_control_account.sync_to_bill_control_account.get_tobill_dn",
			args: {
					doc:frm.doc
				},
			freeze: true,
			freeze_message: __("Processing"),
			callback: function (r) {
					var records = []
					
					$.each(r.message,function(k,v){
						records.push(v)
					})

					frm.events.prepare_and_render_html(frm,records,"delivery_notes")

			}
		})

	},

	prepare_and_render_html:function(frm, records, type){
			var rec_html_wraper=frm.fields_dict.records_html.$wrapper
			rec_html_wraper.html("")
			var html_line='';
			$.each(records, function(i, record) {
				console.log("aaaaa",record)

				if (i===0 || (i % 4) === 0) {
					html_line = $('<div class="row"></div>').appendTo(rec_html_wraper);
				}
				$(repl('<div class="col-xs-6 return-invoice-checkbox">\
					<div class="checkbox">\
					<label><input type="checkbox" class="%(rec_type)s" %(rec_type)s="%(rec_name)s" \
					checked=True/>\
					<b>%(rec_name)s </b></label>\
					</div></div>', {rec_name: record, rec_type:type})).appendTo(html_line);
			})

	},

  process:function(frm){

		var closeable_dn=[]

		var rec_html_wraper=frm.fields_dict.records_html.$wrapper
		$.each(rec_html_wraper.find('.delivery_notes:checked'), function(i, act){
			closeable_dn.push($(this).attr('delivery_notes'))
		})

		frappe.call({
			method:"dn_tobill_account.delivery_note_to_bill_account.doctype.sync_to_bill_control_account.sync_to_bill_control_account.sync_control_account",
			args: {
					closeable_dn:closeable_dn,
					"con_acc_1":frm.doc.account_1,
					"con_acc_2":frm.doc.account_2,

				},
			freeze: true,
			freeze_message: __("Processing"),
			callback: function (r) {
				frm.trigger("fetch_closable_dn")

			}
		})
	}
});
