{
    'name': 'Cargo Fleet Accounting Rent',
    'version': '1.0',
    'summary': 'Suivi comptable des charges et dépenses flotte',
    'category': 'Fleet',
    'author': 'Cargo',
    'depends': [
        'fleet',
        'purchase',
        'account',
        'product',
        'cargo_fleet',  # ton module principal
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_location_tracking_views.xml',
    ],
    'installable': True,
    'application': True,
}