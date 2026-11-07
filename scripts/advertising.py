"""Adsterra's supplied tags, inserted at their format-specific parser positions."""
import json

POPUNDER_URL = 'https://pl32241467.profitableratecpmnetwork.com/71/0c/35/710c35f89fe0ef60b2ac15b62561477d.js'
SOCIAL_BAR_URL = 'https://pl32241468.profitableratecpmnetwork.com/0f/37/59/0f3759706a504e520244852954ae166c.js'


def network_tag(url, format_name):
    # This runs while HTML is being parsed, never after DOMContentLoaded.
    # The provider receives its original synchronous tag and currentScript;
    # preserve the site's existing Global Privacy Control behaviour.
    tag = '<script src="' + url + '"></script>'
    literal = json.dumps(tag).replace('</', '<\\/')
    return ('<script data-adsterra-format="' + format_name + '">'
            'if (!navigator.globalPrivacyControl) { document.write(' + literal + '); }'
            '</script>')


def head_ads():
    return network_tag(POPUNDER_URL, 'popunder')


def footer_ads():
    return network_tag(SOCIAL_BAR_URL, 'social-bar')
