from . import models


def post_init_hook(env):
    env["ir.ui.menu"].sudo().force_fleet_menu_labels_fr()