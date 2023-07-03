# Game Components for the Game Profile module
#

from odoo import models, fields, api, _


# This module includes models for Games and GameProfiles. 
# GameProfiles are linked to a user and a game, as well as Odoo badges.
# Also, each game profile can be shared by any number of games.
# Factions, groups of profiles, can be created to share data between profiles.

# Each Game model references one or more books by ISBN.
# Individual models can be subclassed to implement game-specific functionality.


class Game(models.Model):
    _name = 'game.profile.game'
    _description = 'Game'
    
    name = fields.Char(string='Game Name', required=True)
    description = fields.Text(string='Description')
    isbn = fields.Char(string='ISBN', required=True)
    publisher = fields.Char(string='Publisher')
    year = fields.Char(string='Year')
    author = fields.Char(string='Author')
    genre = fields.Char(string='Genre')
    image = fields.Binary(string='Cover Image')

    # Profiles, many 2 many
    game_profile_ids = fields.Many2many('game.profile', string='Game Profiles')
    game_profile_count = fields.Integer(string='Game Profile Count', compute='_compute_game_profile_count')

    # Link to Product if this game is sold by us
    product_id = fields.Many2one('product.product', string='Product')

    # Each Game contains an XML definition of the game data with placeholders for profile data
    # This XML is used to generate reports, estimates and other game data
    profile_xml = fields.Text(string='Profile XML')
    
    @api.depends('game_profile_ids')
    def _compute_game_profile_count(self):
        for game in self:
            game.game_profile_count = len(game.game_profile_ids)
    
    @api.multi
    def action_view_game_profiles(self):
        self.ensure_one()
        action = self.env.ref('game_profile.action_game_profile').read()[0]
        action['domain'] = [('game_id', '=', self.id)]
        return action


class GameProfile(models.Model):
    _name = 'game.profile'
    _description = 'Game Profile'
    
    name = fields.Char(string='Profile Name', required=True)
    description = fields.Text(string='Description')
    image = fields.Binary(string='Profile Image')
    user_id = fields.Many2one('res.users', string='User', required=True)
    game_id = fields.Many2one('game.profile.game', string='Game', required=True)
    faction_id = fields.Many2one('game.profile.faction', string='Faction')
    badge_ids = fields.Many2many('game.profile.badge', string='Badges')
    game_ids = fields.Many2many('game.profile.game', string='Games')
    product_ids = fields.Many2many('product.product', string='Products')
    product_count = fields.Integer(string='Product Count', compute='_compute_product_count')
    
    @api.depends('product_ids')
    def _compute_product_count(self):
        for profile in self:
            profile.product_count = len(profile.product_ids)
    
    @api.multi
    def action_view_products(self):
        self.ensure_one()
        action = self.env.ref('product.product_normal_action_sell').read()[0]
        action['domain'] = [('id', 'in', self.product_ids.ids)]
        return action


class BadgeTrigger(models.Model):
    _name = 'game.profile.badge.trigger'
    _description = 'Badge Trigger'
    
    name = fields.Char(string='Trigger Name', required=True)
    description = fields.Text(string='Description')
    image = fields.Binary(string='Trigger Image')
    game_id = fields.Many2one('game.profile.game', string='Game', required=True)
    badge_id = fields.Many2one('game.profile.badge', string='Badge', required=True)

    match_profile_xml = fields.Text(string='Match Profile XML', 
    help='This XML is used to match against the profile XML to determine if the badge should be awarded')