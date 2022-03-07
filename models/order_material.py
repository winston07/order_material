# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class OrderMaterial(models.Model):
    _name = "order.material"

    name = fields.Char(
        'Name', copy=False, readonly=True, default=lambda x: _('New'))
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda s: s.env.company,
        required=True, index=True, states={'done': [('readonly', True)]})
    employee_id = fields.Many2one('res.partner', string="Employee", required=True)

    application_date = fields.Date(string="Application Date", required=True, default=fields.Datetime.now())
    order_date = fields.Date(string="Order Date", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State', default='draft', copy=False, index=True, readonly=True)
    internal_picking_count = fields.Integer(string="Internal Picking", compute="_compute_picking")
    purchase_order_count = fields.Integer(string="Purchase Order", compute="_compute_purchase")

    lines_ids = fields.One2many('order.material.detail', 'order_material_id', 'Detail', copy=True)
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Name must be unique per Company!'),
    ]

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('order.material') or _('New')
        resp = super(OrderMaterial, self).create(values)
        return resp

    def action_confirm(self):
        purchase = self.lines_ids.filtered(lambda s: s.action == 'purchase_order')
        if len(purchase) > 0:
            view = self.env.ref('order_material.material_message_wizard')
            view_id = view and view.id or False
            context = dict(self._context or {})
            text = _("The Order for materials contains products without sufficient "
                     "stock, so a Request for Quotation to be confirmed / validated "
                     "will be automatically generated.")
            context['message'] = text
            context['order_material'] = self
            return {
                'name': _('Stop'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'material.message.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': context
            }
        else:
            self.stock_picking()
            self.order_date = fields.Datetime.now()
            self.state = 'done'

    def btn_done(self):
        self.stock_picking()
        self.stock_picking_po()
        self.order_date = fields.Datetime.now()
        self.state = 'done'

    def stock_picking(self):
        lines = []
        for line in self.lines_ids.filtered(lambda s: s.action == 'internal_picking'):
            line = ({'product_id': line.product_id.id,
                     'name': line.product_id.name,
                     'product_uom_qty': line.qty, 'product_uom': line.product_id.uom_id.id})
            lines.append((0, 0, line))
        picking_type_id = self.env['stock.picking.type'].search(
            [('sequence_code', '=', 'OUT'), ('code', '=', 'outgoing')], limit=1)
        loc_dst = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        vals = {'partner_id': self.employee_id.id,
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': loc_dst.id or picking_type_id.default_location_dest_id.id,
                'origin': self.name,
                'scheduled_date': fields.Datetime.now(),
                'order_material_picking_id': self.id,
                'move_ids_without_package': lines}
        if len(lines) > 0:
            stock_picking = self.env['stock.picking'].create(vals)
            stock_picking.action_confirm()
            stock_picking.action_assign()

    def stock_picking_po(self):
        lines = []
        for line in self.lines_ids.filtered(lambda s: s.action == 'purchase_order'):
            line = ({'product_id': line.product_id.id,
                     'name': line.product_id.name,
                     'product_qty': line.qty, 'price_unit': line.product_id.standard_price})
            lines.append((0, 0, line))

        vals = {'partner_id': self.employee_id.id,
                'date_order': fields.Datetime.now(),
                'order_material_po_id': self.id,
                'order_line': lines}
        if len(lines) > 0:
            purchase_order = self.env['purchase.order'].create(vals)
            purchase_order.button_confirm()

    def action_cancel(self):
        for order in self:
            if order.purchase_order_count > 0 or order.internal_picking_count > 0:
                internal_picking = self.env['stock.picking'].search(
                    [('order_material_picking_id', '=', self.id), ('state', '=', 'done')], limit=1)
                purchase = self.env['purchase.order'].search([('order_material_po_id', '=', self.id)], limit=1)
                purchase_picking = self.env['stock.picking'].search(
                    [('origin', '=', purchase.name), ('state', '=', 'done')], limit=1)
                if internal_picking or purchase_picking:
                    raise UserError(
                        _('Cannot cancel the order, stock picking has already been validated.'))
                else:
                    order.state = 'cancel'
            else:
                order.state = 'cancel'

    def unlink(self):
        for rec in self:
            if rec.state in ['done']:
                raise UserError(
                    _('Cannot be deleted in done state'))
        result = super(OrderMaterial, self).unlink()
        return result

    def _compute_picking(self):
        for rec in self:
            picking = self.env['stock.picking'].search_count([('order_material_picking_id', '=', rec.id)])
            rec.internal_picking_count = picking

    def _compute_purchase(self):
        for rec in self:
            po_ids = self.env['purchase.order'].search_count([('order_material_po_id', '=', rec.id)])
            rec.purchase_order_count = po_ids

    def action_view_picking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale',
            'res_model': 'stock.picking',
            'domain': [('order_material_picking_id', '=', self.id)],
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_view_purchase(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase',
            'res_model': 'purchase.order',
            'domain': [('order_material_po_id', '=', self.id)],
            'view_mode': 'tree,form',
            'target': 'current'
        }


class OrderMaterialDetail(models.Model):
    _name = "order.material.detail"

    order_material_id = fields.Many2one('order.material', check_company=True, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string="Description")
    qty = fields.Float(string="Quantity", default=1.0)
    available_qty = fields.Float(string="Available Quantity")
    reserved_qty = fields.Float(string="Reserved Quantity")
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    action = fields.Selection(
        [('purchase_order', 'Purchase Order'), ('internal_picking', 'Internal Picking')], string="Action",
        default='internal_picking')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')

    @api.depends('product_id', 'qty', 'order_material_id.state')
    def _compute_qty_to_deliver(self):
        if self.order_material_id.state != 'draft':
            self.display_qty_widget = False
        else:
            self.display_qty_widget = True

    @api.onchange('product_id', 'qty')
    def onchange_product_qty(self):
        # default values
        self.description = "[%s]%s" % (self.product_id.default_code, self.product_id.name)
        self.uom_id = self.product_id.uom_id.id
        location = self.env['stock.location'].sudo().search(
            [('name', '=', 'Stock'), ('company_id', '=', self.company_id.id)], limit=1)
        stock_quant_env = self.env['stock.quant'].sudo().search(
            [('product_id', '=', self.product_id.id), ('location_id', '=', location.id),
             ('company_id', '=', self.company_id.id)])
        if stock_quant_env:
            self.reserved_qty = stock_quant_env.reserved_quantity
            self.available_qty = stock_quant_env.available_quantity
        if self.qty > self.available_qty:
            self.action = 'purchase_order'
        else:
            self.action = 'internal_picking'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    order_material_picking_id = fields.Many2one('order.material', string="Order Material")


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    order_material_po_id = fields.Many2one('order.material', string="Order Material")
