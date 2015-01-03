# coding: utf-8
import re
import sys
import json
from itertools import chain
from django.http import HttpResponse

if sys.version < '3':
    text_type = basestring
else:
    text_type = str

from django.core.exceptions import ImproperlyConfigured
from django.template import loader
from django.core import urlresolvers
from django.conf import settings
from django import get_version

from slimit import minify

try:
    from subdomains.utils import get_domain
except ImportError:
    get_domain = None

from .js_reverse_settings import (JS_VAR_NAME, JS_MINIFY,
                                  JS_EXCLUDE_NAMESPACES, JS_EXCLUDE_URLNAMES,
                                  JS_USE_SUBDOMAIN)


content_type_keyword_name = 'content_type'
if get_version() < '1.5':
    content_type_keyword_name = 'mimetype'


JS_EXCLUDE_NAMESPACES = getattr(settings, 'JS_REVERSE_EXCLUDE_NAMESPACES',
                                JS_EXCLUDE_NAMESPACES)

JS_EXCLUDE_URLNAMES = getattr(settings, 'JS_REVERSE_EXCLUDE_URLNAMES',
                              JS_EXCLUDE_URLNAMES)

JS_USE_SUBDOMAIN = (
    getattr(settings, 'JS_REVERSE_USE_SUBDOMAIN', JS_USE_SUBDOMAIN) and
    isinstance(getattr(settings, 'SUBDOMAIN_URLCONFS', None), dict) and
    get_domain)


def urls_js(request=None):
    js_var_name = getattr(settings, 'JS_REVERSE_JS_VAR_NAME', JS_VAR_NAME)
    if not re.match(r'^[$A-Z_][\dA-Z_$]*$', js_var_name.upper()):
        raise ImproperlyConfigured(
            u'JS_REVERSE_JS_VAR_NAME setting "{}" is not'
            u' a valid javascript identifier.'.format(js_var_name))

    minfiy = getattr(settings, 'JS_REVERSE_JS_MINIFY', JS_MINIFY)
    if not isinstance(minfiy, bool):
        raise ImproperlyConfigured(
            u'JS_REVERSE_JS_MINIFY setting "{}" is not a valid. '
            u'Needs to be set to True or False.'.format(minfiy))

    if JS_USE_SUBDOMAIN:
        url_confs = settings.SUBDOMAIN_URLCONFS
        _domain = get_domain()
    else:
        url_confs = {None: getattr(request, 'urlconf', None)}
        _domain = None

    urls = {}

    for subdomain, urlconf in url_confs.items():
        if subdomain is not None and _domain:
            domain = '%s.%s' % (subdomain, _domain)
        else:
            domain = _domain

        default_urlresolver = urlresolvers.get_resolver(urlconf)
        row = urls.setdefault(domain, {})

        # prepare data for namespeced urls
        named_urlresolves = [
            (n_urlresolver, namespace_path, namespace + ':')
            for namespace, (namespace_path, n_urlresolver) in
            default_urlresolver.namespace_dict.items()
        ]

        for args in chain(named_urlresolves, [default_urlresolver]):
            if not isinstance(args, (tuple, list)):
                args = [args]

            for result in prepare_url_list(*args):
                name, namespace_path, pattern = result
                row[name] = [namespace_path + pattern[0], pattern[1]]

    response_body = loader.render_to_string(
        'django_js_reverse/urls_js.tpl',
        {
            'urls': json.dumps(urls),
            'url_prefix': urlresolvers.get_script_prefix(),
            'js_var_name': js_var_name,
            'JS_USE_SUBDOMAIN': json.dumps(JS_USE_SUBDOMAIN),
            'domains': json.dumps(url_confs.keys())
        },
        {})

    if minfiy:
        response_body = minify(
            response_body, mangle=True, mangle_toplevel=False)

    if not request:
        return response_body

    return HttpResponse(
        response_body,
        **{content_type_keyword_name: 'application/javascript'})


def prepare_url_list(urlresolver, namespace_path='', namespace=''):
    """
    Generator who make lists like this:
        (<url_name>, <namespace_path>, <url_patern_tuple>)
    """
    for url_name, url_pattern in urlresolver.reverse_dict.items():
        if not isinstance(url_name, text_type):
            continue

        if JS_EXCLUDE_NAMESPACES and namespace[:-1] in JS_EXCLUDE_NAMESPACES:
            continue

        if JS_EXCLUDE_URLNAMES and url_name in JS_EXCLUDE_URLNAMES:
            continue

        yield [namespace + url_name, namespace_path, url_pattern[0][0]]
