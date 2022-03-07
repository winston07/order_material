# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models, _


class CustomMessage(models.TransientModel):
    _name = "material.message.wizard"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)

    def action_done(self):
        context = dict(self._context or {})
        model = context.get('active_model', False)
        m_id = context.get('active_id', False)
        env_model = self.env[model].browse(m_id)
        env_model.btn_done()
