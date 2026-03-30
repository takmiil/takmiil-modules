from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError


class TakJournalTransfer(models.Model):
    _name = "tak.journal.transfer"
    _description = "Journal Transfer"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ============================================
    # FIELDS
    # ============================================
    
    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )

    date = fields.Date(
        string="Date", required=True, default=fields.Date.context_today, tracking=True
    )

    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")],
        string="Status",
        default="draft",
        tracking=True,
    )

    # Source Journal
    source_journal_id = fields.Many2one(
        "account.journal",
        string="Source Journal",
        required=True,
        tracking=True,
        check_company=True,
    )

    source_balance = fields.Monetary(
        string="Source Balance",
        currency_field="company_currency_id",
        compute="_compute_source_balance",
        store=True,
        readonly=True,
    )

    # Destination Journal
    destination_journal_id = fields.Many2one(
        "account.journal",
        string="Destination Journal",
        required=True,
        tracking=True,
        check_company=True,
    )

    destination_balance = fields.Monetary(
        string="Destination Balance",
        currency_field="company_currency_id",
        compute="_compute_destination_balance",
        store=True,
        readonly=True,
    )

    # Amount
    amount = fields.Monetary(
        string="Transfer Amount",
        currency_field="company_currency_id",
        required=True,
        tracking=True,
    )

    # Currency & Company
    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="company_currency_id", store=True
    )

    company_currency_id = fields.Many2one(
        "res.currency",
        string="Company Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    # Journal Entries (One2many instead of payments)
    move_ids = fields.One2many(
        "account.move",
        "tak_transfer_id",
        string="Journal Entries",
        readonly=True,
        copy=False,
        tracking=True,
    )

    move_count = fields.Integer(
        string="Entry Count", compute="_compute_move_count", store=True
    )

    is_reconciled = fields.Boolean(
        string="Fully Reconciled", compute="_compute_is_reconciled", store=True
    )

    notes = fields.Text(
        string="Notes",
        help="Description used for journal entries reference and line labels",
    )

    
    # ============================================
    # ON CHANGE METHODS
    # ============================================
    
    @api.onchange('source_journal_id')
    def _onchange_source_journal_id(self):
        for rec in self:
            rec.amount = rec.source_balance
    
    

    # ============================================
    # COMPUTE METHODS
    # ============================================

    @api.depends("source_journal_id", "date", "company_id")
    def _compute_source_balance(self):
        for record in self:
            if record.source_journal_id:
                account = record.source_journal_id.default_account_id
                if account:
                    balance = account.with_context(
                        date_to=record.date or fields.Date.today()
                    ).current_balance
                    record.source_balance = balance
                else:
                    record.source_balance = 0.0
            else:
                record.source_balance = 0.0

    @api.depends("destination_journal_id", "date", "company_id")
    def _compute_destination_balance(self):
        for record in self:
            if record.destination_journal_id:
                account = record.destination_journal_id.default_account_id
                if account:
                    balance = account.with_context(
                        date_to=record.date or fields.Date.today()
                    ).current_balance
                    record.destination_balance = balance
                else:
                    record.destination_balance = 0.0
            else:
                record.destination_balance = 0.0

    @api.depends("move_ids")
    def _compute_move_count(self):
        for record in self:
            record.move_count = len(record.move_ids)

    @api.depends("move_ids", "move_ids.state", "move_ids.line_ids.reconciled")
    def _compute_is_reconciled(self):
        for record in self:
            if not record.move_ids:
                record.is_reconciled = False
            else:
                # Check if all liquidity lines are reconciled
                all_lines = record.move_ids.line_ids
                liquidity_account = record.company_id.transfer_account_id
                if liquidity_account:
                    liquidity_lines = all_lines.filtered(
                        lambda l: l.account_id == liquidity_account and not l.reconciled
                    )
                    record.is_reconciled = not liquidity_lines
                else:
                    record.is_reconciled = all(
                        m.state == "posted" for m in record.move_ids
                    )

    # ============================================
    # CONSTRAINTS
    # ============================================

    @api.constrains("source_journal_id", "destination_journal_id")
    def _check_different_journals(self):
        for record in self:
            if record.source_journal_id and record.destination_journal_id:
                if record.source_journal_id == record.destination_journal_id:
                    raise ValidationError(
                        _("Source and Destination journals must be different!")
                    )

    @api.constrains("amount")
    def _check_positive_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Transfer amount must be positive!"))

    @api.constrains("amount", "source_balance")
    def _check_sufficient_funds(self):
        for record in self:
            if record.state == "draft" and record.amount > record.source_balance:
                raise ValidationError(
                    _(
                        "Insufficient funds in source journal! Available: %s, Required: %s"
                    )
                    % (record.source_balance, record.amount)
                )

    # ============================================
    # HELPER METHODS
    # ============================================

    def _get_transfer_description(self, direction="out"):
        """Generate description for journal entries"""
        self.ensure_one()

        # Use notes if provided, otherwise generate default
        if self.notes and self.notes.strip():
            base_desc = self.notes.strip()
        else:
            # Default description
            if direction == "out":
                base_desc = _("Transfer from %s") % self.source_journal_id.name
            else:
                base_desc = _("Transfer to %s") % self.destination_journal_id.name

        return base_desc

    # ============================================
    # BUTTON FUNCTIONS
    # ============================================

    def action_confirm(self):
        """Execute two-step transfer using journal entries: Source → Liquidity → Destination"""
        self.ensure_one()

        if self.state != "draft":
            raise UserError(_("Only draft transfers can be confirmed!"))

        # Get liquidity transfer account from company settings
        liquidity_account = self.company_id.transfer_account_id
        if not liquidity_account:
            raise UserError(
                _(
                    "No liquidity transfer account configured! "
                    "Please set it in Accounting Settings (Default Accounts)."
                )
            )

        # Get source and destination accounts
        source_account = self.source_journal_id.default_account_id
        destination_account = self.destination_journal_id.default_account_id

        if not source_account:
            raise UserError(_("Source journal has no default account!"))
        if not destination_account:
            raise UserError(_("Destination journal has no default account!"))

        # ==========================================
        # MOVE 1: Source Journal → Liquidity Account
        # ==========================================
        description_out = self._get_transfer_description(direction="out")

        move_out_vals = {
            "journal_id": self.source_journal_id.id,
            "date": self.date,
            "ref": description_out,
            "tak_transfer_id": self.id,
            "company_id": self.company_id.id,
            "line_ids": [
                # Credit Source Account (money leaving source)
                (
                    0,
                    0,
                    {
                        "account_id": liquidity_account.id,
                        "debit": self.amount,
                        "credit": 0.0,
                        "name": _("From %s to %s") % (self.source_journal_id.name, self.destination_journal_id.name),
                        "date": self.date,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": source_account.id,
                        "credit": self.amount,
                        "debit": 0.0,
                        "name": _("From %s to %s") % (self.source_journal_id.name, self.destination_journal_id.name),
                        "date": self.date,
                    },
                ),
                # Debit Liquidity Account (money entering transit)
            ],
        }

        move_out = self.env["account.move"].create(move_out_vals)
        move_out.action_post()

        # ==========================================
        # MOVE 2: Liquidity Account → Destination Journal
        # ==========================================
        description_in = self._get_transfer_description(direction="in")

        move_in_vals = {
            "journal_id": self.destination_journal_id.id,
            "date": self.date,
            "ref": description_in,
            "tak_transfer_id": self.id,
            "company_id": self.company_id.id,
            "line_ids": [
                # Debit Destination Account (money arriving)
                (
                    0,
                    0,
                    {
                        "account_id": destination_account.id,
                        "debit": self.amount,
                        "credit": 0.0,
                        "name": _("From %s to %s") % (self.source_journal_id.name, self.destination_journal_id.name),
                        "date": self.date,
                    },
                ),
                
                 # Credit Liquidity Account (money leaving transit)
                (
                    0,
                    0,
                    {
                        "account_id": liquidity_account.id,
                        "credit": self.amount,
                        "debit": 0.0,
                        "name": _("From %s to %s") % (self.source_journal_id.name, self.destination_journal_id.name),
                        "date": self.date,
                    },
                ),
            ],
        }

        move_in = self.env["account.move"].create(move_in_vals)
        move_in.action_post()

        # ==========================================
        # AUTO-RECONCILE LIQUIDITY LINES
        # ==========================================
        self._reconcile_liquidity_lines(move_out, move_in, liquidity_account)

        # Update state
        self.write(
            {
                "state": "posted",
                "name": self.env["ir.sequence"].next_by_code("tak.journal.transfer")
                or _("New"),
            }
        )

    def _reconcile_liquidity_lines(self, move_out, move_in, liquidity_account):
        """Auto-reconcile the liquidity account lines from both moves"""
        # Get liquidity lines from outgoing move (debit)
        liquidity_lines_out = move_out.line_ids.filtered(
            lambda l: l.account_id == liquidity_account
            and l.debit > 0
            and not l.reconciled
        )

        # Get liquidity lines from incoming move (credit)
        liquidity_lines_in = move_in.line_ids.filtered(
            lambda l: l.account_id == liquidity_account
            and l.credit > 0
            and not l.reconciled
        )

        if liquidity_lines_out and liquidity_lines_in:
            # Combine and reconcile
            lines_to_reconcile = liquidity_lines_out + liquidity_lines_in
            if len(lines_to_reconcile) >= 2:
                lines_to_reconcile.reconcile()

    def action_reset_to_draft(self):
        """Reset p record back to draft"""
        self.ensure_one()

        if self.state != "posted":
            raise UserError(_("Only posted records can be reset to draft!"))

        # Draft and Unlink original moves (optional: keep for history)
        self.move_ids.button_draft()
        self.move_ids.unlink()

        self.write(
            {
                "state": "draft",
            }
        )

    def action_cancel(self):
        """Cancel the transfer"""
        self.ensure_one()
        if self.state not in ["draft", "posted"]:
            raise UserError(_("Cannot cancel this transfer!"))

        if self.state == "posted" and self.move_ids:
            raise UserError(
                _("Please reset to draft first before cancelling!"))

        self.write({"state": "cancelled"})

    # ============================================
    # SMART BUTTON ACTION
    # ============================================

    def action_view_moves(self):
        """Open journal entries related to this transfer"""
        self.ensure_one()
        list_view = self.env.ref("account.view_move_tree")
        form_view = self.env.ref("account.view_move_form")
        action = {
            "name": _("Journal Entries"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("tak_transfer_id", "=", self.id)],
            "views": [(list_view.id, "list"), (form_view.id, "form")],
            "context": {
                "default_tak_transfer_id": self.id,
                "create": False,
            },
        }
        return action

    # ============================================
    # ORM OVERRIDES
    # ============================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "tak.journal.transfer"
                ) or _("New")
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            if record.state not in ("draft", "cancelled"):
                raise UserError(
                    "You cannot delete a document which is not draft or cancelled!")
        return super(TakJournalTransfer, self).unlink()
