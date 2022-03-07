odoo.define('order_material.QtyWidget', function (require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;

    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    var utils = require('web.utils');

    var _t = core._t;
    var time = require('web.time');

    var QtyWidget = Widget.extend({
        template: 'order_material.qtyStock',
        events: _.extend({}, Widget.prototype.events, {
            'click .fa-area-chart': '_onClickButton',
        }),

        /**
         * @override
         * @param {Widget|null} parent
         * @param {Object} params
         */
        init: function (parent, params) {
            this.data = params.data;
            this.fields = params.fields;
            this._updateData();
            this._super(parent);
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._setPopOver();
            });
        },

        _updateData: function () {
            if (this.data.action) {
                this.data = this.data;
            }
        },

        updateState: function (state) {
            this.$el.popover('dispose');
            var candidate = state.data[this.getParent().currentRow];
            if (candidate) {
                this.data = candidate.data;
                this._updateData();
                this.renderElement();
                this._setPopOver();
            }
        },


        _getContent() {
            if (this.data['product_id'] == false) {
                return
            } else {
                const $content = $(QWeb.render('order_material.QtyDetailPopOver', {
                    data: this.data,
                }));
                return $content;
            }
        },

        _setPopOver() {
            const $content = this._getContent();
            if (!$content) {
                return;
            }
            const options = {
                content: $content,
                html: true,
                placement: 'left',
                title: _t('Availability'),
                trigger: 'focus',
                delay: {'show': 0, 'hide': 100},
            };
            this.$el.popover(options);
        },
        _onClickButton: function () {
            this.$el.find('.fa-area-chart').prop('special_click', true);
        },
    });

    widget_registry.add('qty_stock_widget', QtyWidget);

    return QtyWidget;
});
