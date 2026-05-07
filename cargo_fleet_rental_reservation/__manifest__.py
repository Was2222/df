# -*- coding: utf-8 -*-
{
    'name': 'Fleet Rental Reservation',
    'version': '19.0.1.0.0',
    'summary': 'Intégration CRM pour la gestion des réservations de véhicules',
    'description': """
        Ce module ajoute le workflow CRM complet pour la location de véhicules :
        
        Workflow :
        1. En saisie        → statut réservation : initial
        2. Qualifié         → statut réservation : initial
        3. Proposition      → statut réservation : initial
        4. Confirmé         → statut réservation : confirmé  (avec contrôles)
        5. Converti contrat → statut réservation : converti en contrat
        6. Annulé           → statut réservation : annulé
    """,
    'author': 'Your Company',
    'category': 'Fleet/CRM',
    'depends': [
        'sale',
        'sale_crm',
        'crm',
        'fleet_rental',
        'sale_management',
       
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_stage_rental.xml',
        'data/sequence.xml',
        'views/crm_lead_rental_views.xml',
        #'views/crm_lead_kanban_views.xml',
        'views/sale_order_rental_views.xml',
        'wizard/convert_to_contract_wizard_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
